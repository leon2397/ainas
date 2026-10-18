from loguru import logger
"""
Plugin Base Classes
V6.0 Phase 3: 插件体系
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging

logger = logger.bind(name="ai_nas.plugins.base")


class PluginType(Enum):
    """插件类型"""
    STORAGE = "storage"           # 存储插件
    AI = "ai"                     # AI功能插件
    UI = "ui"                     # UI扩展插件
    TOOL = "tool"                 # 工具类插件
    INTEGRATION = "integration"   # 集成类插件


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
    id: str
    name: str
    version: str
    description: str
    author: str
    plugin_type: PluginType
    tags: List[str] = field(default_factory=list)
    icon: str = "plugin"
    homepage: str = ""
    requirements: List[str] = field(default_factory=list)
    config_schema: Dict[str, Any] = field(default_factory=dict)
    min_app_version: str = "6.0.0"
    permissions: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "plugin_type": self.plugin_type.value,
            "tags": self.tags,
            "icon": self.icon,
            "homepage": self.homepage,
            "requirements": self.requirements,
            "config_schema": self.config_schema,
            "min_app_version": self.min_app_version,
            "permissions": self.permissions
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'PluginManifest':
        return cls(
            id=data["id"],
            name=data["name"],
            version=data["version"],
            description=data["description"],
            author=data["author"],
            plugin_type=PluginType(data["plugin_type"]),
            tags=data.get("tags", []),
            icon=data.get("icon", "plugin"),
            homepage=data.get("homepage", ""),
            requirements=data.get("requirements", []),
            config_schema=data.get("config_schema", {}),
            min_app_version=data.get("min_app_version", "6.0.0"),
            permissions=data.get("permissions", [])
        )


class BasePlugin(ABC):
    """插件基类"""
    
    def __init__(self, manifest: PluginManifest, config: Dict):
        self.manifest = manifest
        self.config = config
        self.state = PluginState.INSTALLED
        self._logger = logger.bind(name=f"ai_nas.plugin.{manifest.id}")
    
    @abstractmethod
    def initialize(self) -> bool:
        """初始化插件"""
        pass
    
    @abstractmethod
    def enable(self) -> bool:
        """启用插件"""
        pass
    
    @abstractmethod
    def disable(self) -> bool:
        """禁用插件"""
        pass
    
    @abstractmethod
    def cleanup(self) -> bool:
        """清理插件资源"""
        pass
    
    def get_info(self) -> Dict:
        """获取插件信息"""
        return {
            "id": self.manifest.id,
            "name": self.manifest.name,
            "version": self.manifest.version,
            "state": self.state.value
        }
    
    def validate_config(self, config: Dict) -> bool:
        """验证配置"""
        schema = self.manifest.config_schema
        required = schema.get("required", [])
        
        for field_name in required:
            if field_name not in config:
                return False
        
        return True
    
    def update_config(self, config: Dict) -> bool:
        """更新配置"""
        if not self.validate_config(config):
            return False
        self.config = config
        return True


class StoragePlugin(BasePlugin):
    """存储插件基类"""
    
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
    def delete_file(self, remote_path: str) -> bool:
        """删除文件"""
        pass


class AIPlugin(BasePlugin):
    """AI插件基类"""
    
    @abstractmethod
    def process(self, data: Any) -> Dict:
        """处理数据"""
        pass
    
    @abstractmethod
    def get_capabilities(self) -> List[str]:
        """获取插件能力"""
        pass


class IntegrationPlugin(BasePlugin):
    """集成插件基类"""
    
    @abstractmethod
    def authenticate(self) -> bool:
        """认证"""
        pass
    
    @abstractmethod
    def sync(self) -> Dict:
        """同步数据"""
        pass
    
    @abstractmethod
    def get_status(self) -> Dict:
        """获取状态"""
        pass
