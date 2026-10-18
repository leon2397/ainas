from loguru import logger
"""
Plugin Loader
Dynamic loading of AI engines and storage plugins
"""

import os
import importlib
import logging
from typing import Dict, Optional, Type
from pathlib import Path

from core.ai_engine import AIEngine
from core.storage import FileStorage

logger = logger.bind(name="ai_nas.plugins")


class PluginLoader:
    """Dynamic plugin loader for AI engines and storage"""
    
    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else Path(__file__).parent.parent
        self._ai_engines: Dict[str, Type[AIEngine]] = {}
        self._storage: Dict[str, Type[FileStorage]] = {}
        self._load_builtin_plugins()
    
    def _load_builtin_plugins(self):
        """Load all builtin plugins"""
        # AI Engines
        self._load_ai_engine('cpu', 'plugins.ai.cpu_engine', 'CPUEngine')
        self._load_ai_engine('bm1688', 'plugins.ai.bm1688_engine', 'BM1688Engine')
        self._load_ai_engine('face', 'plugins.ai.face_engine', 'FaceRecognitionEngine')
        
        # Storage
        self._load_storage('local', 'plugins.storage.local_storage', 'LocalStorage')
        self._load_storage('ssh', 'plugins.storage.ssh_storage', 'SSHStorage')
        self._load_storage('smb', 'plugins.storage.smb_storage', 'SMBStorage')
        self._load_storage('nas', 'plugins.storage.nas_storage', 'NasStorage')
    
    def _load_ai_engine(self, name: str, module_path: str, class_name: str):
        """Load an AI engine plugin"""
        try:
            module = importlib.import_module(module_path)
            engine_class = getattr(module, class_name, None)
            if engine_class and issubclass(engine_class, AIEngine):
                self._ai_engines[name] = engine_class
                logger.info(f"Loaded AI engine: {name}")
            else:
                logger.warning(f"{class_name} is not a subclass of AIEngine")
        except ImportError as e:
            logger.warning(f"Failed to load AI engine {name}: {e}")
        except Exception as e:
            logger.error(f"Loading AI engine {name}: {e}")
    
    def _load_storage(self, name: str, module_path: str, class_name: str):
        """Load a storage plugin"""
        try:
            module = importlib.import_module(module_path)
            storage_class = getattr(module, class_name, None)
            if storage_class and issubclass(storage_class, FileStorage):
                self._storage[name] = storage_class
                logger.info(f"Loaded storage: {name}")
            else:
                logger.warning(f"{class_name} is not a subclass of FileStorage")
        except ImportError as e:
            logger.warning(f"Failed to load storage {name}: {e}")
        except Exception as e:
            logger.error(f"Error loading storage {name}: {e}")
    
    def get_ai_engine(self, name: str, config: Dict) -> Optional[AIEngine]:
        """Create an AI engine instance"""
        engine_class = self._ai_engines.get(name)
        if engine_class:
            return engine_class(config)
        return None
    
    def get_storage(self, name: str, config: Dict) -> Optional[FileStorage]:
        """Create a storage instance"""
        storage_class = self._storage.get(name)
        if storage_class:
            return storage_class(config)
        return None
    
    def list_ai_engines(self) -> list:
        """List available AI engines"""
        return list(self._ai_engines.keys())
    
    def list_storage(self) -> list:
        """List available storage plugins"""
        return list(self._storage.keys())
    
    def register_ai_engine(self, name: str, engine_class: Type[AIEngine]):
        """Register a custom AI engine"""
        self._ai_engines[name] = engine_class
    
    def register_storage(self, name: str, storage_class: Type[FileStorage]):
        """Register a custom storage"""
        self._storage[name] = storage_class


# Global plugin loader instance
plugin_loader = PluginLoader()


def get_plugin_loader() -> PluginLoader:
    """Get plugin loader instance"""
    return plugin_loader
