from loguru import logger
"""
数据库迁移脚本
用法：
  python migrations/run.py           # 运行所有未执行迁移
  python migrations/run.py --init   # 初始化迁移记录表（新建数据库时）
  python migrations/run.py --plan    # 查看待执行迁移（不实际运行）
  python migrations/run.py --version # 查看当前版本
  python migrations/run.py --history # 查看执行历史
  python migrations/run.py --rollback [N] # 回滚最近 N 个迁移（默认 1）

设计原则：
  - 向后兼容：只能 ADD COLUMN，禁止 DROP/CHANGE
  - 每个迁移可重复执行（幂等）
  - 失败自动回滚事务
"""

import sys
import os
import sqlite3
from pathlib import Path
from typing import Optional

# ─── 路径配置 ──────────────────────────────────────────────────────────────

DATABASE_PATH = os.environ.get(
    "AI_NAS_DB_PATH",
    str(Path(__file__).parent.parent / "data" / "metadata.db"),
)
SCHEMA_VERSION_TABLE = "_schema_migrations"

# ─── 迁移注册表（按版本号升序排列）────────────────────────────────────────
# 每个迁移由多条 SQL 组成，逐条执行
# 幂等设计：CREATE TABLE IF NOT EXISTS / CREATE INDEX IF NOT EXISTS（SQLite 3.32.0+）

