"""
AI-NAS Media Manager - 单元测试配置
"""
import pytest
import asyncio
import tempfile
import os
from pathlib import Path

# 添加backend到路径
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def temp_db():
    """临时数据库"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    from database.db import Database
    db = Database(db_path)
    await db.init()
    
    yield db
    
    await db.close()
    os.unlink(db_path)


@pytest.fixture(scope="function")
def temp_dir():
    """临时目录"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_media_file(temp_dir):
    """创建示例媒体文件"""
    from PIL import Image
    
    img_path = temp_dir / "test_image.jpg"
    img = Image.new('RGB', (100, 100), color='red')
    img.save(img_path)
    
    return str(img_path)


@pytest.fixture
def mock_user():
    """模拟用户"""
    return {
        "id": 1,
        "username": "test_user",
        "role": "user",
        "is_active": True
    }


@pytest.fixture
def mock_admin():
    """模拟管理员"""
    return {
        "id": 1,
        "username": "admin",
        "role": "admin",
        "is_active": True
    }
