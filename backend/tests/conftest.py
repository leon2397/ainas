"""
conftest.py - pytest 全局 fixtures
"""

import pytest
import sys, os
from pathlib import Path

# 把 backend 根目录加入 import path
BACKEND_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_ROOT))


@pytest.fixture(scope="session")
def backend_root():
    return BACKEND_ROOT


@pytest.fixture(scope="session")
def test_db_path(backend_root, tmp_path_factory):
    """
    返回测试数据库路径。
    scope='session' 表示所有测试共用一个数据库（只初始化一次）。
    """
    db_dir = tmp_path_factory.mktemp("test_db")
    return str(db_dir / "test_metadata.db")
