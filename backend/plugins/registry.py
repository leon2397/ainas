from loguru import logger
"""
Plugin Registry
V6.0 Phase 3: 插件体系核心
管理所有已安装和可用的插件
"""

import json
import logging
from typing import Dict, List, Optional, Type
from pathlib import Path
from datetime import datetime
import importlib
import inspect

from plugins.base import (
    BasePlugin, PluginManifest, PluginType, PluginState,
    StoragePlugin, AIPlugin, IntegrationPlugin
)

logger = logger.bind(name="ai_nas.plugins.registry")


class PluginRegistry:
    """插件注册表"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self.plugins_dir = Path("backend/plugins/installed")
        self.plugins_dir.mkdir(parents=True, exist_ok=True)
        
        self._manifests: Dict[str, PluginManifest] = {}
        self._instances: Dict[str, BasePlugin] = {}
        self._builtin_plugins: Dict[str, Type[BasePlugin]] = {}
        
        self._load_builtin_plugins()
        self._load_installed_plugins()
    
    def _load_builtin_plugins(self):
        """加载内置插件"""
        # 注册内置插件类型
        from plugins.storage.local_storage import LocalStoragePlugin
        from plugins.storage.ssh_storage import SSHStoragePlugin
        from plugins.storage.smb_storage import SMBStoragePlugin, NASStoragePlugin
        # 注意：NASStoragePlugin（带 PluginManifest、SMB/CIFS 协议）定义在 smb_storage.py；
        # nas_storage.py 中的 NasStorage 是 NFS/直挂载变体，类名不同，勿混用
        
        self._builtin_plugins["local"] = LocalStoragePlugin
        self._builtin_plugins["ssh"] = SSHStoragePlugin
        self._builtin_plugins["smb"] = SMBStoragePlugin
        self._builtin_plugins["nas"] = NASStoragePlugin

        # 将内置插件的 manifest 登记到 _manifests（以注册键为键），
        # 使 get_manifest / list_by_type / 插件详情接口对内置插件生效
        for plugin_id, plugin_class in self._builtin_plugins.items():
            get_manifest = getattr(plugin_class, "get_manifest", None)
            if get_manifest is None:
                continue
            try:
                manifest = get_manifest()
            except Exception as e:
                logger.warning(f"Builtin plugin {plugin_id} manifest load failed: {e}")
                continue
            if manifest is not None:
                self._manifests[plugin_id] = manifest

        logger.info(f"Loaded {len(self._builtin_plugins)} builtin plugins")
    
    def _load_installed_plugins(self):
        """加载已安装插件"""
        manifest_file = self.plugins_dir / "manifests.json"
        if manifest_file.exists():
            with open(manifest_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for plugin_data in data:
                    manifest = PluginManifest.from_dict(plugin_data)
                    self._manifests[manifest.id] = manifest
    
    def _save_manifests(self):
        """保存插件清单（仅第三方安装插件，内置插件不落盘）"""
        manifest_file = self.plugins_dir / "manifests.json"
        data = [
            m.to_dict() for pid, m in self._manifests.items()
            if pid not in self._builtin_plugins
        ]
        with open(manifest_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def register_builtin(self, plugin_id: str, plugin_class: Type[BasePlugin]):
        """注册内置插件"""
        self._builtin_plugins[plugin_id] = plugin_class
        logger.info(f"Registered builtin plugin: {plugin_id}")
    
    def register(self, manifest: PluginManifest, plugin_instance: BasePlugin):
        """注册插件"""
        self._manifests[manifest.id] = manifest
        self._instances[manifest.id] = plugin_instance
        self._save_manifests()
    
    def unregister(self, plugin_id: str) -> bool:
        """取消注册插件"""
        if plugin_id in self._instances:
            plugin = self._instances[plugin_id]
            plugin.cleanup()
            del self._instances[plugin_id]
        
        if plugin_id in self._manifests:
            del self._manifests[plugin_id]
        
        self._save_manifests()
        return True
    
    def get(self, plugin_id: str) -> Optional[BasePlugin]:
        """获取插件实例"""
        return self._instances.get(plugin_id)
    
    def get_manifest(self, plugin_id: str) -> Optional[PluginManifest]:
        """获取插件清单"""
        return self._manifests.get(plugin_id)
    
    def list_all(self) -> List[Dict]:
        """列出所有插件"""
        result = []
        
        # 内置插件
        for plugin_id, plugin_class in self._builtin_plugins.items():
            manifest = self._manifests.get(plugin_id)
            
            result.append({
                "id": plugin_id,
                "name": plugin_class.__name__,
                "type": "builtin",
                "state": "available",
                "enabled": self._instances.get(plugin_id) is not None,
                "manifest": manifest.to_dict() if manifest else None
            })
        
        # 已安装插件
        for plugin_id, manifest in self._manifests.items():
            if plugin_id not in self._builtin_plugins:
                instance = self._instances.get(plugin_id)
                result.append({
                    "id": plugin_id,
                    "name": manifest.name,
                    "type": "installed",
                    "version": manifest.version,
                    "state": instance.state.value if instance else "installed",
                    "enabled": instance is not None,
                    "manifest": manifest.to_dict()
                })
        
        return result
    
    def list_by_type(self, plugin_type: PluginType) -> List[Dict]:
        """按类型列出插件"""
        all_plugins = self.list_all()
        return [
            p for p in all_plugins 
            if p.get("manifest") and 
               p["manifest"].get("plugin_type") == plugin_type.value
        ]
    
    def enable(self, plugin_id: str) -> bool:
        """启用插件"""
        instance = self.get(plugin_id)
        if instance:
            if instance.enable():
                instance.state = PluginState.ENABLED
                return True
        return False
    
    def disable(self, plugin_id: str) -> bool:
        """禁用插件"""
        instance = self.get(plugin_id)
        if instance:
            if instance.disable():
                instance.state = PluginState.DISABLED
                return True
        return False
    
    def install_from_zip(self, zip_path: str) -> Optional[str]:
        """从ZIP文件安装插件"""
        import zipfile
        import shutil
        
        try:
            extract_dir = self.plugins_dir / "temp"
            extract_dir.mkdir(exist_ok=True)
            
            with zipfile.ZipFile(zip_path, 'r') as zf:
                zf.extractall(extract_dir)
            
            # 查找manifest.json
            manifest_file = None
            for json_file in extract_dir.rglob("manifest.json"):
                manifest_file = json_file
                break
            
            if not manifest_file:
                logger.error("No manifest.json found in plugin")
                shutil.rmtree(extract_dir)
                return None
            
            with open(manifest_file, 'r', encoding='utf-8') as f:
                manifest_data = json.load(f)
            
            manifest = PluginManifest.from_dict(manifest_data)
            
            # 移动到正确位置
            plugin_dir = self.plugins_dir / manifest.id
            if plugin_dir.exists():
                shutil.rmtree(plugin_dir)
            shutil.move(str(extract_dir), str(plugin_dir))
            
            # 注册插件
            self._manifests[manifest.id] = manifest
            self._save_manifests()
            
            logger.info(f"Installed plugin: {manifest.name}")
            return manifest.id
            
        except Exception as e:
            logger.error(f"Failed to install plugin: {e}")
            return None
    
    def uninstall(self, plugin_id: str) -> bool:
        """卸载插件"""
        if plugin_id in self._builtin_plugins:
            logger.warning(f"Cannot uninstall builtin plugin: {plugin_id}")
            return False
        
        # 清理实例
        if plugin_id in self._instances:
            self._instances[plugin_id].cleanup()
            del self._instances[plugin_id]
        
        # 删除文件
        plugin_dir = self.plugins_dir / plugin_id
        if plugin_dir.exists():
            import shutil
            shutil.rmtree(plugin_dir)
        
        # 移除清单
        if plugin_id in self._manifests:
            del self._manifests[plugin_id]
        
        self._save_manifests()
        return True


# 全局实例
registry = PluginRegistry()


def get_registry() -> PluginRegistry:
    """获取插件注册表"""
    return registry
