"""
人脸识别增强模块
AI智能化 - Phase 3.1
支持NPU加速、人脸检测、识别、聚类
"""

import cv2
from loguru import logger
import numpy as np
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import json
import asyncio
from datetime import datetime


@dataclass
class FaceDetection:
    """人脸检测结果"""
    face_id: str
    bbox: Tuple[int, int, int, int]  # x, y, w, h
    confidence: float
    landmarks: Optional[List[Tuple[int, int]]] = None
    encoding: Optional[np.ndarray] = None


@dataclass
class FaceIdentity:
    """人脸身份"""
    identity_id: str
    name: str
    face_ids: List[str]
    encodings: List[np.ndarray]
    sample_count: int
    created_at: datetime
    updated_at: datetime
    metadata: Dict = None


class FaceRecognitionEngine:
    """人脸识别引擎"""
    
    def __init__(self, model_path: str = "backend/ai/models/face", use_npu: bool = False):
        self.model_path = Path(model_path)
        self.model_path.mkdir(parents=True, exist_ok=True)
        self.use_npu = use_npu
        
        # 初始化检测器
        self._init_detector()
        
        # 人脸数据库
        self._identities: Dict[str, FaceIdentity] = {}
        self._face_to_identity: Dict[str, str] = {}
        
        # 相似度阈值
        self.similarity_threshold = 0.6
        
    def _init_detector(self):
        """初始化人脸检测器"""
        try:
            # 尝试加载OpenCV DNN人脸检测器
            proto_file = self.model_path / "deploy.prototxt"
            model_file = self.model_path / "res10_300x300_ssd_iter_140000.caffemodel"
            
            if proto_file.exists() and model_file.exists():
                self.detector = cv2.dnn.readNetFromCaffe(
                    str(proto_file),
                    str(model_file)
                )
                
                # 如果使用NPU
                if self.use_npu:
                    self.detector.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
                    self.detector.setPreferableTarget(cv2.dnn.DNN_TARGET_OPENCL)
            else:
                # 使用Haar级联作为备选
                self.detector = cv2.CascadeClassifier(
                    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
                )
                self.detector_type = "haar"
            
            # 初始化人脸编码器 (使用简单的特征提取)
            self.encoder = None
            
        except Exception as e:
            logger.info(f"人脸检测器初始化失败: {e}")
            self.detector = None
    
    async def detect_faces(self, image_path: str) -> List[FaceDetection]:
        """检测图片中的人脸"""
        if not self.detector:
            return []
        
        # 读取图片
        image = cv2.imread(image_path)
        if image is None:
            return []
        
        h, w = image.shape[:2]
        detections = []
        
        try:
            if hasattr(self, 'detector_type') and self.detector_type == "haar":
                # Haar级联检测
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                faces = self.detector.detectMultiScale(
                    gray,
                    scaleFactor=1.1,
                    minNeighbors=5,
                    minSize=(30, 30)
                )
                
                for i, (x, y, w_face, h_face) in enumerate(faces):
                    face_id = f"face_{datetime.now().timestamp()}_{i}"
                    detection = FaceDetection(
                        face_id=face_id,
                        bbox=(x, y, w_face, h_face),
                        confidence=0.8  # Haar不提供置信度
                    )
                    detections.append(detection)
            else:
                # DNN检测
                blob = cv2.dnn.blobFromImage(
                    cv2.resize(image, (300, 300)),
                    1.0,
                    (300, 300),
                    (104.0, 177.0, 123.0)
                )
                
                self.detector.setInput(blob)
                faces = self.detector.forward()
                
                for i in range(faces.shape[2]):
                    confidence = faces[0, 0, i, 2]
                    
                    if confidence > 0.5:
                        box = faces[0, 0, i, 3:7] * np.array([w, h, w, h])
                        x, y, x2, y2 = box.astype(int)
                        
                        face_id = f"face_{datetime.now().timestamp()}_{i}"
                        detection = FaceDetection(
                            face_id=face_id,
                            bbox=(x, y, x2-x, y2-y),
                            confidence=float(confidence)
                        )
                        detections.append(detection)
        
        except Exception as e:
            logger.info(f"人脸检测错误: {e}")
        
        # 提取人脸编码
        for detection in detections:
            detection.encoding = await self._extract_encoding(image, detection.bbox)
        
        return detections
    
    async def _extract_encoding(self, image: np.ndarray, bbox: Tuple[int, ...]) -> np.ndarray:
        """提取人脸特征编码"""
        x, y, w, h = bbox
        
        # 提取人脸区域
        face_roi = image[y:y+h, x:x+w]
        if face_roi.size == 0:
            return np.zeros(128)
        
        # 标准化大小
        face_roi = cv2.resize(face_roi, (128, 128))
        
        # 转换为灰度
        gray = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)
        
        # 计算简单的特征向量 (使用直方图)
        hist = cv2.calcHist([gray], [0], None, [128], [0, 256])
        hist = cv2.normalize(hist, hist).flatten()
        
        return hist
    
    async def identify_face(self, face_encoding: np.ndarray) -> Optional[FaceIdentity]:
        """识别人脸"""
        if not self._identities:
            return None
        
        best_match = None
        best_score = 0
        
        for identity in self._identities.values():
            for encoding in identity.encodings:
                similarity = self._calculate_similarity(face_encoding, encoding)
                if similarity > best_score and similarity > self.similarity_threshold:
                    best_score = similarity
                    best_match = identity
        
        return best_match
    
    def _calculate_similarity(self, encoding1: np.ndarray, encoding2: np.ndarray) -> float:
        """计算编码相似度"""
        # 使用余弦相似度
        dot_product = np.dot(encoding1, encoding2)
        norm1 = np.linalg.norm(encoding1)
        norm2 = np.linalg.norm(encoding2)
        
        if norm1 == 0 or norm2 == 0:
            return 0
        
        return dot_product / (norm1 * norm2)
    
    async def create_identity(self, name: str, face_encodings: List[np.ndarray]) -> FaceIdentity:
        """创建新的人脸身份"""
        import uuid
        
        identity_id = str(uuid.uuid4())
        face_ids = [f"face_{i}_{datetime.now().timestamp()}" for i in range(len(face_encodings))]
        
        identity = FaceIdentity(
            identity_id=identity_id,
            name=name,
            face_ids=face_ids,
            encodings=face_encodings,
            sample_count=len(face_encodings),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            metadata={}
        )
        
        self._identities[identity_id] = identity
        
        # 建立映射
        for face_id in face_ids:
            self._face_to_identity[face_id] = identity_id
        
        return identity
    
    async def add_face_to_identity(self, identity_id: str, face_encoding: np.ndarray) -> bool:
        """向身份添加新人脸"""
        if identity_id not in self._identities:
            return False
        
        identity = self._identities[identity_id]
        face_id = f"face_{len(identity.face_ids)}_{datetime.now().timestamp()}"
        
        identity.face_ids.append(face_id)
        identity.encodings.append(face_encoding)
        identity.sample_count += 1
        identity.updated_at = datetime.utcnow()
        
        self._face_to_identity[face_id] = identity_id
        
        return True
    
    async def cluster_faces(self, face_encodings: List[np.ndarray]) -> Dict[int, List[int]]:
        """人脸聚类"""
        if len(face_encodings) < 2:
            return {0: list(range(len(face_encodings)))}
        
        # 使用简单的层次聚类
        from sklearn.cluster import AgglomerativeClustering
        
        # 计算距离矩阵
        n = len(face_encodings)
        distance_matrix = np.zeros((n, n))
        
        for i in range(n):
            for j in range(i+1, n):
                similarity = self._calculate_similarity(face_encodings[i], face_encodings[j])
                distance = 1 - similarity
                distance_matrix[i, j] = distance
                distance_matrix[j, i] = distance
        
        # 聚类
        clustering = AgglomerativeClustering(
            n_clusters=None,
            distance_threshold=0.4,
            linkage='average',
            metric='precomputed'
        )
        
        labels = clustering.fit_predict(distance_matrix)
        
        # 整理结果
        clusters = {}
        for idx, label in enumerate(labels):
            if label not in clusters:
                clusters[label] = []
            clusters[label].append(idx)
        
        return clusters
    
    async def process_media(self, media_path: str) -> Dict:
        """处理媒体文件，检测和识别人脸"""
        result = {
            "media_path": media_path,
            "faces_detected": 0,
            "faces_recognized": 0,
            "identities": [],
            "detections": []
        }
        
        # 检测人脸
        detections = await self.detect_faces(media_path)
        result["faces_detected"] = len(detections)
        
        # 识别人脸
        for detection in detections:
            identity = await self.identify_face(detection.encoding)
            
            detection_info = {
                "face_id": detection.face_id,
                "bbox": detection.bbox,
                "confidence": detection.confidence,
                "identity": None
            }
            
            if identity:
                detection_info["identity"] = {
                    "id": identity.identity_id,
                    "name": identity.name
                }
                result["faces_recognized"] += 1
                
                if identity.name not in [i["name"] for i in result["identities"]]:
                    result["identities"].append({
                        "id": identity.identity_id,
                        "name": identity.name
                    })
            
            result["detections"].append(detection_info)
        
        return result
    
    def save_identities(self, filepath: str = None):
        """保存身份数据库"""
        if filepath is None:
            filepath = self.model_path / "identities.json"
        
        data = {}
        for identity_id, identity in self._identities.items():
            data[identity_id] = {
                "identity_id": identity.identity_id,
                "name": identity.name,
                "face_ids": identity.face_ids,
                "encodings": [enc.tolist() for enc in identity.encodings],
                "sample_count": identity.sample_count,
                "created_at": identity.created_at.isoformat(),
                "updated_at": identity.updated_at.isoformat(),
                "metadata": identity.metadata
            }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def load_identities(self, filepath: str = None):
        """加载身份数据库"""
        if filepath is None:
            filepath = self.model_path / "identities.json"
        
        if not Path(filepath).exists():
            return
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for identity_id, identity_data in data.items():
            identity = FaceIdentity(
                identity_id=identity_data["identity_id"],
                name=identity_data["name"],
                face_ids=identity_data["face_ids"],
                encodings=[np.array(enc) for enc in identity_data["encodings"]],
                sample_count=identity_data["sample_count"],
                created_at=datetime.fromisoformat(identity_data["created_at"]),
                updated_at=datetime.fromisoformat(identity_data["updated_at"]),
                metadata=identity_data.get("metadata", {})
            )
            
            self._identities[identity_id] = identity
            
            for face_id in identity.face_ids:
                self._face_to_identity[face_id] = identity_id


# 全局人脸识别引擎实例
face_engine = FaceRecognitionEngine()
