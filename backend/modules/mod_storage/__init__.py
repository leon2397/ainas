"""
mod_storage — AI-NAS 存储模块

提供：
- FileStorage 抽象基类
- LocalStorage（本地文件系统）
- SSHStorage（SSH/SFTP）
- SMBStorage（SMB/CIFS）
- NasStorage（NAS 专用）
- CloudStorage（云存储）

使用方式：
    from modules.mod_storage import FileStorage, LocalStorage
"""

from modules.mod_storage.base import FileStorage
from modules.mod_storage.local_storage import LocalStorage
from modules.mod_storage.ssh_storage import SSHStorage
from modules.mod_storage.smb_storage import SMBStorage
from modules.mod_storage.nas_storage import NasStorage
from modules.mod_storage.cloud_storage import CloudStorage
from modules.mod_storage.loader import StorageLoader, get_storage, get_storage_status

__all__ = [
    "FileStorage",
    "LocalStorage",
    "SSHStorage",
    "SMBStorage",
    "NasStorage",
    "CloudStorage",
    "StorageLoader",
    "get_storage",
    "get_storage_status",
]
