"""
test_database.py - 数据库模块单元测试
=====================================
覆盖范围（对齐 modules.mod_database.Database 当前 API）：
  1. 数据库初始化与表/索引创建
  2. 媒体文件 CRUD（add_media_file / update_ai_analysis / search_media）
  3. 相册管理（create_album / get_albums）
  4. 用户管理（create_user / get_user_by_username / 改密码 / 改角色）
  5. 任务管理（create_task / update_task_status）

注意：Database 经重构已精简为「少量方法 + fetchall/fetchone/fetchval 原语」，
路由层均直接用原语写 SQL。本测试随之适配：已删除的便捷方法
（get_media_file / list_media_files / delete_media_file / get_media_count /
get_album / list_albums / add_media_to_album / get_task）对应的验证
统一改用原语查询，不再作为独立方法测试。

运行：
  cd backend
  pytest tests/unit/test_database.py -v
"""

import pytest
import sys
import os
from pathlib import Path

# 添加 backend 到 path
backend_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_root))

from modules.mod_database import Database


class TestDatabaseInit:
    """数据库初始化测试"""

    @pytest.mark.asyncio
    async def test_database_initialization(self):
        """测试数据库初始化"""
        db = Database(":memory:")
        await db.init()

        assert db is not None
        assert db._conn is not None

        await db.close()

    @pytest.mark.asyncio
    async def test_database_tables_created(self):
        """测试数据库表创建"""
        db = Database(":memory:")
        await db.init()

        tables = await db.fetchall(
            "SELECT name FROM sqlite_master WHERE type='table'",
            ()
        )
        table_names = [t["name"] for t in tables]

        assert "media_files" in table_names
        assert "albums" in table_names
        assert "users" in table_names
        assert "tasks" in table_names

        await db.close()


class TestMediaFiles:
    """媒体文件 CRUD 测试"""

    @pytest.fixture
    async def db(self):
        """创建测试数据库"""
        db = Database(":memory:")
        await db.init()
        yield db
        await db.close()

    @pytest.mark.asyncio
    async def test_add_media_file(self, db):
        """测试添加媒体文件（dict 入参）"""
        media_id = await db.add_media_file({
            "file_path": "/test/media/image.jpg",
            "file_name": "image.jpg",
            "file_type": "image",
            "file_size": 1024000,
            "mime_type": "image/jpeg"
        })

        assert media_id is not None
        assert isinstance(media_id, int)

    @pytest.mark.asyncio
    async def test_get_media_file(self, db):
        """测试获取媒体文件（原语查询）"""
        media_id = await db.add_media_file({
            "file_path": "/test/image.jpg",
            "file_name": "image.jpg",
            "file_type": "image",
            "file_size": 1024000
        })

        media = await db.fetchone(
            "SELECT * FROM media_files WHERE id = ?", (media_id,)
        )

        assert media is not None
        assert media["id"] == media_id
        assert media["file_path"] == "/test/image.jpg"
        assert media["file_name"] == "image.jpg"

    @pytest.mark.asyncio
    async def test_update_ai_analysis(self, db):
        """测试 AI 分析结果更新"""
        media_id = await db.add_media_file({
            "file_path": "/test/image.jpg",
            "file_name": "image.jpg",
            "file_type": "image"
        })

        await db.update_ai_analysis(
            media_id,
            tags=["nature", "landscape"],
            feature_vector=b"\x00\x01\x02",
            confidence=0.95
        )

        media = await db.fetchone(
            "SELECT * FROM media_files WHERE id = ?", (media_id,)
        )
        assert media["ai_processed"]  # SQLite TRUE 存为 1
        assert "nature" in media["tags"]

    @pytest.mark.asyncio
    async def test_delete_media_file(self, db):
        """测试软删除媒体文件（原语更新）"""
        media_id = await db.add_media_file({
            "file_path": "/test/image.jpg",
            "file_name": "image.jpg",
            "file_type": "image"
        })

        await db.execute(
            "UPDATE media_files SET is_deleted = TRUE WHERE id = ?",
            (media_id,)
        )

        media = await db.fetchone(
            "SELECT * FROM media_files WHERE id = ?", (media_id,)
        )
        assert media["is_deleted"]  # SQLite TRUE 存为 1

    @pytest.mark.asyncio
    async def test_list_media_files(self, db):
        """测试列出媒体文件（原语查询）"""
        for i in range(5):
            await db.add_media_file({
                "file_path": f"/test/image{i}.jpg",
                "file_name": f"image{i}.jpg",
                "file_type": "image"
            })

        files = await db.fetchall(
            "SELECT * FROM media_files WHERE is_deleted = FALSE LIMIT ?",
            (10,)
        )

        assert len(files) == 5

    @pytest.mark.asyncio
    async def test_search_media(self, db):
        """测试全文检索（FTS）"""
        await db.add_media_file({
            "file_path": "/test/nature.jpg",
            "file_name": "nature.jpg",
            "file_type": "image"
        })
        await db.add_media_file({
            "file_path": "/test/city.jpg",
            "file_name": "city.jpg",
            "file_type": "image"
        })

        results = await db.search_media("nature")

        assert len(results) == 1
        assert results[0]["file_name"] == "nature.jpg"

    @pytest.mark.asyncio
    async def test_get_media_count(self, db):
        """测试获取媒体数量（原语查询）"""
        for i in range(3):
            await db.add_media_file({
                "file_path": f"/test/image{i}.jpg",
                "file_name": f"image{i}.jpg",
                "file_type": "image"
            })

        count = await db.fetchval(
            "SELECT COUNT(*) FROM media_files WHERE is_deleted = FALSE"
        )

        assert count == 3


