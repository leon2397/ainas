"""
Database Module
SQLite + FTS5 for metadata storage
"""

import sqlite3
import json as _json
import asyncio
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime

import aiosqlite

from core.logger import logger
from core.exceptions import DatabaseError, DatabaseConnectionError

DATABASE_PATH = "./data/metadata.db"

# SQL for creating tables
CREATE_TABLES_SQL = """
-- Media files metadata table
CREATE TABLE IF NOT EXISTS media_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT NOT NULL UNIQUE,
    file_name TEXT NOT NULL,
    file_type TEXT NOT NULL,
    file_size INTEGER,
    mime_type TEXT,
    width INTEGER,
    height INTEGER,
    duration REAL,
    taken_at DATETIME,
    camera_make TEXT,
    camera_model TEXT,
    gps_lat REAL,
    gps_lon REAL,
    tags TEXT,
    people_ids TEXT,
    feature_vector BLOB,
    ai_confidence REAL,
    ai_processed BOOLEAN DEFAULT FALSE,
    device_id TEXT,
    original_path TEXT,
    album_path TEXT,
    is_archived BOOLEAN DEFAULT FALSE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    indexed_at DATETIME
);

CREATE INDEX IF NOT EXISTS idx_file_type ON media_files(file_type);
CREATE INDEX IF NOT EXISTS idx_taken_at ON media_files(taken_at);
CREATE INDEX IF NOT EXISTS idx_ai_processed ON media_files(ai_processed);
CREATE INDEX IF NOT EXISTS idx_device_id ON media_files(device_id);
CREATE INDEX IF NOT EXISTS idx_is_archived ON media_files(is_archived);
CREATE INDEX IF NOT EXISTS idx_created_at ON media_files(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_updated_at ON media_files(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_is_deleted ON media_files(is_deleted);

CREATE VIRTUAL TABLE IF NOT EXISTS media_fts USING fts5(
    file_name,
    tags,
    content='media_files',
    content_rowid='id'
);

CREATE TRIGGER IF NOT EXISTS media_fts_insert AFTER INSERT ON media_files
BEGIN
    INSERT INTO media_fts(rowid, file_name, tags) VALUES (new.id, new.file_name, new.tags);
END;

CREATE TRIGGER IF NOT EXISTS media_fts_delete AFTER DELETE ON media_files
BEGIN
    INSERT INTO media_fts(media_fts, rowid, file_name, tags) VALUES('delete', old.id, old.file_name, old.tags);
END;

CREATE TRIGGER IF NOT EXISTS media_fts_update AFTER UPDATE ON media_files
BEGIN
    INSERT INTO media_fts(media_fts, rowid, file_name, tags) VALUES('delete', old.id, old.file_name, old.tags);
    INSERT INTO media_fts(rowid, file_name, tags) VALUES (new.id, new.file_name, new.tags);
END;

CREATE TABLE IF NOT EXISTS albums (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    album_name TEXT NOT NULL,
    album_type TEXT NOT NULL,
    parent_id INTEGER,
    cover_file_id INTEGER,
    file_count INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (cover_file_id) REFERENCES media_files(id)
);

CREATE TABLE IF NOT EXISTS album_files (
    album_id INTEGER NOT NULL,
    file_id INTEGER NOT NULL,
    added_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (album_id, file_id),
    FOREIGN KEY (album_id) REFERENCES albums(id),
    FOREIGN KEY (file_id) REFERENCES media_files(id)
);

CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL UNIQUE,
    task_type TEXT NOT NULL,
    device_id TEXT,
    status TEXT NOT NULL,
    params TEXT,
    result TEXT,
    progress INTEGER DEFAULT 0,
    error_msg TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    started_at DATETIME,
    finished_at DATETIME
);

CREATE INDEX IF NOT EXISTS idx_task_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_task_type ON tasks(task_type);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    hashed_password TEXT NOT NULL,
    salt TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'viewer',
    disabled BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_user_username ON users(username);

CREATE TABLE IF NOT EXISTS devices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id TEXT NOT NULL UNIQUE,
    device_name TEXT,
    ip_address TEXT,
    port INTEGER,
    npu_type TEXT,
    status TEXT DEFAULT 'offline',
    cpu_usage REAL,
    npu_usage REAL,
    storage_usage REAL,
    last_seen DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ai_tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tag_name TEXT NOT NULL UNIQUE,
    tag_count INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS media_similar (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id INTEGER NOT NULL,
    similar_ids TEXT,
    similarity REAL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (file_id) REFERENCES media_files(id)
);
"""


