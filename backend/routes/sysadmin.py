"""
Admin API Routes
审计日志、系统配置、管理功能
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from datetime import datetime
from enum import Enum

from database.db import Database, get_db
from core.auth import get_current_user, require_admin

router = APIRouter(prefix="/api/system", tags=["System"])


# ============ Enums ============

class LogLevel(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    DEBUG = "DEBUG"


class LogCategory(str, Enum):
    AUTH = "auth"
    MEDIA = "media"
    ALBUM = "album"
    DEVICE = "device"
    TASK = "task"
    SYSTEM = "system"
    AI = "ai"
    USER = "user"
    CLOUD = "cloud"
    SYNC = "sync"


# ============ Audit Log Models ============

from pydantic import BaseModel


class AuditLogEntry(BaseModel):
    id: int
    timestamp: datetime
    level: str
    category: str
    username: str
    action: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    request_data: Optional[dict] = None
    response_data: Optional[dict] = None
    status: Optional[str] = None
    duration_ms: Optional[int] = None


class AuditLogList(BaseModel):
    logs: List[AuditLogEntry]
    total: int
    page: int
    page_size: int


# ============ In-Memory Audit Log Store ============

class AuditLogStore:
    """内存审计日志存储"""
    
    def __init__(self, max_logs: int = 10000):
        self.logs: List[dict] = []
        self.max_logs = max_logs
        self._log_id_counter = 1
    
    def add_log(self, entry: dict) -> int:
        """添加日志条目"""
        log_id = self._log_id_counter
        self._log_id_counter += 1
        
        log_entry = {
            "id": log_id,
            "timestamp": datetime.now(),
            "level": entry.get("level", "INFO"),
            "category": entry.get("category", "system"),
            "username": entry.get("username", "system"),
            "action": entry.get("action", ""),
            "ip_address": entry.get("ip_address"),
            "user_agent": entry.get("user_agent"),
            "request_data": entry.get("request_data"),
            "response_data": entry.get("response_data"),
            "status": entry.get("status", "success"),
            "duration_ms": entry.get("duration_ms")
        }
        
        self.logs.append(log_entry)
        
        # 保持最大日志数
        if len(self.logs) > self.max_logs:
            self.logs = self.logs[-self.max_logs:]
        
        return log_id
    
    def get_logs(
        self,
        level: Optional[str] = None,
        category: Optional[str] = None,
        username: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        keyword: Optional[str] = None,
        skip: int = 0,
        limit: int = 20
    ) -> tuple[List[dict], int]:
        """获取过滤后的日志"""
        filtered = self.logs.copy()
        filtered.reverse()  # 最新的在前
        
        # 应用过滤器
        if level:
            filtered = [l for l in filtered if l["level"] == level]
        if category:
            filtered = [l for l in filtered if l["category"] == category]
        if username:
            filtered = [l for l in filtered if username.lower() in (l["username"] or "").lower()]
        if start_date:
            filtered = [l for l in filtered if l["timestamp"] >= start_date]
        if end_date:
            filtered = [l for l in filtered if l["timestamp"] <= end_date]
        if keyword:
            filtered = [l for l in filtered if keyword.lower() in (l["action"] or "").lower()]
        
        total = len(filtered)
        paginated = filtered[skip:skip + limit]
        
        return paginated, total
    
    def get_stats(self) -> dict:
        """获取统计数据"""
        total = len(self.logs)
        by_level = {"INFO": 0, "WARNING": 0, "ERROR": 0, "DEBUG": 0}
        by_category = {}
        
        for log in self.logs:
            level = log.get("level", "INFO")
            if level in by_level:
                by_level[level] += 1
            
            cat = log.get("category", "system")
            by_category[cat] = by_category.get(cat, 0) + 1
        
        return {
            "total": total,
            "by_level": by_level,
            "by_category": by_category
        }
    
    def export_logs(self, format: str = "json", level: Optional[str] = None, category: Optional[str] = None) -> dict:
        """导出日志"""
        filtered = self.logs.copy()
        
        if level:
            filtered = [l for l in filtered if l["level"] == level]
        if category:
            filtered = [l for l in filtered if l["category"] == category]
        
        filtered.reverse()
        
        if format == "csv":
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=["id", "timestamp", "level", "category", "username", "action", "ip_address"])
            writer.writeheader()
            for log in filtered:
                row = log.copy()
                row["timestamp"] = row["timestamp"].isoformat()
                writer.writerow(row)
            
            return {"format": "csv", "data": output.getvalue()}
        else:
            return {
                "format": "json",
                "data": [
                    {
                        **log,
                        "timestamp": log["timestamp"].isoformat()
                    }
                    for log in filtered
                ]
            }


# 全局审计日志存储
audit_store = AuditLogStore()


# ============ Audit Log Routes ============

@router.get("/audit/logs", response_model=AuditLogList, tags=["Audit"])
async def get_audit_logs(
    level: Optional[str] = Query(None, description="日志级别"),
    category: Optional[str] = Query(None, description="日志类别"),
    username: Optional[str] = Query(None, description="用户名"),
    start_date: Optional[datetime] = Query(None, description="开始时间"),
    end_date: Optional[datetime] = Query(None, description="结束时间"),
    keyword: Optional[str] = Query(None, description="关键词搜索"),
    skip: int = Query(0, ge=0, description="跳过数量"),
    limit: int = Query(20, ge=1, le=100, description="返回数量"),
    current_user: dict = Depends(get_current_user)
):
    """获取审计日志列表"""
    init_sample_logs()  # 初始化示例数据
    logs, total = audit_store.get_logs(
        level=level,
        category=category,
        username=username,
        start_date=start_date,
        end_date=end_date,
        keyword=keyword,
        skip=skip,
        limit=limit
    )
    
    return {
        "logs": logs,
        "total": total,
        "page": skip // limit + 1,
        "page_size": limit
    }


@router.get("/audit/stats")
async def get_audit_stats(current_user: dict = Depends(get_current_user)):
    init_sample_logs()  # 初始化示例数据
    """获取审计统计数据"""
    return audit_store.get_stats()


@router.get("/audit/export")
async def export_audit_logs(
    format: str = Query("json", description="导出格式: json 或 csv"),
    level: Optional[str] = Query(None, description="日志级别"),
    category: Optional[str] = Query(None, description="日志类别"),
    current_user: dict = Depends(get_current_user)
):
    """导出审计日志"""
    return audit_store.export_logs(format=format, level=level, category=category)


@router.post("/audit/log")
async def create_audit_log(
    level: str = Query("INFO", description="日志级别"),
    category: str = Query("system", description="日志类别"),
    action: str = Query(..., description="操作描述"),
    current_user: dict = Depends(get_current_user)
):
    """手动创建审计日志"""
    log_id = audit_store.add_log({
        "level": level,
        "category": category,
        "username": current_user["username"],
        "action": action
    })
    
    return {"id": log_id, "status": "created"}


@router.get("/audit/logs/{log_id}")
async def get_audit_log_detail(
    log_id: int,
    current_user: dict = Depends(get_current_user)
):
    """获取单条审计日志详情"""
    init_sample_logs()  # 初始化示例数据
    log = next((l for l in audit_store.logs if l.get("id") == log_id), None)
    if not log:
        raise HTTPException(status_code=404, detail="Audit log not found")
    return {"log": log}


@router.delete("/audit/clear")
async def clear_audit_logs(current_user: dict = Depends(get_current_user)):
    """清空所有审计日志"""
    count = len(audit_store.logs)
    audit_store.logs = []
    return {"status": "cleared", "count": count}


# ============ System Routes ============

@router.get("/system/info")
async def get_system_info(current_user: dict = Depends(get_current_user)):
    """获取系统信息"""
    import platform
    import psutil
    
    return {
        "platform": platform.system(),
        "platform_version": platform.version(),
        "python_version": platform.python_version(),
        "cpu_count": psutil.cpu_count(),
        "memory_total": psutil.virtual_memory().total,
        "disk_total": psutil.disk_usage("/").total if platform.system() != "Windows" else psutil.disk_usage("C:\\").total,
        "hostname": platform.node()
    }


@router.get("/system/health")
async def get_system_health(current_user: dict = Depends(get_current_user)):
    """获取系统健康状态"""
    import psutil
    
    return {
        "cpu": {
            "usage": psutil.cpu_percent(interval=0.1),
            "count": psutil.cpu_count()
        },
        "memory": {
            "total": psutil.virtual_memory().total,
            "available": psutil.virtual_memory().available,
            "percent": psutil.virtual_memory().percent
        },
        "disk": {
            "total": psutil.disk_usage("/").total if platform.system() != "Windows" else psutil.disk_usage("C:\\").total,
            "used": psutil.disk_usage("/").used if platform.system() != "Windows" else psutil.disk_usage("C:\\").used,
            "free": psutil.disk_usage("/").free if platform.system() != "Windows" else psutil.disk_usage("C:\\").free,
            "percent": psutil.disk_usage("/").percent if platform.system() != "Windows" else psutil.disk_usage("C:\\").percent
        }
    }


@router.post("/system/cleanup")
async def cleanup_system(
    action: str = Query(..., description="清理操作: logs, cache, temp"),
    current_user: dict = Depends(require_admin)
):
    """系统清理操作"""
    import shutil
    import os
    
    results = {}
    
    if action == "logs":
        # 清理日志文件
        log_dir = os.path.join(os.path.dirname(__file__), "..", "..", "logs")
        if os.path.exists(log_dir):
            count = 0
            for f in os.listdir(log_dir):
                if f.endswith(".log"):
                    os.remove(os.path.join(log_dir, f))
                    count += 1
            results["logs"] = f"Deleted {count} log files"
    
    if action == "cache":
        # 清理缓存
        cache_dirs = [
            os.path.join(os.path.dirname(__file__), "..", "..", "data", "thumbnails"),
            os.path.join(os.path.dirname(__file__), "..", "..", "data", "chroma")
        ]
        for cache_dir in cache_dirs:
            if os.path.exists(cache_dir):
                count = sum(len(files) for _, _, files in os.walk(cache_dir))
                shutil.rmtree(cache_dir)
                os.makedirs(cache_dir, exist_ok=True)
                results[f"cache_{os.path.basename(cache_dir)}"] = f"Cleared {count} files"
    
    if action == "temp":
        # 清理临时文件
        temp_dir = tempfile.gettempdir()
        count = 0
        for f in os.listdir(temp_dir):
            if f.startswith("ai_nas_"):
                try:
                    os.remove(os.path.join(temp_dir, f))
                    count += 1
                except OSError:
                    pass  # 文件被占用或权限不足，静默跳过
        results["temp"] = f"Deleted {count} temp files"
    
    return {"status": "success", "results": results}


# ============ Initialize sample audit logs ============

def init_sample_logs():
    """初始化示例审计日志（延迟加载）"""
    import random
    
    if len(audit_store.logs) > 0:
        return  # 已经初始化
    
    sample_actions = [
        ("用户登录", "auth", "INFO"),
        ("浏览媒体库", "media", "INFO"),
        ("创建相册", "album", "INFO"),
        ("上传文件", "media", "INFO"),
        ("删除媒体", "media", "WARNING"),
        ("系统扫描", "system", "INFO"),
        ("AI标签生成", "ai", "INFO"),
        ("设备连接", "device", "INFO"),
        ("配置更新", "system", "WARNING"),
        ("API调用", "system", "INFO")
    ]
    
    usernames = ["admin", "user1", "user2", "system"]
    
    from datetime import timedelta
    now = datetime.now()
    
    for i in range(50):
        action, category, level = random.choice(sample_actions)
        username = random.choice(usernames)
        timestamp = now - timedelta(
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59),
            seconds=random.randint(0, 59)
        )
        
        audit_store.logs.append({
            "id": i + 1,
            "timestamp": timestamp,
            "level": level,
            "category": category,
            "username": username,
            "action": action,
            "ip_address": f"192.168.1.{random.randint(1, 254)}",
            "user_agent": "Mozilla/5.0",
            "request_data": None,
            "response_data": None,
            "status": "success",
            "duration_ms": random.randint(10, 500)
        })
    
    audit_store._log_id_counter = 51


import tempfile
import platform
