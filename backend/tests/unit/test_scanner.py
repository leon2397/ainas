"""
test_scanner.py - 媒体扫描模块单元测试
=======================================
覆盖范围：
  1. 目录扫描
  2. 文件过滤
  3. 增量扫描
  4. 进度回调
  5. 错误处理

运行：
  cd backend
  pytest tests/unit/test_scanner.py -v
"""

import pytest
import sys
import os
import tempfile
import asyncio
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch, MagicMock

# 设置测试环境
os.environ["AI_NAS_DB_PATH"] = ":memory:"

# 添加 backend 到 path
backend_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_root))

from database.db import Database
from services.scanner import MediaScanner, IMAGE_EXTENSIONS, VIDEO_EXTENSIONS


class TestMediaExtensions:
    """媒体扩展名测试"""

    def test_image_extensions_defined(self):
        """测试图片扩展名已定义"""
        assert '.jpg' in IMAGE_EXTENSIONS
        assert '.jpeg' in IMAGE_EXTENSIONS
        assert '.png' in IMAGE_EXTENSIONS
        assert '.webp' in IMAGE_EXTENSIONS
        assert '.heic' in IMAGE_EXTENSIONS

    def test_video_extensions_defined(self):
        """测试视频扩展名已定义"""
        assert '.mp4' in VIDEO_EXTENSIONS
        assert '.mov' in VIDEO_EXTENSIONS
        assert '.avi' in VIDEO_EXTENSIONS
        assert '.mkv' in VIDEO_EXTENSIONS

    def test_all_extensions_lowercase(self):
        """测试所有扩展名都是小写"""
        for ext in IMAGE_EXTENSIONS | VIDEO_EXTENSIONS:
            assert ext == ext.lower()

    def test_image_and_video_separate(self):
        """测试图片和视频扩展名不重叠"""
        overlap = IMAGE_EXTENSIONS & VIDEO_EXTENSIONS
        assert len(overlap) == 0


class TestMediaScannerInit:
    """MediaScanner 初始化测试"""

    @pytest.mark.asyncio
    async def test_scanner_initialization(self):
        """测试扫描器初始化"""
        db = Database(":memory:")
        await db.init()
        
        scanner = MediaScanner(db)
        
        assert scanner.db is db
        assert scanner._running is False
        assert scanner._progress_callback is None
        
        await db.close()

    def test_set_progress_callback(self):
        """测试设置进度回调"""
        db = Database(":memory:")
        scanner = MediaScanner(db)
        
        callback = Mock()
        scanner.set_progress_callback(callback)
        
        assert scanner._progress_callback is callback


class TestMediaScannerDirectory:
    """目录扫描测试"""

    @pytest.fixture
    async def scanner(self):
        """创建测试扫描器"""
        db = Database(":memory:")
        await db.init()
        scanner = MediaScanner(db)
        yield scanner
        await db.close()

    @pytest.mark.asyncio
    async def test_scan_nonexistent_directory(self, scanner):
        """测试扫描不存在的目录"""
        result = await scanner.scan_directory("/nonexistent/path/xyz")
        
        assert "error" in result

    @pytest.mark.asyncio
    async def test_scan_empty_directory(self, scanner):
        """测试扫描空目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = await scanner.scan_directory(tmpdir)
            
            assert result["total"] == 0
            assert result["images"] == 0
            assert result["videos"] == 0
            assert result["new"] == 0


class TestMediaScannerFiles:
    """文件扫描测试"""

    @pytest.fixture
    async def scanner(self):
        """创建测试扫描器"""
        db = Database(":memory:")
        await db.init()
        scanner = MediaScanner(db)
        yield scanner
        await db.close()

    @pytest.mark.asyncio
    async def test_scan_with_images_only(self, scanner):
        """测试仅扫描图片"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建测试图片文件
            for i in range(3):
                Path(tmpdir, f"image{i}.jpg").touch()
                Path(tmpdir, f"photo{i}.png").touch()
            
            # 创建非媒体文件
            Path(tmpdir, "readme.txt").touch()
            
            result = await scanner.scan_directory(tmpdir)
            
            assert result["total"] == 4  # 4 个媒体文件
            assert result["images"] == 4
            assert result["videos"] == 0

    @pytest.mark.asyncio
    async def test_scan_with_videos_only(self, scanner):
        """测试仅扫描视频"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建测试视频文件
            for i in range(2):
                Path(tmpdir, f"video{i}.mp4").touch()
                Path(tmpdir, f"movie{i}.mov").touch()
            
            result = await scanner.scan_directory(tmpdir)
            
            assert result["total"] == 4
            assert result["videos"] == 4

    @pytest.mark.asyncio
    async def test_scan_with_mixed_media(self, scanner):
        """测试混合媒体扫描"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建图片
            Path(tmpdir, "photo.jpg").touch()
            # 创建视频
            Path(tmpdir, "video.mp4").touch()
            # 创建其他文件
            Path(tmpdir, "document.pdf").touch()
            Path(tmpdir, "data.json").touch()
            
            result = await scanner.scan_directory(tmpdir)
            
            assert result["total"] == 2
            assert result["images"] == 1
            assert result["videos"] == 1


