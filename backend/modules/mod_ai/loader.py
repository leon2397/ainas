"""
AI Engine Loader

简化版加载器，从 mod_ai 内部加载引擎
"""

import os
from typing import Dict, Optional, Type, Any
from pathlib import Path

from core.logger import logger
from modules.mod_ai.base import AIEngine


class AILoader:
    """AI 引擎加载器"""
    
    def __init__(self):
        self._engines: Dict[str, Type[AIEngine]] = {}
        self._load_builtin_engines()
    
    def _load_builtin_engines(self):
        """加载内置 AI 引擎"""
        # CPU Engine (ONNX)
        try:
            from modules.mod_ai.cpu_engine import CPUEngine
            self._engines['cpu'] = CPUEngine
            logger.info("[AI] Loaded engine: cpu")
        except Exception as e:
            logger.warning(f"[AI] Failed to load cpu engine: {e}")
        
        # BM1688 Engine (算能 NPU)
        try:
            from modules.mod_ai.bm1688_engine import BM1688Engine
            self._engines['bm1688'] = BM1688Engine
            logger.info("[AI] Loaded engine: bm1688")
        except Exception as e:
            logger.debug(f"[AI] BM1688 not available: {e}")
        
        # Face Engine
        try:
            from modules.mod_ai.face_engine import FaceRecognitionEngine as FaceEngine
            self._engines['face'] = FaceEngine
            logger.info("[AI] Loaded engine: face")
        except Exception as e:
            logger.debug(f"[AI] Face engine not available: {e}")
    
    def get_engine(self, name: str, config: Dict[str, Any] = None) -> Optional[AIEngine]:
        """获取 AI 引擎实例"""
        engine_class = self._engines.get(name)
        if engine_class:
            return engine_class(config or {})
        return None
    
    def list_engines(self) -> list:
        """列出可用引擎"""
        return list(self._engines.keys())
    
    def register_engine(self, name: str, engine_class: Type[AIEngine]):
        """注册自定义引擎"""
        self._engines[name] = engine_class


# 全局单例
_loader: Optional[AILoader] = None


def get_ai_engine(name: str = 'cpu', config: Dict[str, Any] = None) -> Optional[AIEngine]:
    """获取 AI 引擎（便捷函数）"""
    global _loader
    if _loader is None:
        _loader = AILoader()
    return _loader.get_engine(name, config)


def get_engine_status() -> Dict[str, Any]:
    """获取引擎状态"""
    global _loader
    if _loader is None:
        _loader = AILoader()
    return {
        'available': _loader.list_engines(),
        'count': len(_loader.list_engines()),
    }
