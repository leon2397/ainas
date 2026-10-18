"""
集成测试 - 数据库测试
"""
import pytest
import asyncio
import tempfile
import os
from pathlib import Path


@pytest.fixture
async def test_db():
    """创建测试数据库"""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))
    
    from database.db import Database
    
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    db = Database(db_path)
    await db.init()
    
    yield db
    
    await db.close()
    os.unlink(db_path)


class TestDatabaseConnection:
    """数据库连接测试"""
    
    @pytest.mark.asyncio
    async def test_database_initialization(self, test_db):
        """测试数据库初始化"""
        # 验证表已创建
        tables = await test_db.fetch_all(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        
        table_names = [t["name"] for t in tables]
        
        # 验证核心表存在
        assert "users" in table_names
        assert "media" in table_names
        assert "albums" in table_names
        assert "tasks" in table_names
    
    @pytest.mark.asyncio
    async def test_default_admin_creation(self, test_db):
        """测试默认管理员创建"""
        await test_db.init_default_admin()
        
        admin = await test_db.fetch_one(
            "SELECT * FROM users WHERE username = ?",
            ("admin",)
        )
        
        assert admin is not None
        assert admin["role"] == "admin"
        assert admin["is_active"] == 1


class TestMediaOperations:
    """媒体操作测试"""
    
    @pytest.mark.asyncio
    async def test_insert_media(self, test_db):
        """测试插入媒体记录"""
        media_data = {
            "file_path": "/test/path/image.jpg",
            "file_name": "image.jpg",
            "file_type": "image",
            "file_size": 1024000,
            "file_hash": "abc123",
            "width": 1920,
            "height": 1080,
            "created_at": "2024-01-01 12:00:00"
        }
        
        media_id = await test_db.insert_media(media_data)
        
        assert media_id is not None
        assert isinstance(media_id, int)
    
    @pytest.mark.asyncio
    async def test_get_media_by_id(self, test_db):
        """测试根据ID获取媒体"""
        # 先插入一条记录
        media_data = {
            "file_path": "/test/path/image.jpg",
            "file_name": "image.jpg",
            "file_type": "image",
            "file_size": 1024000,
            "file_hash": "abc123"
        }
        
        media_id = await test_db.insert_media(media_data)
        
        # 查询
        media = await test_db.get_media_by_id(media_id)
        
        assert media is not None
        assert media["id"] == media_id
        assert media["file_name"] == "image.jpg"
    
    @pytest.mark.asyncio
    async def test_update_media_tags(self, test_db):
        """测试更新媒体标签"""
        # 插入媒体
        media_id = await test_db.insert_media({
            "file_path": "/test/path/image.jpg",
            "file_name": "image.jpg",
            "file_type": "image",
            "file_size": 1024000
        })
        
        # 更新标签
        await test_db.update_media_tags(media_id, ["风景", "日落"])
        
        # 验证
        tags = await test_db.get_media_tags(media_id)
        assert "风景" in tags
        assert "日落" in tags
    
    @pytest.mark.asyncio
    async def test_search_media(self, test_db):
        """测试搜索媒体"""
        # 插入测试数据
        await test_db.insert_media({
            "file_path": "/test/beach.jpg",
            "file_name": "beach.jpg",
            "file_type": "image",
            "tags": "海滩,度假"
        })
        
        await test_db.insert_media({
            "file_path": "/test/mountain.jpg",
            "file_name": "mountain.jpg",
            "file_type": "image",
            "tags": "山脉,徒步"
        })
        
        # 搜索
        results = await test_db.search_media("海滩")
        
        assert len(results) >= 1
        assert any("beach" in r["file_name"] for r in results)


class TestAlbumOperations:
    """相册操作测试"""
    
    @pytest.mark.asyncio
    async def test_create_album(self, test_db):
        """测试创建相册"""
        album_id = await test_db.create_album({
            "name": "测试相册",
            "album_type": "custom",
            "description": "用于测试"
        })
        
        assert album_id is not None
    
    @pytest.mark.asyncio
    async def test_add_media_to_album(self, test_db):
        """测试添加媒体到相册"""
        # 创建相册
        album_id = await test_db.create_album({
            "name": "测试相册",
            "album_type": "custom"
        })
        
        # 插入媒体
        media_id = await test_db.insert_media({
            "file_path": "/test/image.jpg",
            "file_name": "image.jpg",
            "file_type": "image"
        })
        
        # 添加到相册
        await test_db.add_media_to_album(album_id, media_id)
        
        # 验证
        album_media = await test_db.get_album_media(album_id)
        assert any(m["id"] == media_id for m in album_media)


class TestTaskOperations:
    """任务操作测试"""
    
    @pytest.mark.asyncio
    async def test_create_task(self, test_db):
        """测试创建任务"""
        task_id = await test_db.create_task({
            "task_type": "scan",
            "status": "pending",
            "params": '{"path": "/test"}'
        })
        
        assert task_id is not None
    
    @pytest.mark.asyncio
    async def test_update_task_status(self, test_db):
        """测试更新任务状态"""
        # 创建任务
        task_id = await test_db.create_task({
            "task_type": "classify",
            "status": "pending"
        })
        
        # 更新状态
        await test_db.update_task_status(task_id, "running", progress=50)
        
        # 验证
        task = await test_db.get_task_by_id(task_id)
        assert task["status"] == "running"
        assert task["progress"] == 50
    
    @pytest.mark.asyncio
    async def test_get_pending_tasks(self, test_db):
        """测试获取待处理任务"""
        # 创建多个任务
        await test_db.create_task({"task_type": "scan", "status": "pending"})
        await test_db.create_task({"task_type": "classify", "status": "pending"})
        await test_db.create_task({"task_type": "dedup", "status": "running"})
        
        # 获取待处理任务
        pending = await test_db.get_tasks_by_status("pending")
        
        assert len(pending) == 2


class TestUserOperations:
    """用户操作测试"""
    
    @pytest.mark.asyncio
    async def test_create_user(self, test_db):
        """测试创建用户"""
        user_id = await test_db.create_user({
            "username": "testuser",
            "password_hash": "hashed_password",
            "role": "user",
            "is_active": 1
        })
        
        assert user_id is not None
    
    @pytest.mark.asyncio
    async def test_get_user_by_username(self, test_db):
        """测试根据用户名获取用户"""
        await test_db.create_user({
            "username": "testuser2",
            "password_hash": "hash123",
            "role": "user"
        })
        
        user = await test_db.get_user_by_username("testuser2")
        
        assert user is not None
        assert user["username"] == "testuser2"
    
    @pytest.mark.asyncio
    async def test_update_user_last_login(self, test_db):
        """测试更新最后登录时间"""
        user_id = await test_db.create_user({
            "username": "testuser3",
            "password_hash": "hash123",
            "role": "user"
        })
        
        await test_db.update_user_last_login(user_id)
        
        user = await test_db.get_user_by_id(user_id)
        assert user["last_login"] is not None


class TestTransaction:
    """事务测试"""
    
    @pytest.mark.asyncio
    async def test_transaction_rollback(self, test_db):
        """测试事务回滚"""
        try:
            async with test_db.transaction() as tx:
                # 插入数据
                await tx.execute(
                    "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                    ("tx_user", "hash")
                )
                
                # 故意抛出错误
                raise Exception("Test error")
        
        except Exception:
            pass
        
        # 验证数据未插入
        user = await test_db.get_user_by_username("tx_user")
        assert user is None
    
    @pytest.mark.asyncio
    async def test_transaction_commit(self, test_db):
        """测试事务提交"""
        async with test_db.transaction() as tx:
            await tx.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                ("tx_user2", "hash")
            )
        
        # 验证数据已插入
        user = await test_db.get_user_by_username("tx_user2")
        assert user is not None