class TestMediaScannerRecursive:
    """递归扫描测试"""

    @pytest.fixture
    async def scanner(self):
        """创建测试扫描器"""
        db = Database(":memory:")
        await db.init()
        scanner = MediaScanner(db)
        yield scanner
        await db.close()

    @pytest.mark.asyncio
    async def test_scan_non_recursive(self, scanner):
        """测试非递归扫描"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建子目录
            subdir = Path(tmpdir) / "subdir"
            subdir.mkdir()
            
            # 根目录文件
            Path(tmpdir, "root.jpg").touch()
            # 子目录文件
            Path(subdir, "child.jpg").touch()
            
            # 非递归扫描
            result = await scanner.scan_directory(tmpdir, recursive=False)
            
            assert result["total"] == 1  # 只扫描根目录

    @pytest.mark.asyncio
    async def test_scan_recursive(self, scanner):
        """测试递归扫描"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建子目录
            subdir1 = Path(tmpdir) / "subdir1"
            subdir2 = subdir1 / "subdir2"
            subdir2.mkdir(parents=True)
            
            # 各目录文件
            Path(tmpdir, "root.jpg").touch()
            Path(subdir1, "child1.jpg").touch()
            Path(subdir2, "child2.jpg").touch()
            
            # 递归扫描
            result = await scanner.scan_directory(tmpdir, recursive=True)
            
            assert result["total"] == 3


class TestMediaScannerExtensions:
    """扩展名过滤测试"""

    @pytest.fixture
    async def scanner(self):
        """创建测试扫描器"""
        db = Database(":memory:")
        await db.init()
        scanner = MediaScanner(db)
        yield scanner
        await db.close()

    @pytest.mark.asyncio
    async def test_custom_extensions(self, scanner):
        """测试自定义扩展名过滤"""
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "image.jpg").touch()
            Path(tmpdir, "video.mp4").touch()
            
            # 只扫描 jpg
            result = await scanner.scan_directory(
                tmpdir,
                extensions={'.jpg'}
            )
            
            assert result["total"] == 1
            assert result["images"] == 1


class TestMediaScannerProgress:
    """进度回调测试"""

    @pytest.mark.asyncio
    async def test_progress_callback_called(self):
        """测试进度回调被调用"""
        db = Database(":memory:")
        await db.init()
        scanner = MediaScanner(db)
        
        callback = Mock()
        scanner.set_progress_callback(callback)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "image.jpg").touch()
            
            await scanner.scan_directory(tmpdir)
            
            # 回调应该被调用
            assert callback.called
        
        await db.close()

    @pytest.mark.asyncio
    async def test_progress_callback_receives_data(self):
        """测试进度回调接收数据"""
        db = Database(":memory:")
        await db.init()
        scanner = MediaScanner(db)
        
        callback_data = []
        def callback(progress):
            callback_data.append(progress)
        
        scanner.set_progress_callback(callback)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "image.jpg").touch()
            
            await scanner.scan_directory(tmpdir)
            
            # 回调应接收字典类型数据
            if callback_data:
                assert isinstance(callback_data[0], dict)
        
        await db.close()


class TestMediaScannerIncremental:
    """增量扫描测试"""

    @pytest.mark.asyncio
    async def test_incremental_scan(self):
        """测试增量扫描"""
        db = Database(":memory:")
        await db.init()
        scanner = MediaScanner(db)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # 首次扫描
            Path(tmpdir, "image1.jpg").touch()
            result1 = await scanner.scan_directory(tmpdir)
            assert result1["new"] == 1
            
            # 增量扫描（无新文件）
            result2 = await scanner.scan_directory(tmpdir)
            assert result2["new"] == 0  # 已有文件不重复添加
            
            # 添加新文件
            Path(tmpdir, "image2.jpg").touch()
            result3 = await scanner.scan_directory(tmpdir)
            assert result3["new"] == 1
        
        await db.close()


class TestMediaScannerErrorHandling:
    """错误处理测试"""

    @pytest.mark.asyncio
    async def test_permission_error_handling(self):
        """测试权限错误处理"""
        db = Database(":memory:")
        await db.init()
        scanner = MediaScanner(db)
        
        # 扫描一个无法访问的路径（如果有）
        result = await scanner.scan_directory("/root/system/secret")
        
        # 应该返回错误而不是崩溃
        assert "error" in result or result["errors"] > 0
        
        await db.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