class Database:
    """统一数据库访问接口"""

    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path
        self._conn: Optional[aiosqlite.Connection] = None

    async def init(self):
        """初始化数据库连接并创建表结构"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = await aiosqlite.connect(self.db_path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.executescript(CREATE_TABLES_SQL)
        await self._conn.commit()
        logger.info(f"数据库初始化完成: {self.db_path}")

    async def close(self):
        """关闭数据库连接"""
        if self._conn:
            await self._conn.close()
            self._conn = None
            logger.debug("数据库连接已关闭")

    # ── 基础查询接口 ─────────────────────────────────────────────────────

    async def execute(self, sql: str, params: tuple = ()) -> None:
        """
        执行 INSERT/UPDATE/DELETE 语句
        注意：不返回结果；如需获取插入 ID，用 insert_id()
        """
        if not self._conn:
            await self.init()
        await self._conn.execute(sql, params)
        await self._conn.commit()

    async def fetchone(self, sql: str, params: tuple = ()) -> Optional[Dict]:
        """查询一行，返回字典或 None"""
        if not self._conn:
            await self.init()
        cursor = await self._conn.execute(sql, params)
        row = await cursor.fetchone()
        if row:
            return dict(row)
        return None

    async def fetchall(self, sql: str, params: tuple = ()) -> List[Dict]:
        """查询多行，返回字典列表"""
        if not self._conn:
            await self.init()
        cursor = await self._conn.execute(sql, params)
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def fetchval(self, sql: str, params: tuple = ()) -> Any:
        """查询单个值（标量查询）"""
        row = await self.fetchone(sql, params)
        if row:
            return next(iter(row.values()))
        return None

    async def insert_id(self) -> int:
        """获取最后一次 INSERT 的自增 ID（必须在 execute 后立即调用）"""
        cursor = await self._conn.execute("SELECT last_insert_rowid()")
        row = await cursor.fetchone()
        return row[0]

    # ── 媒体文件 ─────────────────────────────────────────────────────────

    async def add_media_file(self, file_data: Dict[str, Any]) -> int:
        """添加媒体文件记录"""
        sql = """
        INSERT INTO media_files (
            file_path, file_name, file_type, file_size, mime_type,
            width, height, duration, taken_at, camera_make, camera_model,
            gps_lat, gps_lon, device_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            file_data.get('file_path'),
            file_data.get('file_name'),
            file_data.get('file_type'),
            file_data.get('file_size'),
            file_data.get('mime_type'),
            file_data.get('width'),
            file_data.get('height'),
            file_data.get('duration'),
            file_data.get('taken_at'),
            file_data.get('camera_make'),
            file_data.get('camera_model'),
            file_data.get('gps_lat'),
            file_data.get('gps_lon'),
            file_data.get('device_id'),
        )
        await self.execute(sql, params)
        return await self.insert_id()

    async def update_ai_analysis(self, file_id: int, tags: List[str],
                                  feature_vector: bytes, confidence: float) -> None:
        """更新 AI 分析结果"""
        await self.execute(
            """UPDATE media_files SET
                tags = ?, feature_vector = ?, ai_confidence = ?,
                ai_processed = TRUE, indexed_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
               WHERE id = ?""",
            (_json.dumps(tags), feature_vector, confidence, file_id)
        )

    async def search_media(self, keyword: str,
                            file_type: Optional[str] = None,
                            limit: int = 50) -> List[Dict]:
        """全文检索媒体文件"""
        if file_type:
            rows = await self.fetchall(
                """SELECT m.* FROM media_files m
                   JOIN media_fts f ON m.id = f.rowid
                   WHERE media_fts MATCH ? AND m.file_type = ?
                     AND m.is_deleted = FALSE
                   ORDER BY rank LIMIT ?""",
                (keyword, file_type, limit)
            )
        else:
            rows = await self.fetchall(
                """SELECT m.* FROM media_files m
                   JOIN media_fts f ON m.id = f.rowid
                   WHERE media_fts MATCH ? AND m.is_deleted = FALSE
                   ORDER BY rank LIMIT ?""",
                (keyword, limit)
            )
        return rows

    async def get_media_by_date(self, year: int,
                                  month: Optional[int] = None) -> List[Dict]:
        """按年月查询媒体"""
        if month:
            return await self.fetchall(
                """SELECT * FROM media_files
                   WHERE strftime('%Y', taken_at) = ?
                     AND strftime('%m', taken_at) = ?
                     AND is_deleted = FALSE
                   ORDER BY taken_at DESC""",
                (str(year), f"{month:02d}")
            )
        return await self.fetchall(
            """SELECT * FROM media_files
               WHERE strftime('%Y', taken_at) = ?
                 AND is_deleted = FALSE
               ORDER BY taken_at DESC""",
            (str(year),)
        )

    # ── 相册 ─────────────────────────────────────────────────────────────

    async def create_album(self, name: str, album_type: str,
                            parent_id: Optional[int] = None) -> int:
        """创建相册"""
        await self.execute(
            "INSERT INTO albums (album_name, album_type, parent_id) VALUES (?, ?, ?)",
            (name, album_type, parent_id)
        )
        return await self.insert_id()

    async def get_albums(self, album_type: Optional[str] = None) -> List[Dict]:
        """获取相册列表"""
        if album_type:
            return await self.fetchall(
                "SELECT * FROM albums WHERE album_type = ? ORDER BY album_name",
                (album_type,)
            )
        return await self.fetchall(
            "SELECT * FROM albums ORDER BY album_type, album_name"
        )

    # ── 任务 ────────────────────────────────────────────────────────────

    async def create_task(self, task_id: str, task_type: str,
                           device_id: str, params: Dict) -> int:
        """创建任务记录"""
        await self.execute(
            """INSERT INTO tasks
               (task_id, task_type, device_id, params, status)
               VALUES (?, ?, ?, ?, 'pending')""",
            (task_id, task_type, device_id, _json.dumps(params))
        )
        return await self.insert_id()

    async def update_task_status(self, task_id: str, status: str,
                                  progress: Optional[int] = None,
                                  error_msg: Optional[str] = None,
                                  result: Optional[str] = None) -> None:
        """更新任务状态。result 为 JSON 字符串（扫描统计等），写入即完结。"""
        if result is not None:
            await self.execute(
                """UPDATE tasks SET status = ?, result = ?, progress = 100,
                   finished_at = CURRENT_TIMESTAMP WHERE task_id = ?""",
                (status, result, task_id)
            )
        elif progress is not None:
            await self.execute(
                "UPDATE tasks SET status = ?, progress = ? WHERE task_id = ?",
                (status, progress, task_id)
            )
        elif error_msg:
            await self.execute(
                """UPDATE tasks SET status = ?, error_msg = ?,
                   finished_at = CURRENT_TIMESTAMP WHERE task_id = ?""",
                (status, error_msg, task_id)
            )
        else:
            await self.execute(
                """UPDATE tasks SET status = ?,
                   started_at = CASE WHEN started_at IS NULL
                                     THEN CURRENT_TIMESTAMP
                                     ELSE started_at END
                   WHERE task_id = ?""",
                (status, task_id)
            )

    # ── 设备 ────────────────────────────────────────────────────────────

    async def register_device(self, device_id: str, device_name: str,
                               ip_address: str, port: int = 8001,
                               npu_type: Optional[str] = None) -> None:
        """注册设备（upsert 语义）"""
        await self.execute(
            """INSERT INTO devices
               (device_id, device_name, ip_address, port, npu_type, status, last_seen)
               VALUES (?, ?, ?, ?, ?, 'online', CURRENT_TIMESTAMP)
               ON CONFLICT(device_id) DO UPDATE SET
                   device_name = excluded.device_name,
                   ip_address = excluded.ip_address,
                   port = excluded.port,
                   npu_type = excluded.npu_type,
                   status = 'online',
                   last_seen = CURRENT_TIMESTAMP""",
            (device_id, device_name, ip_address, port, npu_type)
        )

    async def update_device_status(self, device_id: str, status: str,
                                     cpu_usage: Optional[float] = None,
                                     npu_usage: Optional[float] = None) -> None:
        """更新设备状态"""
        await self.execute(
            """UPDATE devices SET status = ?, cpu_usage = ?,
               npu_usage = ?, last_seen = CURRENT_TIMESTAMP
               WHERE device_id = ?""",
            (status, cpu_usage, npu_usage, device_id)
        )

    async def get_online_devices(self) -> List[Dict]:
        """获取所有在线设备"""
        return await self.fetchall(
            "SELECT * FROM devices WHERE status = 'online'"
        )

    # ── 用户 ─────────────────────────────────────────────────────────────

    async def init_default_admin(self) -> Optional[str]:
        """
        首次启动时创建默认管理员
        返回：随机密码（供首次登录使用），或 None（已存在 admin）
        """
        existing = await self.fetchone(
            "SELECT id FROM users WHERE username = 'admin'"
        )
        if existing:
            return None

        import hashlib
        import secrets
        salt = secrets.token_hex(16)
        password = secrets.token_urlsafe(8)
        hashed = hashlib.pbkdf2_hmac(
            'sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000
        ).hex()

        await self.execute(
            """INSERT INTO users
               (username, hashed_password, salt, role, disabled)
               VALUES (?, ?, ?, 'admin', FALSE)""",
            ('admin', hashed, salt)
        )

        msg = (
            "\n" + "=" * 60 + "\n"
            "  Initial admin account created (persisted in DB)\n"
            f"  Username: admin\n"
            f"  Password: {password}\n"
            "  Please change your password after first login!\n"
            + "=" * 60 + "\n"
        )
        logger.info(msg)
        return password

    async def get_user_by_username(self, username: str) -> Optional[Dict]:
        """根据用户名查询用户"""
        return await self.fetchone(
            "SELECT * FROM users WHERE username = ?", (username,)
        )

    async def get_all_users(self) -> List[Dict]:
        """查询所有用户（不返回密码字段）"""
        return await self.fetchall(
            """SELECT id, username, role, disabled,
                      created_at, updated_at
               FROM users ORDER BY created_at"""
        )

    async def create_user(self, username: str, hashed_password: str,
                            salt: str, role: str = 'viewer') -> int:
        """创建用户"""
        await self.execute(
            """INSERT INTO users
               (username, hashed_password, salt, role)
               VALUES (?, ?, ?, ?)""",
            (username, hashed_password, salt, role)
        )
        return await self.insert_id()

    async def update_user_role(self, username: str, role: str) -> None:
        """更新用户角色"""
        await self.execute(
            """UPDATE users SET role = ?,
               updated_at = CURRENT_TIMESTAMP WHERE username = ?""",
            (role, username)
        )

    async def update_user_password(self, username: str,
                                     hashed_password: str,
                                     salt: str) -> None:
        """更新用户密码"""
        await self.execute(
            """UPDATE users SET hashed_password = ?, salt = ?,
               updated_at = CURRENT_TIMESTAMP WHERE username = ?""",
            (hashed_password, salt, username)
        )

    async def toggle_user_disabled(self, username: str,
                                    disabled: bool) -> None:
        """启用/禁用用户"""
        await self.execute(
            """UPDATE users SET disabled = ?,
               updated_at = CURRENT_TIMESTAMP WHERE username = ?""",
            (disabled, username)
        )

    async def delete_user(self, username: str) -> None:
        """删除用户（admin 不可删除）"""
        await self.execute(
            "DELETE FROM users WHERE username = ? AND username != 'admin'",
            (username,)
        )


# ── 全局单例 ─────────────────────────────────────────────────────────────

db = Database()

async def get_db() -> Database:
    """注入数据库实例（供 FastAPI Depends 使用）"""
    return db
