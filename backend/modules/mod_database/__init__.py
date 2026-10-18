"""
mod_database — AI-NAS 数据库模块

统一数据库访问接口，提供：
- Database 类：异步 SQLite 连接管理
- CRUD 操作：fetchone / fetchall / fetchval / execute
- 业务方法：媒体、相册、任务、设备、用户
- 迁移管理：Schema 版本控制

使用方式：
    from modules.mod_database import Database, get_db
"""

from modules.mod_database.db import Database, get_db, db, DATABASE_PATH

__all__ = [
    "Database",
    "get_db",
    "db",
    "DATABASE_PATH",
]
