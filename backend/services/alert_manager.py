"""
告警通知模块
支持多种告警方式
"""

from loguru import logger
from typing import Dict, List, Optional, Callable
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from collections import deque
import asyncio


class AlertLevel(Enum):
    """告警级别"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertType(Enum):
    """告警类型"""
    SYSTEM = "system"
    TASK = "task"
    DEVICE = "device"
    SECURITY = "security"
    DATABASE = "database"


@dataclass
class Alert:
    """告警信息"""
    level: AlertLevel
    alert_type: AlertType
    title: str
    message: str
    device_id: Optional[str] = None
    task_id: Optional[str] = None
    metadata: Dict = field(default_factory=dict)
    created_at: str = ""
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


class AlertManager:
    """告警管理器"""
    
    def __init__(self, max_history: int = 100):
        self.max_history = max_history
        self.alerts: deque = deque(maxlen=max_history)
        self.handlers: Dict[AlertLevel, List[Callable]] = {
            AlertLevel.INFO: [],
            AlertLevel.WARNING: [],
            AlertLevel.ERROR: [],
            AlertLevel.CRITICAL: [],
        }
        self._alert_callbacks: List[Callable] = []
    
    def add_handler(self, level: AlertLevel, handler: Callable):
        """添加告警处理器"""
        if level not in self.handlers:
            self.handlers[level] = []
        self.handlers[level].append(handler)
    
    def on_alert(self, callback: Callable):
        """监听所有告警"""
        self._alert_callbacks.append(callback)
    
    def _notify_handlers(self, alert: Alert):
        """通知处理器"""
        handlers = self.handlers.get(alert.level, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    asyncio.create_task(handler(alert))
                else:
                    handler(alert)
            except Exception as e:
                logger.warning(f"Alert handler error: {e}")
        
        for callback in self._alert_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    asyncio.create_task(callback(alert))
                else:
                    callback(alert)
            except Exception as e:
                logger.warning(f"Alert callback error: {e}")
    
    def send_alert(
        self,
        level: AlertLevel,
        alert_type: AlertType,
        title: str,
        message: str,
        **kwargs
    ) -> Alert:
        """发送告警"""
        alert = Alert(
            level=level,
            alert_type=alert_type,
            title=title,
            message=message,
            **kwargs
        )
        self.alerts.append(alert)
        self._notify_handlers(alert)
        return alert
    
    def get_alerts(
        self,
        level: AlertLevel = None,
        alert_type: AlertType = None,
        limit: int = 50
    ) -> List[Dict]:
        """获取告警列表"""
        alerts = list(self.alerts)
        
        if level:
            alerts = [a for a in alerts if a.level == level]
        if alert_type:
            alerts = [a for a in alerts if a.alert_type == alert_type]
        
        alerts = alerts[-limit:]
        return [
            {
                "level": a.level.value,
                "type": a.alert_type.value,
                "title": a.title,
                "message": a.message,
                "device_id": a.device_id,
                "task_id": a.task_id,
                "created_at": a.created_at,
            }
            for a in reversed(alerts)
        ]
    
    def get_unread_count(self) -> Dict[str, int]:
        """获取未读告警数量"""
        counts = {}
        for level in AlertLevel:
            counts[level.value] = len([
                a for a in self.alerts if a.level == level
            ])
        return counts
    
    def clear_alerts(self):
        """清空告警"""
        self.alerts.clear()


class AlertLogger:
    """告警日志处理器"""
    
    def __init__(self, log_file: str = "./logs/alerts.log"):
        self.log_file = log_file
    
    def handle(self, alert: Alert):
        """记录告警到日志"""
        import os
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        
        log_entry = (
            f"[{alert.created_at}] [{alert.level.value.upper()}] "
            f"[{alert.alert_type.value}] {alert.title}: {alert.message}\n"
        )
        
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(log_entry)


# 全局限警管理器
alert_manager = AlertManager()

# 添加默认日志处理器
alert_logger = AlertLogger()
alert_manager.add_handler(AlertLevel.WARNING, alert_logger.handle)
alert_manager.add_handler(AlertLevel.ERROR, alert_logger.handle)
alert_manager.add_handler(AlertLevel.CRITICAL, alert_logger.handle)