class TestAlbums:
    """相册测试"""

    @pytest.fixture
    async def db(self):
        db = Database(":memory:")
        await db.init()
        yield db
        await db.close()

    @pytest.mark.asyncio
    async def test_create_album(self, db):
        """测试创建相册"""
        album_id = await db.create_album("Test Album", "manual")

        assert album_id is not None
        assert isinstance(album_id, int)

    @pytest.mark.asyncio
    async def test_get_albums(self, db):
        """测试获取相册（含过滤）"""
        await db.create_album("Manual Album", "manual")
        await db.create_album("Smart Album", "smart")

        all_albums = await db.get_albums()
        assert len(all_albums) == 2

        manual = await db.get_albums(album_type="manual")
        assert len(manual) == 1
        assert manual[0]["album_name"] == "Manual Album"

    @pytest.mark.asyncio
    async def test_list_albums(self, db):
        """测试列出相册"""
        for i in range(3):
            await db.create_album(f"Album {i}", "manual")

        albums = await db.get_albums()

        assert len(albums) == 3


class TestUsers:
    """用户管理测试"""

    @pytest.fixture
    async def db(self):
        db = Database(":memory:")
        await db.init()
        yield db
        await db.close()

    @pytest.mark.asyncio
    async def test_create_user(self, db):
        """测试创建用户"""
        user_id = await db.create_user(
            username="testuser",
            hashed_password="hash123",
            salt="salt123",
            role="viewer"
        )

        assert user_id is not None

    @pytest.mark.asyncio
    async def test_get_user_by_username(self, db):
        """测试按用户名获取用户"""
        await db.create_user(
            username="testuser",
            hashed_password="hash123",
            salt="salt123",
            role="viewer"
        )

        user = await db.get_user_by_username("testuser")

        assert user is not None
        assert user["username"] == "testuser"
        assert user["role"] == "viewer"

    @pytest.mark.asyncio
    async def test_update_user_password(self, db):
        """测试更新密码"""
        await db.create_user(
            username="testuser",
            hashed_password="old_hash",
            salt="old_salt",
            role="viewer"
        )

        await db.update_user_password("testuser", "new_hash", "new_salt")

        user = await db.get_user_by_username("testuser")
        assert user["hashed_password"] == "new_hash"

    @pytest.mark.asyncio
    async def test_update_user_role(self, db):
        """测试更新角色"""
        await db.create_user(
            username="testuser",
            hashed_password="hash",
            salt="salt",
            role="viewer"
        )

        await db.update_user_role("testuser", "editor")

        user = await db.get_user_by_username("testuser")
        assert user["role"] == "editor"


class TestTasks:
    """任务管理测试"""

    @pytest.fixture
    async def db(self):
        db = Database(":memory:")
        await db.init()
        yield db
        await db.close()

    @pytest.mark.asyncio
    async def test_create_task(self, db):
        """测试创建任务"""
        task_id = await db.create_task(
            task_id="task-uuid-1",
            task_type="scan",
            device_id="device-1",
            params={"path": "/test"}
        )

        assert task_id is not None

    @pytest.mark.asyncio
    async def test_update_task_status(self, db):
        """测试更新任务状态"""
        await db.create_task(
            task_id="task-uuid-1",
            task_type="scan",
            device_id="device-1",
            params={"path": "/test"}
        )

        await db.update_task_status("task-uuid-1", "running")

        task = await db.fetchone(
            "SELECT * FROM tasks WHERE task_id = ?", ("task-uuid-1",)
        )
        assert task["status"] == "running"


class TestIndexes:
    """索引测试"""

    @pytest.mark.asyncio
    async def test_indexes_created(self):
        """测试索引已创建"""
        db = Database(":memory:")
        await db.init()

        indexes = await db.fetchall(
            "SELECT name, tbl_name FROM sqlite_master WHERE type='index'",
            ()
        )

        index_names = [idx["name"] for idx in indexes]

        assert any("file_type" in name for name in index_names)
        assert any("taken_at" in name for name in index_names)
        assert any("ai_processed" in name for name in index_names)

        await db.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
