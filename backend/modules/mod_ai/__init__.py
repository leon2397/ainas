"""
mod_ai — AI-NAS AI 引擎模块

提供：
- AIEngine 抽象基类
- CPUEngine（ONNX Runtime）
- BM1688Engine（算能 NPU）
- FaceRecognitionEngine（人脸检测）
- 引擎加载器

使用方式：
    from modules.mod_ai import AIEngine, get_ai_engine
"""

from modules.mod_ai.base import AIEngine
from modules.mod_ai.cpu_engine import CPUEngine, create_engine as create_cpu_engine
from modules.mod_ai.bm1688_engine import BM1688Engine
from modules.mod_ai.face_engine import FaceRecognitionEngine
from modules.mod_ai.loader import get_ai_engine, get_engine_status

__all__ = [
    "AIEngine",
    "CPUEngine",
    "create_cpu_engine",
    "BM1688Engine",
    "FaceRecognitionEngine",
    "get_ai_engine",
    "get_engine_status",
]
