# File Storage Abstract Base Class
# V2.0 Phase 1: 架构修复 - 继承 StoragePlugin

from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from enum import Enum
from dataclasses import dataclass, field


class PluginType(Enum):
    """插件类型"""
    STORAGE = "storage"
    AI = "ai"
    UI = "ui"
    TOOL = "tool"
    INTEGRATION = "integration"


class PluginState(Enum):
    """插件状态"""
    UNINSTALLED = "uninstalled"
    INSTALLED = "installed"
    ENABLED = "enabled"
    DISABLED = "disabled"
    ERROR = "error"


@dataclass
class PluginManifest:
    """插件清单"""
    id: str = ""
    name: str = ""
    version: str = "1.0.0"
    description: str = ""
    author: str = ""
    plugin_type: PluginType = PluginType.STORAGE
    tags: List[str] = field(default_factory=list)
    icon: str = "plugin"
    homepage: str = ""
    requirements: List[str] = field(default_factory=list)
    config_schema: Dict = field(default_factory=dict)
    min_app_version: str = "6.0.0"
    permissions: List[str] = field(default_factory=list)


class StoragePlugin(ABC):
    """存储插件基类（最小实现）"""
    
    def __init__(self, manifest: PluginManifest = None, config: Dict = None):
        self.manifest = manifest or PluginManifest()
        self.config = config or {}
        self.state = PluginState.INSTALLED
    
    @abstractmethod
    def connect(self) -> bool:
        """连接存储"""
        pass
    
    @abstractmethod
    def disconnect(self) -> bool:
        """断开连接"""
        pass
    
    @abstractmethod
    def list_files(self, path: str = "/") -> List[Dict]:
        """列出文件"""
        pass
    
    @abstractmethod
    def upload_file(self, local_path: str, remote_path: str) -> bool:
        """上传文件"""
        pass
    
    @abstractmethod
    def download_file(self, remote_path: str, local_path: str) -> bool:
        """下载文件"""
        pass
    
    @abstractmethod
    def delete_file(self, path: str) -> bool:
        """删除文件"""
        pass


class FileStorage(StoragePlugin):
    """
    文件存储抽象基类
    
    继承链: StoragePlugin → FileStorage → 具体存储插件
    """
    
    @abstractmethod
    def get_exif(self, filepath: str) -> Dict:
        """读取文件 EXIF 信息"""
        pass
    
    @abstractmethod
    def create_symlink(self, target_path: str, link_path: str) -> bool:
        """创建软链接/快捷方式"""
        pass
    
    @abstractmethod
    def move_file(self, src_path: str, dst_path: str) -> bool:
        """移动文件（不复制，避免占用空间）"""
        pass
    
    @abstractmethod
    def is_support_symlink(self) -> bool:
        """判断当前存储是否支持软链接"""
        pass
    
    @abstractmethod
    def get_thumbnail(self, filepath: str, size: Tuple[int, int] = (200, 200)) -> bytes:
        """生成文件缩略图"""
        pass
    
    @abstractmethod
    def get_file_info(self, filepath: str) -> Dict:
        """获取文件详细信息"""
        pass
    
    def resolve_path(self, filepath: str) -> Path:
        """解析文件路径（辅助方法）"""
        raise NotImplementedError("子类需实现 resolve_path 方法")
