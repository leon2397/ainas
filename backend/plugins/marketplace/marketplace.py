from loguru import logger
"""
插件市场系统
生态化扩展 - Phase 4.2
支持插件发布、安装、管理
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
import json
import zipfile
import shutil
from pathlib import Path


class PluginType(Enum):
    """插件类型"""
    STORAGE = "storage"
    AI = "ai"
    UI = "ui"
    TOOL = "tool"
    INTEGRATION = "integration"


class PluginStatus(Enum):
    """插件状态"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    PUBLISHED = "published"


@dataclass
class Plugin:
    """插件"""
    id: str
    name: str
    version: str
    description: str
    author: str
    plugin_type: PluginType
    tags: List[str]
    download_url: Optional[str]
    icon_url: Optional[str]
    readme: str
    requirements: List[str]
    config_schema: Dict
    status: PluginStatus
    downloads: int
    rating: float
    rating_count: int
    created_at: datetime
    updated_at: datetime
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "plugin_type": self.plugin_type.value,
            "tags": self.tags,
            "download_url": self.download_url,
            "icon_url": self.icon_url,
            "readme": self.readme,
            "requirements": self.requirements,
            "config_schema": self.config_schema,
            "status": self.status.value,
            "downloads": self.downloads,
            "rating": self.rating,
            "rating_count": self.rating_count,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


@dataclass
class InstalledPlugin:
    """已安装插件"""
    plugin_id: str
    version: str
    install_path: str
    config: Dict
    enabled: bool
    installed_at: datetime
    last_updated: datetime