MIGRATIONS: list[dict] = [
    {
        "version": 1,
        "description": "v1: 初始建表",
        "sqls": [
            # media_files（含 AI 相关字段）
            """
            CREATE TABLE IF NOT EXISTS media_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL UNIQUE,
                file_name TEXT NOT NULL,
                file_type TEXT NOT NULL,
                file_size INTEGER, mime_type TEXT,
                width INTEGER, height INTEGER, duration REAL,
                taken_at DATETIME, camera_make TEXT, camera_model TEXT,
                gps_lat REAL, gps_lon REAL,
                tags TEXT, people_ids TEXT, feature_vector BLOB,
                ai_confidence REAL, ai_processed INTEGER DEFAULT 0,
                ai_tags TEXT, face_count INTEGER DEFAULT 0, person_name TEXT,
                device_id TEXT, original_path TEXT, album_path TEXT,
                is_archived INTEGER DEFAULT 0, is_deleted INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                indexed_at DATETIME
            )
            """,
            # 索引（SQLite 3.32.0+ 支持 IF NOT EXISTS）
            "CREATE INDEX IF NOT EXISTS idx_file_type ON media_files(file_type)",
            "CREATE INDEX IF NOT EXISTS idx_taken_at ON media_files(taken_at)",
            "CREATE INDEX IF NOT EXISTS idx_ai_processed ON media_files(ai_processed)",
            "CREATE INDEX IF NOT EXISTS idx_device_id ON media_files(device_id)",
            "CREATE INDEX IF NOT EXISTS idx_is_archived ON media_files(is_archived)",
            "CREATE INDEX IF NOT EXISTS idx_created_at ON media_files(created_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_updated_at ON media_files(updated_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_is_deleted ON media_files(is_deleted)",
            "CREATE INDEX IF NOT EXISTS idx_ai_tags ON media_files(ai_tags)",
            # FTS5
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS media_fts USING fts5(
                file_name, tags, content='media_files', content_rowid='id'
            )
            """,
            # FTS 触发器（幂等：先删后建）
            "DROP TRIGGER IF EXISTS media_fts_insert",
            "DROP TRIGGER IF EXISTS media_fts_delete",
            "DROP TRIGGER IF EXISTS media_fts_update",
            """
            CREATE TRIGGER media_fts_insert AFTER INSERT ON media_files
            BEGIN INSERT INTO media_fts(rowid,file_name,tags) VALUES(new.id,new.file_name,new.tags); END
            """,
            """
            CREATE TRIGGER media_fts_delete AFTER DELETE ON media_files
            BEGIN INSERT INTO media_fts(media_fts,rowid,file_name,tags) VALUES('delete',old.id,old.file_name,old.tags); END
            """,
            """
            CREATE TRIGGER media_fts_update AFTER UPDATE ON media_files
            BEGIN INSERT INTO media_fts(media_fts,rowid,file_name,tags) VALUES('delete',old.id,old.file_name,old.tags);
                  INSERT INTO media_fts(rowid,file_name,tags) VALUES(new.id,new.file_name,new.tags); END
            """,
            # albums
            """
            CREATE TABLE IF NOT EXISTS albums (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                album_name TEXT NOT NULL, album_type TEXT NOT NULL,
                album_description TEXT, parent_id INTEGER, cover_file_id INTEGER,
                file_count INTEGER DEFAULT 0, is_smart INTEGER DEFAULT 0,
                smart_query TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (cover_file_id) REFERENCES media_files(id)
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_album_type ON albums(album_type)",
            # album_files
            """
            CREATE TABLE IF NOT EXISTS album_files (
                album_id INTEGER NOT NULL, file_id INTEGER NOT NULL,
                added_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (album_id, file_id),
                FOREIGN KEY (album_id) REFERENCES albums(id),
                FOREIGN KEY (file_id) REFERENCES media_files(id)
            )
            """,
            # tasks
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT, task_id TEXT NOT NULL UNIQUE,
                task_type TEXT NOT NULL, device_id TEXT, status TEXT NOT NULL,
                params TEXT, result TEXT, progress INTEGER DEFAULT 0,
                error_msg TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                started_at DATETIME, finished_at DATETIME
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_task_status ON tasks(status)",
            "CREATE INDEX IF NOT EXISTS idx_task_type ON tasks(task_type)",
            # users
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL UNIQUE,
                hashed_password TEXT NOT NULL, salt TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'viewer', disabled INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_user_username ON users(username)",
            # devices
            """
            CREATE TABLE IF NOT EXISTS devices (
                id INTEGER PRIMARY KEY AUTOINCREMENT, device_id TEXT NOT NULL UNIQUE,
                device_name TEXT, ip_address TEXT, port INTEGER, npu_type TEXT,
                status TEXT DEFAULT 'offline', cpu_usage REAL, npu_usage REAL,
                storage_usage REAL, last_seen DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """,
            # ai_tags
            """
            CREATE TABLE IF NOT EXISTS ai_tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tag_name TEXT NOT NULL UNIQUE,
                tag_count INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """,
            # media_similar
            """
            CREATE TABLE IF NOT EXISTS media_similar (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id INTEGER NOT NULL,
                similar_ids TEXT,
                similarity REAL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (file_id) REFERENCES media_files(id)
            )
            """,
        ],
    },
    # ── 在此处添加未来的迁移 ────────────────────────────────────────────
    # {
    #     "version": 2,
    #     "description": "v2: 添加媒体文件 Exif 字段",
    #     "sqls": [
    #         "ALTER TABLE media_files ADD COLUMN exif_data TEXT",
    #         "ALTER TABLE media_files ADD COLUMN quality_score REAL",
    #     ],
    # },
]


# ─── 核心迁移引擎 ─────────────────────────────────────────────────────────

class MigrationEngine:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None

    def _connect(self):
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.execute("PRAGMA foreign_keys = ON")

    def _close(self):
        if self._conn:
            self._conn.close()
            self._conn = None

    def _ensure_migrations_table(self):
        """确保迁移记录表存在"""
        self._connect()
        self._conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {SCHEMA_VERSION_TABLE} (
                version INTEGER PRIMARY KEY,
                description TEXT,
                applied_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self._conn.commit()
        self._close()

    def _get_applied_versions(self) -> set[int]:
        self._connect()
        self._conn.execute(f"CREATE TABLE IF NOT EXISTS {SCHEMA_VERSION_TABLE} (version INTEGER PRIMARY KEY, description TEXT, applied_at DATETIME DEFAULT CURRENT_TIMESTAMP)")
        rows = self._conn.execute(
            f"SELECT version FROM {SCHEMA_VERSION_TABLE} ORDER BY version"
        ).fetchall()
        self._close()
        return {row[0] for row in rows}

    def _record_migration(self, version: int, description: str):
        self._connect()
        self._conn.execute(
            f"INSERT OR IGNORE INTO {SCHEMA_VERSION_TABLE} (version, description) VALUES (?, ?)",
            (version, description),
        )
        self._conn.commit()
        self._close()

    def _get_current_version(self) -> int:
        self._connect()
        self._conn.execute(f"CREATE TABLE IF NOT EXISTS {SCHEMA_VERSION_TABLE} (version INTEGER PRIMARY KEY, description TEXT, applied_at DATETIME DEFAULT CURRENT_TIMESTAMP)")
        row = self._conn.execute(
            f"SELECT MAX(version) FROM {SCHEMA_VERSION_TABLE}"
        ).fetchone()
        self._close()
        return row[0] or 0

    def _run_sqls(self, sqls: list[str], dry_run: bool = False) -> list[tuple[str, Optional[str]]]:
        """
        逐条执行 SQL，返回 [(sql, error)] 列表。
        错误记录但不中断（幂等设计），除非是致命错误。
        """
        results: list[tuple[str, Optional[str]]] = []
        for sql in sqls:
            sql = sql.strip()
            if not sql:
                continue
            try:
                self._conn.execute(sql)
            except sqlite3.OperationalError as e:
                err = str(e)
                # 忽略常见的"不存在"类错误（幂等设计）
                safe_errors = (
                    "already exists",
                    "no such table",
                    "no such column",
                    "duplicate column name",
                )
                if not any(e2 in err.lower() for e2 in safe_errors):
                    results.append((sql, err))
                # else: 幂等，忽略
            except Exception as e:
                results.append((sql, str(e)))
        return results

    def run(self, target_version: Optional[int] = None, dry_run: bool = False):
        """执行所有未执行的迁移"""
        self._ensure_migrations_table()
        applied = self._get_applied_versions()
        pending = [m for m in MIGRATIONS if m["version"] not in applied]

        if target_version is not None:
            pending = [m for m in pending if m["version"] <= target_version]

        if not pending:
            v = self._get_current_version()
            logger.info(f"[OK] Database is at version v{v} (no pending migrations)")
            return

        for m in pending:
            version, desc = m["version"], m["description"]
            logger.info(f"[>>] Applying migration v{version}: {desc}")

            if dry_run:
                logger.info(f"     [dry-run] Skipping execution")
                continue

            self._connect()
            try:
                errors = self._run_sqls(m["sqls"])
                if errors:
                    # 有非幂等错误，打印警告但不中断
                    for sql, err in errors:
                        logger.info(f"     [WARN] '{sql[:60]}...' failed: {err}")
                self._conn.commit()
                self._record_migration(version, desc)
                logger.info(f"[OK] v{version} done ({len(m['sqls'])} statements)")
            except Exception as e:
                self._conn.rollback()
                logger.info(f"[FAIL] v{version} failed: {e}")
                logger.info(f"     [INFO] Transaction rolled back - no data loss")
                self._close()
                raise SystemExit(1) from e
            finally:
                self._close()

        v = self._get_current_version()
        logger.info(f"[OK] All migrations applied, current version: v{v}")

    def rollback(self, steps: int = 1):
        """回滚最近 N 个迁移（仅限有 down SQL 的迁移）"""
        applied = sorted(self._get_applied_versions(), reverse=True)
        undone = 0
        for v in applied:
            if undone >= steps:
                break
            m = next((m for m in MIGRATIONS if m["version"] == v), None)
            down_sqls = m.get("down_sqls", []) if m else []
            if not down_sqls:
                logger.info(f"[SKIP] v{v} has no rollback defined, skipping")
                continue

            logger.info(f"[<<] Rolling back v{v}: {m['description']}")
            self._connect()
            try:
                for sql in down_sqls:
                    sql = sql.strip()
                    if sql:
                        self._conn.execute(sql)
                self._conn.commit()
                self._conn.execute(
                    f"DELETE FROM {SCHEMA_VERSION_TABLE} WHERE version = ?", (v,)
                )
                self._conn.commit()
                logger.info(f"[OK] v{v} rolled back")
                undone += 1
            except Exception as e:
                self._conn.rollback()
                logger.info(f"[FAIL] Rollback v{v} failed: {e}")
                self._close()
                raise SystemExit(1) from e
            finally:
                self._close()

        if undone:
            logger.info(f"[OK] Rolled back {undone} migration(s)")
        else:
            logger.info("[OK] No migrations rolled back")

    def plan(self):
        """显示待执行的迁移"""
        applied = self._get_applied_versions()
        pending = [m for m in MIGRATIONS if m["version"] not in applied]
        if not pending:
            v = self._get_current_version()
            logger.info(f"[OK] Database is at version v{v} (no pending migrations)")
            return
        logger.info(f"Pending migrations ({len(pending)}):")
        for m in pending:
            logger.info(f"  v{m['version']}: {m['description']} ({len(m['sqls'])} statements)")

    def history(self):
        """显示迁移历史"""
        self._connect()
        self._conn.execute(f"CREATE TABLE IF NOT EXISTS {SCHEMA_VERSION_TABLE} (version INTEGER PRIMARY KEY, description TEXT, applied_at DATETIME DEFAULT CURRENT_TIMESTAMP)")
        rows = self._conn.execute(
            f"SELECT version, description, applied_at FROM {SCHEMA_VERSION_TABLE} ORDER BY version DESC"
        ).fetchall()
        self._close()
        if not rows:
            logger.info("[OK] No migration history")
            return
        logger.info("Migration history:")
        for v, desc, at in rows:
            logger.info(f"  v{v}: {desc}  ({at})")

    def current_version(self):
        v = self._get_current_version()
        logger.info(f"Current database version: v{v}")


# ─── CLI 入口 ──────────────────────────────────────────────────────────────

def main():
    engine = MigrationEngine(DATABASE_PATH)
    if len(sys.argv) < 2:
        # 无参数：运行所有待执行迁移（默认行为）
        engine.run()
        return

    cmd = sys.argv[1]

    if cmd in ("--help", "-h"):
        logger.info(__doc__)
    elif cmd == "--init":
        engine._ensure_migrations_table()
        engine.run()
    elif cmd == "--plan":
        engine.plan()
    elif cmd == "--version":
        engine.current_version()
    elif cmd == "--history":
        engine.history()
    elif cmd == "--dry-run":
        engine.run(dry_run=True)
    elif cmd == "--rollback":
        steps = int(sys.argv[2]) if len(sys.argv) > 2 else 1
        engine.rollback(steps=steps)
    else:
        engine.run()


if __name__ == "__main__":
    main()
