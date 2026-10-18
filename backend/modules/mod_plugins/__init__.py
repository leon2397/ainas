"""
mod_plugins — AI-NAS 插件管理模块

提供：
- 插件加载与管理
- 插件生命周期控制
- 插件间通信

使用方式：
    from modules.mod_plugins import PluginManager, get_plugin_manager
"""

from modules.mod_plugins.manager import PluginManager, get_plugin_manager

__all__ = [
    "PluginManager",
    "get_plugin_manager",
]
