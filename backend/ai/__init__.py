"""
AI模块初始化
"""

from .face_recognition.engine import FaceRecognitionEngine, face_engine
from .smart_album.recommender import SmartAlbumRecommender, smart_album_recommender
from .auto_tagging.tagger import AutoTagger, auto_tagger
from .similarity.detector import SimilarityDetector, similarity_detector

__all__ = [
    'FaceRecognitionEngine',
    'face_engine',
    'SmartAlbumRecommender',
    'smart_album_recommender',
    'AutoTagger',
    'auto_tagger',
    'SimilarityDetector',
    'similarity_detector',
]