class PluginMarketplace:
    """插件市场"""
    
    def __init__(self, storage_path: str = "data/marketplace"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self._plugins: Dict[str, Plugin] = {}
        self._load_plugins()
    
    def _load_plugins(self):
        """加载插件列表"""
        plugins_file = self.storage_path / "plugins.json"
        if plugins_file.exists():
            with open(plugins_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for plugin_data in data:
                    plugin = Plugin(
                        id=plugin_data["id"],
                        name=plugin_data["name"],
                        version=plugin_data["version"],
                        description=plugin_data["description"],
                        author=plugin_data["author"],
                        plugin_type=PluginType(plugin_data["plugin_type"]),
                        tags=plugin_data["tags"],
                        download_url=plugin_data.get("download_url"),
                        icon_url=plugin_data.get("icon_url"),
                        readme=plugin_data["readme"],
                        requirements=plugin_data["requirements"],
                        config_schema=plugin_data["config_schema"],
                        status=PluginStatus(plugin_data["status"]),
                        downloads=plugin_data["downloads"],
                        rating=plugin_data["rating"],
                        rating_count=plugin_data["rating_count"],
                        created_at=datetime.fromisoformat(plugin_data["created_at"]),
                        updated_at=datetime.fromisoformat(plugin_data["updated_at"])
                    )
                    self._plugins[plugin.id] = plugin
    
    def _save_plugins(self):
        """保存插件列表"""
        plugins_file = self.storage_path / "plugins.json"
        data = [plugin.to_dict() for plugin in self._plugins.values()]
        with open(plugins_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    async def publish_plugin(self, plugin_data: Dict) -> Plugin:
        """发布插件"""
        import uuid
        
        plugin = Plugin(
            id=str(uuid.uuid4()),
            name=plugin_data["name"],
            version=plugin_data["version"],
            description=plugin_data["description"],
            author=plugin_data["author"],
            plugin_type=PluginType(plugin_data["plugin_type"]),
            tags=plugin_data.get("tags", []),
            download_url=plugin_data.get("download_url"),
            icon_url=plugin_data.get("icon_url"),
            readme=plugin_data.get("readme", ""),
            requirements=plugin_data.get("requirements", []),
            config_schema=plugin_data.get("config_schema", {}),
            status=PluginStatus.PENDING,
            downloads=0,
            rating=0.0,
            rating_count=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        self._plugins[plugin.id] = plugin
        self._save_plugins()
        
        return plugin
    
    async def search_plugins(self, 
                            query: str = "",
                            plugin_type: Optional[PluginType] = None,
                            tags: List[str] = None,
                            sort_by: str = "downloads") -> List[Plugin]:
        """搜索插件"""
        results = []
        
        for plugin in self._plugins.values():
            # 只返回已发布的插件
            if plugin.status != PluginStatus.PUBLISHED:
                continue
            
            # 搜索过滤
            if query:
                query_lower = query.lower()
                if (query_lower not in plugin.name.lower() and 
                    query_lower not in plugin.description.lower()):
                    continue
            
            # 类型过滤
            if plugin_type and plugin.plugin_type != plugin_type:
                continue
            
            # 标签过滤
            if tags:
                if not any(tag in plugin.tags for tag in tags):
                    continue
            
            results.append(plugin)
        
        # 排序
        if sort_by == "downloads":
            results.sort(key=lambda x: x.downloads, reverse=True)
        elif sort_by == "rating":
            results.sort(key=lambda x: x.rating, reverse=True)
        elif sort_by == "newest":
            results.sort(key=lambda x: x.created_at, reverse=True)
        
        return results
    
    async def get_plugin(self, plugin_id: str) -> Optional[Plugin]:
        """获取插件详情"""
        return self._plugins.get(plugin_id)
    
    async def rate_plugin(self, plugin_id: str, rating: int, user_id: str):
        """给插件评分"""
        plugin = self._plugins.get(plugin_id)
        if not plugin:
            return False
        
        # 更新评分
        total_rating = plugin.rating * plugin.rating_count + rating
        plugin.rating_count += 1
        plugin.rating = total_rating / plugin.rating_count
        plugin.updated_at = datetime.utcnow()
        
        self._save_plugins()
        return True
    
    async def increment_downloads(self, plugin_id: str):
        """增加下载计数"""
        plugin = self._plugins.get(plugin_id)
        if plugin:
            plugin.downloads += 1
            plugin.updated_at = datetime.utcnow()
            self._save_plugins()


class PluginManager:
    """插件管理器"""
    
    def __init__(self, plugins_dir: str = "backend/plugins/installed"):
        self.plugins_dir = Path(plugins_dir)
        self.plugins_dir.mkdir(parents=True, exist_ok=True)
        
        self._installed: Dict[str, InstalledPlugin] = {}
        self._load_installed()
    
    def _load_installed(self):
        """加载已安装插件"""
        installed_file = self.plugins_dir / "installed.json"
        if installed_file.exists():
            with open(installed_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for plugin_data in data:
                    plugin = InstalledPlugin(
                        plugin_id=plugin_data["plugin_id"],
                        version=plugin_data["version"],
                        install_path=plugin_data["install_path"],
                        config=plugin_data["config"],
                        enabled=plugin_data["enabled"],
                        installed_at=datetime.fromisoformat(plugin_data["installed_at"]),
                        last_updated=datetime.fromisoformat(plugin_data["last_updated"])
                    )
                    self._installed[plugin.plugin_id] = plugin
    
    def _save_installed(self):
        """保存已安装插件列表"""
        installed_file = self.plugins_dir / "installed.json"
        data = []
        for plugin in self._installed.values():
            data.append({
                "plugin_id": plugin.plugin_id,
                "version": plugin.version,
                "install_path": plugin.install_path,
                "config": plugin.config,
                "enabled": plugin.enabled,
                "installed_at": plugin.installed_at.isoformat(),
                "last_updated": plugin.last_updated.isoformat()
            })
        with open(installed_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    async def install_plugin(self, plugin_file: str, plugin_id: str) -> bool:
        """安装插件"""
        try:
            # 解压插件
            install_path = self.plugins_dir / plugin_id
            install_path.mkdir(exist_ok=True)
            
            with zipfile.ZipFile(plugin_file, 'r') as zip_ref:
                zip_ref.extractall(install_path)
            
            # 读取插件信息
            manifest_file = install_path / "manifest.json"
            if manifest_file.exists():
                with open(manifest_file, 'r', encoding='utf-8') as f:
                    manifest = json.load(f)
                
                # 创建已安装记录
                installed = InstalledPlugin(
                    plugin_id=plugin_id,
                    version=manifest["version"],
                    install_path=str(install_path),
                    config={},
                    enabled=False,  # 默认禁用，需要手动启用
                    installed_at=datetime.utcnow(),
                    last_updated=datetime.utcnow()
                )
                
                self._installed[plugin_id] = installed
                self._save_installed()
                
                return True
        
        except Exception as e:
            logger.info(f"安装插件失败: {e}")
            return False
    
    async def uninstall_plugin(self, plugin_id: str) -> bool:
        """卸载插件"""
        if plugin_id not in self._installed:
            return False
        
        plugin = self._installed[plugin_id]
        
        # 删除文件
        install_path = Path(plugin.install_path)
        if install_path.exists():
            shutil.rmtree(install_path)
        
        # 删除记录
        del self._installed[plugin_id]
        self._save_installed()
        
        return True
    
    async def enable_plugin(self, plugin_id: str) -> bool:
        """启用插件"""
        if plugin_id not in self._installed:
            return False
        
        self._installed[plugin_id].enabled = True
        self._installed[plugin_id].last_updated = datetime.utcnow()
        self._save_installed()
        
        return True
    
    async def disable_plugin(self, plugin_id: str) -> bool:
        """禁用插件"""
        if plugin_id not in self._installed:
            return False
        
        self._installed[plugin_id].enabled = False
        self._installed[plugin_id].last_updated = datetime.utcnow()
        self._save_installed()
        
        return True
    
    async def configure_plugin(self, plugin_id: str, config: Dict) -> bool:
        """配置插件"""
        if plugin_id not in self._installed:
            return False
        
        self._installed[plugin_id].config = config
        self._installed[plugin_id].last_updated = datetime.utcnow()
        self._save_installed()
        
        return True
    
    async def list_installed(self) -> List[Dict]:
        """列出已安装插件"""
        return [
            {
                "plugin_id": p.plugin_id,
                "version": p.version,
                "enabled": p.enabled,
                "installed_at": p.installed_at.isoformat()
            }
            for p in self._installed.values()
        ]
    
    async def get_enabled_plugins(self) -> List[InstalledPlugin]:
        """获取启用的插件"""
        return [p for p in self._installed.values() if p.enabled]


# 全局实例
plugin_marketplace = PluginMarketplace()
plugin_manager = PluginManager()
