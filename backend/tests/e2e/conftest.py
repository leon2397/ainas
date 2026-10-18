"""
conftest.py - E2E test fixtures
==============================
"""

import pytest
import sys
import os
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

# 添加 backend 到 path
backend_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_root))


@pytest.fixture(scope="session")
def e2e_config():
    """E2E 测试配置"""
    return {
        "test_media_dir": "/tmp/ai_nas_e2e_test",
        "test_timeout": 30,
        "cleanup": True,
    }


@pytest.fixture(scope="function")
def temp_media_directory(tmp_path):
    """创建临时媒体目录"""
    media_dir = tmp_path / "test_media"
    media_dir.mkdir()
    
    # 创建测试文件结构
    (media_dir / "images").mkdir()
    (media_dir / "videos").mkdir()
    
    # 创建假图片文件
    for i in range(3):
        img = media_dir / "images" / f"test_{i}.jpg"
        img.write_bytes(b"\xff\xd8\xff\xe0\x00\x10JFIF" + b"\x00" * 100)
    
    yield media_dir
    
    # 清理
    if media_dir.exists():
        shutil.rmtree(media_dir)


@pytest.fixture(scope="function")
def test_user_data():
    """测试用户数据"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return {
        "username": f"testuser_{timestamp}",
        "password": "TestPassword123!",
        "email": f"test_{timestamp}@example.com",
    }


@pytest.fixture(scope="function")
def cleanup_test_data():
    """测试数据清理标记"""
    created_items = []
    yield created_items
    
    # 测试后清理
    for item in created_items:
        try:
            if isinstance(item, Path) and item.exists():
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()
        except Exception:
            pass
