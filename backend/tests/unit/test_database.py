"""
test_database.py - 数据库模块单元测试
=====================================
覆盖范围：
  1. 数据库初始化
  2. CRUD 操作（媒体文件）
  3. 用户管理
  4. 索引与查询
  5. 事务处理

运行：
  cd backend
  pytest tests/unit/test_database.py -v
"""

import pytest
import sys
import os
import tempfile
import asyncio
from pathlib import Path
from datetime import datetime

# 设置测试环境
os.environ["AI_NAS_DB_PATH"] = ":memory:"

# 添加 backend 到 path
backend_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_root))

from database.db import Database


class TestDatabaseInit:
    """数据库初始化测试"""

    @pytest.mark.asyncio
    async def test_database_initialization(self):
        """测试数据库初始化"""
        db = Database(":memory:")
        await db.init()
        
        assert db is not None
        assert db._connection is not None
        
        await db.close()

    @pytest.mark.asyncio
    async def test_database_tables_created(self):
        """测试数据库表创建"""
        db = Database(":memory:")
        await db.init()
        
        # 检查表是否存在
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
        """测试添加媒体文件"""
        file_path = "/test/media/image.jpg"
        file_name = "image.jpg"
        file_type = "image"
        
        media_id = await db.add_media_file(
            file_path=file_path,
            file_name=file_name,
            file_type=file_type,
            file_size=1024000,
            mime_type="image/jpeg"
        )
        
        assert media_id is not None
        assert isinstance(media_id, int)

    @pytest.mark.asyncio
    async def test_get_media_file(self, db):
        """测试获取媒体文件"""
        # 添加文件
        media_id = await db.add_media_file(
            file_path="/test/image.jpg",
            file_name="image.jpg",
            file_type="image",
            file_size=1024000
        )
        
        # 获取文件
        media = await db.get_media_file(media_id)
        
        assert media is not None
        assert media["id"] == media_id
        assert media["file_path"] == "/test/image.jpg"
        assert media["file_name"] == "image.jpg"

    @pytest.mark.asyncio
    async def test_update_media_file(self, db):
        """测试更新媒体文件"""
        # 添加文件
        media_id = await db.add_media_file(
            file_path="/test/image.jpg",
            file_name="image.jpg",
            file_type="image"
        )
        
        # 更新文件
        await db.update_media_file(
            media_id,
            tags='["nature", "landscape"]',
            ai_processed=True
        )
        
        # 验证更新
        media = await db.get_media_file(media_id)
        assert media["tags"] == '["nature", "landscape"]'
        assert media["ai_processed"] is True

    @pytest.mark.asyncio
    async def test_delete_media_file(self, db):
        """测试删除媒体文件"""
        # 添加文件
        media_id = await db.add_media_file(
            file_path="/test/image.jpg",
            file_name="image.jpg",
            file_type="image"
        )
        
        # 软删除
        await db.delete_media_file(media_id)
        
        # 验证删除
        media = await db.get_media_file(media_id)
        assert media["is_deleted"] is True

    @pytest.mark.asyncio
    async def test_list_media_files(self, db):
        """测试列出媒体文件"""
        # 添加多个文件
        for i in range(5):
            await db.add_media_file(
                file_path=f"/test/image{i}.jpg",
                file_name=f"image{i}.jpg",
                file_type="image"
            )
        
        # 列出文件
        files = await db.list_media_files(limit=10)
        
        assert len(files) == 5

    @pytest.mark.asyncio
    async def test_search_media_by_tags(self, db):
        """测试按标签搜索"""
        # 添加带标签的文件
        await db.add_media_file(
            file_path="/test/nature.jpg",
            file_name="nature.jpg",
            file_type="image",
            tags='["nature", "landscape"]'
        )
        await db.add_media_file(
            file_path="/test/city.jpg",
            file_name="city.jpg",
            file_type="image",
            tags='["city", "urban"]'
        )
        
        # 搜索
        results = await db.search_media_by_tags(["nature"])
        
        assert len(results) == 1
        assert results[0]["file_name"] == "nature.jpg"

    @pytest.mark.asyncio
    async def test_get_media_count(self, db):
        """测试获取媒体数量"""
        # 添加文件
        for i in range(3):
            await db.add_media_file(
                file_path=f"/test/image{i}.jpg",
                file_name=f"image{i}.jpg",
                file_type="image"
            )
        
        count = await db.get_media_count()
        
        assert count == 3


class TestAlbums:
    """相册测试"""

    @pytest.fixture
    async def db(self):
        """创建测试数据库"""
        db = Database(":memory:")
        await db.init()
        yield db
        await db.close()

    @pytest.mark.asyncio
    async def test_create_album(self, db):
        """测试创建相册"""
        album_id = await db.create_album(
            name="Test Album",
            path="/test/album",
            cover_media_id=None
        )
        
        assert album_id is not None
        assert isinstance(album_id, int)

    @pytest.mark.asyncio
    async def test_get_album(self, db):
        """测试获取相册"""
        album_id = await db.create_album(
            name="Test Album",
            path="/test/album"
        )
        
        album = await db.get_album(album_id)
        
        assert album is not None
        assert album["name"] == "Test Album"

    @pytest.mark.asyncio
    async def test_list_albums(self, db):
        """测试列出相册"""
        # 创建多个相册
        for i in range(3):
            await db.create_album(
                name=f"Album {i}",
                path=f"/test/album{i}"
            )
        
        albums = await db.list_albums()
        
        assert len(albums) == 3

    @pytest.mark.asyncio
    async def test_add_media_to_album(self, db):
        """测试添加媒体到相册"""
        # 创建相册和媒体
        album_id = await db.create_album(name="Album", path="/test/album")
        media_id = await db.add_media_file(
            file_path="/test/image.jpg",
            file_name="image.jpg",
            file_type="image"
        )
        
        # 添加到相册
        await db.add_media_to_album(album_id, media_id)
        
        # 验证
        album = await db.get_album(album_id)
        assert album["media_count"] == 1


class TestUsers:
    """用户管理测试"""

    @pytest.fixture
    async def db(self):
        """创建测试数据库"""
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
        
        await db.update_user_password(
            "testuser",
            "new_hash",
            "new_salt"
        )
        
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
        """创建测试数据库"""
        db = Database(":memory:")
        await db.init()
        yield db
        await db.close()

    @pytest.mark.asyncio
    async def test_create_task(self, db):
        """测试创建任务"""
        task_id = await db.create_task(
            task_type="scan",
            status="pending",
            params='{"path": "/test"}'
        )
        
        assert task_id is not None

    @pytest.mark.asyncio
    async def test_update_task_status(self, db):
        """测试更新任务状态"""
        task_id = await db.create_task(
            task_type="scan",
            status="pending"
        )
        
        await db.update_task_status(task_id, "running")
        
        task = await db.get_task(task_id)
        assert task["status"] == "running"


class TestIndexes:
    """索引测试"""

    @pytest.mark.asyncio
    async def test_indexes_created(self):
        """测试索引已创建"""
        db = Database(":memory:")
        await db.init()
        
        # 获取所有索引
        indexes = await db.fetchall(
            "SELECT name, tbl_name FROM sqlite_master WHERE type='index'",
            ()
        )
        
        index_names = [idx["name"] for idx in indexes]
        
        # 验证重要索引存在
        assert any("file_type" in name for name in index_names)
        assert any("taken_at" in name for name in index_names)
        assert any("ai_processed" in name for name in index_names)
        
        await db.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
