from loguru import logger
"""
Face Detection Engine Plugin
Uses face_recognition library (dlib-based) for face detection and embedding extraction.
Falls back to OpenCV Haar cascade when face_recognition is not available.
"""

import os
import cv2
import numpy as np
from typing import Dict, List, Any, Optional
from PIL import Image

from modules.mod_ai.base import AIEngine


class FaceRecognitionEngine(AIEngine):
    """
    Face detection and recognition engine.

    Supports two backends:
    1. face_recognition (dlib) - high accuracy, generates 128-dim embeddings
    2. OpenCV Haar cascade - lightweight, no dlib dependency
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.detection_model = config.get("detection_model", "hog")  # hog or cnn
        self.up_sample = config.get("up_sample", 1)
        self.tolerance = config.get("tolerance", 0.6)
        self.min_face_size = config.get("min_face_size", 30)
        self._use_dlib = False
        self._cascade = None
        self._init_backend()

    def _init_backend(self):
        """Initialize the best available backend"""
        try:
            import face_recognition
            self._use_dlib = True
            logger.info("[OK] FaceRecognition: using dlib backend (high accuracy)")
        except ImportError:
            self._use_dlib = False
            cascade_path = self.config.get(
                "haar_cascade_path",
                cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            )
            if os.path.exists(cascade_path):
                self._cascade = cv2.CascadeClassifier(cascade_path)
                logger.info("[OK] FaceRecognition: using OpenCV Haar cascade (fallback)")
            else:
                logger.info("[WARN] FaceRecognition: no backend available")

    def image_predict(self, filepath: str) -> Dict[str, Any]:
        """Image classification (face count as a feature)"""
        result = self.face_detect(filepath)
        return {
            "tags": [f"{len(result.get('faces', []))}_faces"],
            "feature": [],
            "confidence": 1.0 if result.get("faces") else 0.0
        }

    def video_predict(self, filepath: str) -> Dict[str, Any]:
        """Video face detection (sample frames)"""
        cap = cv2.VideoCapture(filepath)
        if not cap.isOpened():
            return {"tags": [], "audio_tags": [], "duration": 0, "feature": []}

        fps = cap.get(cv2.CAP_PROP_FPS) or 25
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps if fps > 0 else 0

        all_faces = []
        sample_interval = max(1, int(fps * 2))  # sample every 2 seconds
        frame_idx = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            if frame_idx % sample_interval == 0:
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                result = self._detect_faces_array(rgb)
                all_faces.extend(result)
            frame_idx += 1

        cap.release()

        return {
            "tags": [f"{len(all_faces)}_faces_detected"],
            "audio_tags": [],
            "duration": duration,
            "feature": []
        }

    def face_detect(self, filepath: str) -> Dict[str, Any]:
        """
        Detect faces and extract embeddings.

        Returns:
            {"faces": [{"box": [top,right,bottom,left], "confidence": 0.95}],
             "embeddings": [[0.1, 0.2, ...], ...]}
        """
        try:
            img = Image.open(filepath)
            img_array = np.array(img.convert("RGB"))
            return self._detect_faces_array(img_array)
        except Exception as e:
            return {"faces": [], "embeddings": [], "error": str(e)}

    def _detect_faces_array(self, img_array: np.ndarray) -> Dict[str, Any]:
        """Detect faces in a numpy RGB array"""
        if self._use_dlib:
            return self._detect_dlib(img_array)
        elif self._cascade is not None:
            return self._detect_haar(img_array)
        else:
            return {"faces": [], "embeddings": []}

    def _detect_dlib(self, img_array: np.ndarray) -> Dict[str, Any]:
        """Detect faces using face_recognition (dlib)"""
        try:
            import face_recognition

            face_locations = face_recognition.face_locations(
                img_array,
                number_of_times_to_upsample=self.up_sample,
                model=self.detection_model
            )
            face_encodings = face_recognition.face_encodings(img_array, face_locations)

            faces = []
            for loc in face_locations:
                top, right, bottom, left = loc
                h, w = bottom - top, right - left
                confidence = min(1.0, max(h, w) / 200.0)  # rough confidence from size
                faces.append({
                    "box": [top, right, bottom, left],
                    "size": [h, w],
                    "confidence": round(confidence, 2)
                })

            embeddings = [enc.tolist() for enc in face_encodings]

            return {"faces": faces, "embeddings": embeddings}
        except Exception as e:
            logger.info(f"[ERROR] dlib face detection failed: {e}")
            return {"faces": [], "embeddings": []}

    def _detect_haar(self, img_array: np.ndarray) -> Dict[str, Any]:
        """Detect faces using OpenCV Haar cascade (no embedding, box only)"""
        try:
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            detected = self._cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(self.min_face_size, self.min_face_size)
            )

            faces = []
            for (x, y, w, h) in detected:
                confidence = min(1.0, max(w, h) / 200.0)
                faces.append({
                    "box": [y, x + w, y + h, x],  # top, right, bottom, left
                    "size": [h, w],
                    "confidence": round(confidence, 2)
                })

            return {"faces": faces, "embeddings": []}
        except Exception as e:
            logger.info(f"[ERROR] Haar face detection failed: {e}")
            return {"faces": [], "embeddings": []}

    def deduplicate(self, feature: List[float], threshold: float = 0.8) -> List[str]:
        """Compare face embedding against known faces (placeholder)"""
        # This requires a face database; actual dedup handled by vector_db service
        return []

    def compare_faces(self, embedding1: List[float], embedding2: List[float]) -> Dict:
        """
        Compare two face embeddings.

        Returns:
            {"match": bool, "distance": float}
        """
        if not self._use_dlib:
            return {"match": False, "distance": -1, "error": "dlib required"}

        try:
            import face_recognition
            dist = face_recognition.face_distance(
                [np.array(embedding1)], np.array(embedding2)
            )[0]
            return {
                "match": dist <= self.tolerance,
                "distance": round(float(dist), 4)
            }
        except Exception as e:
            return {"match": False, "distance": -1, "error": str(e)}


def create_engine(config: Dict) -> FaceRecognitionEngine:
    """Factory function for plugin loader"""
    return FaceRecognitionEngine(config)
