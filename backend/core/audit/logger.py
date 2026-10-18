"""
审计日志系统
企业级功能 - Phase 2.2
"""

from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
import json
import asyncio
from pathlib import Path


class AuditLevel(str, Enum):
    """审计级别"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AuditCategory(str, Enum):
    """审计类别"""
    AUTH = "auth"                    # 认证相关
    USER = "user"                    # 用户管理
    MEDIA = "media"                  # 媒体操作
    ALBUM = "album"                  # 相册操作
    DEVICE = "device"                # 设备操作
    SYSTEM = "system"                # 系统操作
    CONFIG = "config"                # 配置变更
    SECURITY = "security"            # 安全事件
    ADMIN = "admin"                  # 管理操作


class AuditAction(str, Enum):
    """审计动作"""
    # 认证动作
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"
    PASSWORD_CHANGE = "password_change"
    TOKEN_REFRESH = "token_refresh"
    
    # 用户动作
    USER_CREATE = "user_create"
    USER_UPDATE = "user_update"
    USER_DELETE = "user_delete"
    USER_ENABLE = "user_enable"
    USER_DISABLE = "user_disable"
    ROLE_ASSIGN = "role_assign"
    ROLE_REVOKE = "role_revoke"
    
    # 媒体动作
    MEDIA_UPLOAD = "media_upload"
    MEDIA_DELETE = "media_delete"
    MEDIA_UPDATE = "media_update"
    MEDIA_VIEW = "media_view"
    MEDIA_DOWNLOAD = "media_download"
    MEDIA_SHARE = "media_share"
    MEDIA_SCAN = "media_scan"
    
    # 相册动作
    ALBUM_CREATE = "album_create"
    ALBUM_DELETE = "album_delete"
    ALBUM_UPDATE = "album_update"
    ALBUM_ADD_MEDIA = "album_add_media"
    ALBUM_REMOVE_MEDIA = "album_remove_media"
    
    # 设备动作
    DEVICE_REGISTER = "device_register"
    DEVICE_UNREGISTER = "device_unregister"
    DEVICE_UPDATE = "device_update"
    DEVICE_COMMAND = "device_command"
    
    # 系统动作
    SYSTEM_START = "system_start"
    SYSTEM_STOP = "system_stop"
    BACKUP_CREATE = "backup_create"
    BACKUP_RESTORE = "backup_restore"
    UPDATE_APPLY = "update_apply"
    
    # 配置动作
    CONFIG_CHANGE = "config_change"
    SETTING_UPDATE = "setting_update"
    
    # 安全动作
    PERMISSION_DENIED = "permission_denied"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    RATE_LIMIT_HIT = "rate_limit_hit"


@dataclass
class AuditLog:
    """审计日志条目"""
    id: str
    timestamp: datetime
    level: AuditLevel
    category: AuditCategory
    action: AuditAction
    user_id: Optional[str]
    user_name: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    resource_type: Optional[str]
    resource_id: Optional[str]
    description: str
    details: Dict[str, Any] = field(default_factory=dict)
    success: bool = True
    error_message: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "level": self.level.value,
            "category": self.category.value,
            "action": self.action.value,
            "user_id": self.user_id,
            "user_name": self.user_name,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "description": self.description,
            "details": self.details,
            "success": self.success,
            "error_message": self.error_message,
            "session_id": self.session_id,
            "request_id": self.request_id,
        }
    
    def to_json(self) -> str:
        """转换为 JSON"""
        return json.dumps(self.to_dict(), ensure_ascii=False, default=str)


class AuditLogger:
    """审计日志管理器"""
    
    def __init__(self, log_dir: str = "logs/audit", max_file_size: int = 10*1024*1024):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.max_file_size = max_file_size
        self._buffer: List[AuditLog] = []
        self._buffer_size = 100
        self._lock = asyncio.Lock()
        self._current_file: Optional[Path] = None
    
    def _get_log_file(self) -> Path:
        """获取当前日志文件"""
        today = datetime.now().strftime("%Y-%m-%d")
        return self.log_dir / f"audit_{today}.log"
    
    async def _write_to_file(self, log_entry: AuditLog):
        """写入日志文件"""
        log_file = self._get_log_file()
        
        async with self._lock:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(log_entry.to_json() + "\n")
    
    async def _flush_buffer(self):
        """刷新缓冲区"""
        if not self._buffer:
            return
        
        async with self._lock:
            log_file = self._get_log_file()
            with open(log_file, "a", encoding="utf-8") as f:
                for entry in self._buffer:
                    f.write(entry.to_json() + "\n")
            self._buffer.clear()
    
    async def log(self, level: AuditLevel, category: AuditCategory, action: AuditAction,
                  description: str, user_id: Optional[str] = None,
                  user_name: Optional[str] = None, ip_address: Optional[str] = None,
                  user_agent: Optional[str] = None, resource_type: Optional[str] = None,
                  resource_id: Optional[str] = None, details: Optional[Dict] = None,
                  success: bool = True, error_message: Optional[str] = None,
                  session_id: Optional[str] = None, request_id: Optional[str] = None) -> AuditLog:
        """记录审计日志"""
        import uuid
        
        log_entry = AuditLog(
            id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            level=level,
            category=category,
            action=action,
            description=description,
            user_id=user_id,
            user_name=user_name,
            ip_address=ip_address,
            user_agent=user_agent,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
            success=success,
            error_message=error_message,
            session_id=session_id,
            request_id=request_id,
        )
        
        # 添加到缓冲区
        self._buffer.append(log_entry)
        
        # 立即写入关键级别日志
        if level in [AuditLevel.ERROR, AuditLevel.CRITICAL]:
            await self._write_to_file(log_entry)
        
        # 缓冲区满时刷新
        if len(self._buffer) >= self._buffer_size:
            await self._flush_buffer()
        
        return log_entry
    
    # 便捷方法
    async def log_auth(self, action: AuditAction, description: str, **kwargs) -> AuditLog:
        """记录认证日志"""
        return await self.log(AuditLevel.INFO, AuditCategory.AUTH, action, description, **kwargs)
    
    async def log_user(self, action: AuditAction, description: str, **kwargs) -> AuditLog:
        """记录用户管理日志"""
        return await self.log(AuditLevel.INFO, AuditCategory.USER, action, description, **kwargs)
    
    async def log_media(self, action: AuditAction, description: str, **kwargs) -> AuditLog:
        """记录媒体操作日志"""
        return await self.log(AuditLevel.INFO, AuditCategory.MEDIA, action, description, **kwargs)
    
    async def log_security(self, level: AuditLevel, action: AuditAction, description: str, **kwargs) -> AuditLog:
        """记录安全日志"""
        return await self.log(level, AuditCategory.SECURITY, action, description, **kwargs)
    
    async def log_system(self, action: AuditAction, description: str, **kwargs) -> AuditLog:
        """记录系统日志"""
        return await self.log(AuditLevel.INFO, AuditCategory.SYSTEM, action, description, **kwargs)
    
    async def query_logs(self, start_time: Optional[datetime] = None,
                        end_time: Optional[datetime] = None,
                        level: Optional[AuditLevel] = None,
                        category: Optional[AuditCategory] = None,
                        action: Optional[AuditAction] = None,
                        user_id: Optional[str] = None,
                        limit: int = 100, offset: int = 0) -> List[AuditLog]:
        """查询审计日志"""
        logs = []
        
        # 读取日志文件
        log_files = sorted(self.log_dir.glob("audit_*.log"), reverse=True)
        
        for log_file in log_files:
            with open(log_file, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        data = json.loads(line)
                        log_time = datetime.fromisoformat(data["timestamp"])
                        
                        # 时间过滤
                        if start_time and log_time < start_time:
                            continue
                        if end_time and log_time > end_time:
                            continue
                        
                        # 级别过滤
                        if level and data["level"] != level.value:
                            continue
                        
                        # 类别过滤
                        if category and data["category"] != category.value:
                            continue
                        
                        # 动作过滤
                        if action and data["action"] != action.value:
                            continue
                        
                        # 用户过滤
                        if user_id and data.get("user_id") != user_id:
                            continue
                        
                        logs.append(data)
                    except (json.JSONDecodeError, KeyError):
                        continue
        
        # 排序和分页
        logs.sort(key=lambda x: x["timestamp"], reverse=True)
        return logs[offset:offset + limit]
    
    async def get_statistics(self, days: int = 7) -> Dict:
        """获取审计统计"""
        stats = {
            "total_logs": 0,
            "by_level": {},
            "by_category": {},
            "by_action": {},
            "by_user": {},
            "failed_actions": 0,
        }
        
        since = datetime.utcnow() - __import__('datetime').timedelta(days=days)
        logs = await self.query_logs(start_time=since, limit=10000)
        
        for log in logs:
            stats["total_logs"] += 1
            stats["by_level"][log["level"]] = stats["by_level"].get(log["level"], 0) + 1
            stats["by_category"][log["category"]] = stats["by_category"].get(log["category"], 0) + 1
            stats["by_action"][log["action"]] = stats["by_action"].get(log["action"], 0) + 1
            
            if log.get("user_id"):
                stats["by_user"][log["user_id"]] = stats["by_user"].get(log["user_id"], 0) + 1
            
            if not log.get("success", True):
                stats["failed_actions"] += 1
        
        return stats
    
    async def export_logs(self, format: str = "json", 
                         start_time: Optional[datetime] = None,
                         end_time: Optional[datetime] = None) -> str:
        """导出审计日志"""
        logs = await self.query_logs(start_time=start_time, end_time=end_time, limit=10000)
        
        if format == "json":
            return json.dumps(logs, ensure_ascii=False, indent=2)
        elif format == "csv":
            import csv
            import io
            
            output = io.StringIO()
            if logs:
                writer = csv.DictWriter(output, fieldnames=logs[0].keys())
                writer.writeheader()
                writer.writerows(logs)
            return output.getvalue()
        else:
            raise ValueError(f"Unsupported format: {format}")


# 全局审计日志实例
audit_logger = AuditLogger()
