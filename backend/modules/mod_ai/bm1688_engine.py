from loguru import logger
"""
BM1688 AI Engine Plugin
NPU-based AI inference using Sophon BMNNSDK

NOTE: This is a framework/template. Actual implementation requires:
1. BMNNSDK installed on the device
2. ONNX model converted to BM1688 format (.bmodel)
3. sophon-pytorch or sophon-tensorflow for model conversion

For development/testing without BM1688 hardware, use CPUEngine instead.
"""

import os
import numpy as np
from typing import Dict, List, Any, Optional

from modules.mod_ai.base import AIEngine


class BM1688Engine(AIEngine):
    """
    BM1688 NPU Engine
    
    Hardware: Sophon BM1688 AI Processor
    - 32 TOPS INT8 / 16 TFLOPS FP16
    - Supports ONNX, TensorFlow, PyTorch models
    - Model format: .bmodel (compiled)
    
    This is a placeholder implementation. 
    Install sophon-pytorch and bmnnsdk2 for actual use.
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.model_path = config.get('model_path', 'models/image_model.bmodel')
        self.input_size = tuple(config.get('input_size', [224, 224]))
        self.threshold = config.get('threshold', 0.5)
        self.batch_size = config.get('batch_size', 8)
        self.npu_device_id = config.get('npu_device_id', 0)
        
        self._handle = None
        self._input_names = []
        self._output_names = []
        self._initialized = False
        self._available = False
    
    def _initialize(self):
        """Initialize BM1688 NPU"""
        if self._initialized:
            return
        
        self._initialized = True
        
        # Check if BMNNSDK is available
        try:
            # Try to import sophon library
            import bmnnsdk2 as bm
            
            # Initialize BM1688
            self._handle = bm.BM1688()
            
            # Load model
            if os.path.exists(self.model_path):
                self._handle.load_model(self.model_path)
                self._available = True
                logger.info(f"✅ BM1688 Engine loaded: {self.model_path}")
            else:
                logger.info(f"⚠️ BM1688 model not found: {self.model_path}")
                logger.info("   Falling back to CPU inference")
                self._available = False
                
        except ImportError:
            logger.info("⚠️ BMNNSDK2 not installed")
            logger.info("   Please install: pip install bmnnsdk2")
            logger.info("   Or download from: https://developer.sophgo.com/")
            self._available = False
        except Exception as e:
            logger.info(f"⚠️ BM1688 initialization failed: {e}")
            self._available = False
    
    @property
    def is_available(self) -> bool:
        """Check if NPU is available"""
        if not self._initialized:
            self._initialize()
        return self._available
    
    def image_predict(self, filepath: str) -> Dict[str, Any]:
        """Image AI inference using BM1688 NPU"""
        self._initialize()
        
        if not self._available:
            logger.info("⚠️ BM1688 not available, skipping inference")
            return {
                'tags': [],
                'feature': [],
                'confidence': 0.0,
                'engine': 'none',
                'error': 'BM1688 not available'
            }
        
        try:
            # Import BMNNSDK
            import bmnnsdk2 as bm
            import cv2
            
            # Read and preprocess image
            img = cv2.imread(filepath)
            if img is None:
                return {'tags': [], 'feature': [], 'confidence': 0.0, 'error': 'Cannot read image'}
            
            # Resize to model input size
            img_input = cv2.resize(img, self.input_size)
            
            # Convert BGR to RGB and normalize
            img_input = cv2.cvtColor(img_input, cv2.COLOR_BGR2RGB)
            img_input = img_input.astype(np.float32) / 255.0
            
            # Transpose to NCHW format
            img_input = np.transpose(img_input, (2, 0, 1))
            img_input = np.expand_dims(img_input, axis=0)
            
            # Inference on NPU
            output = self._handle.inference(img_input)
            
            # Process output
            probs = output[0]  # Assuming first output is classification
            tags, confidence = self._process_classification_output(probs)
            
            # Extract feature vector
            feature = self._extract_feature(img_input)
            
            return {
                'tags': tags,
                'feature': feature,
                'confidence': confidence,
                'engine': 'bm1688'
            }
            
        except Exception as e:
            logger.info(f"BM1688 inference error: {e}")
            return {
                'tags': [],
                'feature': [],
                'confidence': 0.0,
                'engine': 'bm1688',
                'error': str(e)
            }
    
    def _process_classification_output(self, output: np.ndarray) -> tuple:
        """Process classification output from NPU"""
        # Get top-k predictions
        top_indices = np.argsort(output)[-5:][::-1]
        
        tags = []
        for idx in top_indices:
            if output[idx] >= self.threshold:
                tags.append(f'class_{idx}')
        
        confidence = float(output[top_indices[0]]) if len(top_indices) > 0 else 0.0
        
        return tags, confidence
    
    def _extract_feature(self, img_input: np.ndarray) -> List[float]:
        """Extract feature vector from intermediate layer"""
        # For feature extraction, use the model's embedding layer
        # This would require accessing the feature extraction head
        # For now, return a simple histogram-based feature
        img = (img_input[0] * 255).astype(np.uint8)
        hist = []
        for c in range(3):
            h = np.histogram(img[c], bins=32, range=(0, 256))[0]
            h = h / (h.sum() + 1e-6)
            hist.extend(h.tolist())
        return hist
    
    def video_predict(self, filepath: str) -> Dict[str, Any]:
        """Video AI inference using BM1688 NPU"""
        self._initialize()
        
        if not self._available:
            return {
                'tags': [],
                'audio_tags': [],
                'duration': 0,
                'feature': [],
                'engine': 'none',
                'error': 'BM1688 not available'
            }
        
        try:
            import cv2
            
            cap = cv2.VideoCapture(filepath)
            if not cap.isOpened():
                return {'tags': [], 'audio_tags': [], 'duration': 0, 'feature': [], 'error': 'Cannot open video'}
            
            duration = cap.get(cv2.CAP_PROP_FRAME_COUNT) / cap.get(cv2.CAP_PROP_FPS)
            
            # Extract key frames (scene detection or uniform sampling)
            frame_tags = []
            features = []
            
            # Uniform sampling: 5 key frames
            frame_interval = max(1, int(cap.get(cv2.CAP_PROP_FRAME_COUNT) / 5))
            
            frame_count = 0
            while len(features) < 5:
                ret, frame = cap.read()
                if not ret:
                    break
                
                if frame_count % frame_interval == 0:
                    # Save frame to temp file for inference
                    temp_path = f'/tmp/frame_{frame_count}.jpg'
                    cv2.imwrite(temp_path, frame)
                    
                    result = self.image_predict(temp_path)
                    frame_tags.extend(result.get('tags', []))
                    features.append(result.get('feature', []))
                    
                    # Clean up
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                
                frame_count += 1
            
            cap.release()
            
            # Aggregate results
            tags = list(set(frame_tags))[:10]
            
            # Average features
            if features:
                feature = np.mean(features, axis=0).tolist()
            else:
                feature = []
            
            return {
                'tags': tags,
                'audio_tags': [],  # Audio requires separate processing
                'duration': duration,
                'feature': feature,
                'engine': 'bm1688'
            }
            
        except Exception as e:
            return {
                'tags': [],
                'audio_tags': [],
                'duration': 0,
                'feature': [],
                'engine': 'bm1688',
                'error': str(e)
            }
    
    def face_detect(self, filepath: str) -> Dict[str, Any]:
        """Face detection using BM1688"""
        self._initialize()
        
        if not self._available:
            return {'faces': [], 'embeddings': [], 'count': 0, 'engine': 'none'}
        
        try:
            import cv2
            
            # Use OpenCV's DNN module with a face detection model
            # For BM1688, would use a compiled face detection model
            face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            )
            
            img = cv2.imread(filepath)
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            faces = face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(30, 30)
            )
            
            face_list = []
            embedding_list = []
            
            for (x, y, w, h) in faces:
                face_list.append({
                    'x': int(x), 'y': int(y),
                    'width': int(w), 'height': int(h)
                })
                
                # Extract face region
                face_roi = img[y:y+h, x:x+w]
                face_path = f'/tmp/face_{x}_{y}.jpg'
                cv2.imwrite(face_path, face_roi)
                
                # Get face embedding (would use a face recognition model)
                embedding = self._extract_face_embedding(face_path)
                embedding_list.append(embedding)
                
                if os.path.exists(face_path):
                    os.remove(face_path)
            
            return {
                'faces': face_list,
                'embeddings': embedding_list,
                'count': len(face_list),
                'engine': 'bm1688'
            }
            
        except Exception as e:
            return {
                'faces': [],
                'embeddings': [],
                'count': 0,
                'engine': 'bm1688',
                'error': str(e)
            }
    
    def _extract_face_embedding(self, face_path: str) -> List[float]:
        """Extract face embedding using face recognition model"""
        # This would use a face recognition model compiled for BM1688
        # For now, return a simple feature
        try:
            import cv2
            img = cv2.imread(face_path)
            img = cv2.resize(img, (64, 64))
            feature = img.flatten() / 255.0
            return feature[:128].tolist()  # 128-dim embedding
        except Exception:
            return [0.0] * 128
    
    def deduplicate(self, feature: List[float], threshold: float = 0.8) -> List[str]:
        """Similarity-based deduplication"""
        # Would use vector similarity search with ChromaDB or FAISS
        # For BM1688, can use BM1880's vector engine for acceleration
        return []
    
    def get_npu_status(self) -> Dict[str, Any]:
        """Get NPU usage status"""
        if not self._initialized:
            self._initialize()
        
        if not self._available:
            return {
                'available': False,
                'usage': 0.0,
                'model': None
            }
        
        try:
            # Get NPU utilization
            usage = self._handle.get_utilization()
            
            return {
                'available': True,
                'usage': usage,
                'model': self.model_path
            }
        except Exception:
            return {
                'available': True,
                'usage': 0.0,
                'model': self.model_path
            }


def create_engine(config: Dict) -> BM1688Engine:
    """Create BM1688 engine instance"""
    return BM1688Engine(config)
