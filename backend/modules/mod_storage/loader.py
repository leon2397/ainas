"""
Storage Loader

简化版加载器，从 mod_storage 内部加载存储引擎
"""

from typing import Dict, Optional, Type, Any

from core.logger import logger
from modules.mod_storage.base import FileStorage


class StorageLoader:
    """存储加载器"""
    
    def __init__(self):
        self._storages: Dict[str, Type[FileStorage]] = {}
        self._load_builtin_storages()
    
    def _load_builtin_storages(self):
        """加载内置存储引擎"""
        # Local Storage
        try:
            from modules.mod_storage.local_storage import LocalStorage
            self._storages['local'] = LocalStorage
            logger.info("[Storage] Loaded: local")
        except Exception as e:
            logger.warning(f"[Storage] Failed to load local: {e}")
        
        # SSH Storage
        try:
            from modules.mod_storage.ssh_storage import SSHStorage
            self._storages['ssh'] = SSHStorage
            logger.info("[Storage] Loaded: ssh")
        except Exception as e:
            logger.debug(f"[Storage] SSH not available: {e}")
        
        # SMB Storage
        try:
            from modules.mod_storage.smb_storage import SMBStorage
            self._storages['smb'] = SMBStorage
            logger.info("[Storage] Loaded: smb")
        except Exception as e:
            logger.debug(f"[Storage] SMB not available: {e}")
        
        # NAS Storage
        try:
            from modules.mod_storage.nas_storage import NasStorage
            self._storages['nas'] = NasStorage
            logger.info("[Storage] Loaded: nas")
        except Exception as e:
            logger.debug(f"[Storage] NAS not available: {e}")
        
        # Cloud Storage
        try:
            from modules.mod_storage.cloud_storage import CloudStorage
            self._storages['cloud'] = CloudStorage
            logger.info("[Storage] Loaded: cloud")
        except Exception as e:
            logger.debug(f"[Storage] Cloud not available: {e}")
    
    def get_storage(self, name: str, config: Dict[str, Any] = None) -> Optional[FileStorage]:
        """获取存储实例"""
        storage_class = self._storages.get(name)
        if storage_class:
            return storage_class(config or {})
        return None
    
    def list_storages(self) -> list:
        """列出可用存储"""
        return list(self._storages.keys())
    
    def register_storage(self, name: str, storage_class: Type[FileStorage]):
        """注册自定义存储"""
        self._storages[name] = storage_class


# 全局单例
_loader: Optional[StorageLoader] = None


def get_storage(name: str = 'local', config: Dict[str, Any] = None) -> Optional[FileStorage]:
    """获取存储实例（便捷函数）"""
    global _loader
    if _loader is None:
        _loader = StorageLoader()
    return _loader.get_storage(name, config)


def get_storage_status() -> Dict[str, Any]:
    """获取存储状态"""
    global _loader
    if _loader is None:
        _loader = StorageLoader()
    return {
        'available': _loader.list_storages(),
        'count': len(_loader.list_storages()),
    }
