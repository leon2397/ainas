"""
mod_monitor — AI-NAS 系统监控模块

提供：
- 系统资源监控（CPU、内存、磁盘、网络）
- 服务健康检查
- 性能指标收集

使用方式：
    from modules.mod_monitor import SystemMonitor, get_monitor
"""

from modules.mod_monitor.monitor import SystemMonitor, get_monitor

__all__ = [
    "SystemMonitor",
    "get_monitor",
]
