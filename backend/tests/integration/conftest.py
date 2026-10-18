"""
conftest.py - Integration test fixtures
========================================
"""

import pytest
import sys
import os
from pathlib import Path

# 添加 backend 到 path
backend_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_root))

# 测试配置
TEST_CONFIG = {
    "test_username": "test_admin",
    "test_password": "test_password_123",
    "test_db_path": ":memory:",
}


@pytest.fixture(scope="session")
def test_config():
    """返回测试配置"""
    return TEST_CONFIG


@pytest.fixture(scope="function")
def temp_media_file(tmp_path):
    """创建临时媒体文件用于测试"""
    # 创建一个假的图片文件
    media_file = tmp_path / "test_image.jpg"
    media_file.write_bytes(b"fake_image_data_for_testing")
    return media_file


@pytest.fixture(scope="function")
def temp_video_file(tmp_path):
    """创建临时视频文件用于测试"""
    video_file = tmp_path / "test_video.mp4"
    video_file.write_bytes(b"fake_video_data_for_testing")
    return video_file
