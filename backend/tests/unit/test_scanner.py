"""
test_scanner.py - 媒体扫描模块单元测试
=======================================
覆盖范围：
  1. 目录扫描
  2. 文件过滤
  3. 增量扫描
  4. 进度回调
  5. 错误处理
  6. 消失文件自动软删除（计数准确性核心机制）
  7. 扩展名大小写归一与新格式识别
  8. 扫描统计口径（new/updated/unchanged）
  9. 对账预览（reconcile dry-run）

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
from modules.mod_media.scanner import MediaScanner, IMAGE_EXTENSIONS, VIDEO_EXTENSIONS


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
            
            assert result["total"] == 6  # 6 个媒体文件（txt 被排除）
            assert result["images"] == 6
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
        """测试权限错误处理

        场景：扫描一个当前进程无权访问的目录。
        期望：返回错误信息，而不是抛出异常让整个扫描任务崩溃。

        注意：不能依赖具体路径（如 /root/system/secret）——
        那是 Linux 特有的，Windows 上不存在，会退化成「路径不存在」分支，
        等于没测到权限这条路径。所以这里用 mock 精确模拟 PermissionError，
        让所有平台都真正走到这条分支。
        """
        db = Database(":memory:")
        await db.init()
        scanner = MediaScanner(db)

        with patch.object(Path, "exists", side_effect=PermissionError(
                13, "Permission denied", "/root/system/secret")):
            result = await scanner.scan_directory("/root/system/secret")

        # 应该返回错误而不是崩溃
        assert "error" in result, f"应返回 error，实际得到: {result}"
        assert "not accessible" in result["error"]

        await db.close()

    @pytest.mark.asyncio
    async def test_nonexistent_path_returns_error(self):
        """扫描不存在的路径应返回错误而非崩溃"""
        db = Database(":memory:")
        await db.init()
        scanner = MediaScanner(db)

        result = await scanner.scan_directory("/definitely/not/exist/path")

        assert "error" in result
        assert "does not exist" in result["error"]

        await db.close()


class TestVanishedFileCleanup:
    """磁盘消失文件自动软删除（计数准确性核心机制）"""

    @pytest.fixture
    async def scanner(self):
        db = Database(":memory:")
        await db.init()
        scanner = MediaScanner(db)
        yield scanner
        await db.close()

    @pytest.mark.asyncio
    async def test_removed_file_soft_deleted(self, scanner):
        """库有盘无的记录重扫时被软删除，计数回落"""
        with tempfile.TemporaryDirectory() as tmpdir:
            f1 = Path(tmpdir, "a.jpg")
            f2 = Path(tmpdir, "b.jpg")
            f1.touch()
            f2.touch()
            await scanner.scan_directory(tmpdir)
            assert await scanner.db.fetchval(
                "SELECT COUNT(*) FROM media_files WHERE is_deleted=FALSE") == 2

            f2.unlink()  # 模拟用户在 AINAS 之外删除文件
            stats = await scanner.scan_directory(tmpdir)

            assert stats['removed'] == 1
            assert stats['unchanged'] == 1
            assert stats['new'] == 0
            row = await scanner.db.fetchone(
                "SELECT is_deleted FROM media_files WHERE file_path = ?",
                (str(f2),))
            assert row['is_deleted']
            # 软删除而非物理删除：记录仍在，可恢复
            assert await scanner.db.fetchval(
                "SELECT COUNT(*) FROM media_files") == 2

    @pytest.mark.asyncio
    async def test_reappeared_file_resurrected(self, scanner):
        """被软删除的文件重新出现在磁盘上，重扫后复活重新计数"""
        with tempfile.TemporaryDirectory() as tmpdir:
            f1 = Path(tmpdir, "a.jpg")
            f1.touch()
            await scanner.scan_directory(tmpdir)
            f1.unlink()
            await scanner.scan_directory(tmpdir)
            assert await scanner.db.fetchval(
                "SELECT COUNT(*) FROM media_files WHERE is_deleted=FALSE") == 0

            f1.touch()  # 文件回来了
            stats = await scanner.scan_directory(tmpdir)
            assert stats['updated'] == 1
            assert await scanner.db.fetchval(
                "SELECT COUNT(*) FROM media_files WHERE is_deleted=FALSE") == 1

    @pytest.mark.asyncio
    async def test_non_recursive_scan_keeps_subdir_entries(self, scanner):
        """非递归扫描不得把子目录里的现存记录误判为消失"""
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "a.jpg").touch()
            subdir = Path(tmpdir, "sub")
            subdir.mkdir()
            Path(subdir, "b.jpg").touch()
            await scanner.scan_directory(tmpdir, recursive=True)

            stats = await scanner.scan_directory(tmpdir, recursive=False)
            assert stats['removed'] == 0
            assert await scanner.db.fetchval(
                "SELECT COUNT(*) FROM media_files WHERE is_deleted=FALSE") == 2

    @pytest.mark.asyncio
    async def test_custom_extension_scan_keeps_other_types(self, scanner):
        """自定义扩展名扫描不得软删除其他类型的历史记录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "a.jpg").touch()
            Path(tmpdir, "b.mp4").touch()
            await scanner.scan_directory(tmpdir)

            stats = await scanner.scan_directory(tmpdir, extensions={'.jpg'})
            assert stats['removed'] == 0
            assert stats['total'] == 1
            assert await scanner.db.fetchval(
                "SELECT COUNT(*) FROM media_files WHERE is_deleted=FALSE") == 2

    @pytest.mark.asyncio
    async def test_removal_scoped_to_root(self, scanner):
        """扫描子目录不影响根目录其他记录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "a.jpg").touch()
            subdir = Path(tmpdir, "sub")
            subdir.mkdir()
            Path(subdir, "b.jpg").touch()
            await scanner.scan_directory(tmpdir, recursive=True)

            stats = await scanner.scan_directory(str(subdir), recursive=True)
            assert stats['removed'] == 0
            assert stats['unchanged'] == 1
            assert await scanner.db.fetchval(
                "SELECT COUNT(*) FROM media_files WHERE is_deleted=FALSE") == 2


class TestCaseInsensitiveExtensions:
    """扩展名大小写归一与新格式识别"""

    @pytest.fixture
    async def scanner(self):
        db = Database(":memory:")
        await db.init()
        scanner = MediaScanner(db)
        yield scanner
        await db.close()

    @pytest.mark.asyncio
    async def test_mixed_case_extension_indexed(self, scanner):
        """`.Jpg` 混合大小写扩展名必须被索引（Linux 大小写敏感）"""
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "photo.Jpg").touch()
            result = await scanner.scan_directory(tmpdir)
            assert result['total'] == 1
            assert result['images'] == 1

    @pytest.mark.asyncio
    async def test_uppercase_extension_indexed(self, scanner):
        """`.JPG` 全大写扩展名必须被索引"""
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "photo.JPG").touch()
            result = await scanner.scan_directory(tmpdir)
            assert result['total'] == 1
            assert result['images'] == 1

    @pytest.mark.asyncio
    async def test_new_formats_indexed(self, scanner):
        """.avif 计为图片，.mts/.rmvb 计为视频"""
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "a.avif").touch()
            Path(tmpdir, "b.mts").touch()
            Path(tmpdir, "c.rmvb").touch()
            result = await scanner.scan_directory(tmpdir)
            assert result['total'] == 3
            assert result['images'] == 1
            assert result['videos'] == 2

    @pytest.mark.asyncio
    async def test_ts_not_indexed(self, scanner):
        """.ts 与 TypeScript 源码歧义，刻意不收（见 scanner 模块注释）"""
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "code.ts").touch()
            result = await scanner.scan_directory(tmpdir)
            assert result['total'] == 0


class TestScanStatistics:
    """扫描统计口径：new/updated/unchanged 各自独立且诚实"""

    @pytest.fixture
    async def scanner(self):
        db = Database(":memory:")
        await db.init()
        scanner = MediaScanner(db)
        yield scanner
        await db.close()

    @pytest.mark.asyncio
    async def test_unchanged_on_rescan(self, scanner):
        """无变化重扫：全部计为 unchanged，不得虚报 updated"""
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "a.jpg").touch()
            Path(tmpdir, "b.mp4").touch()
            await scanner.scan_directory(tmpdir)
            stats = await scanner.scan_directory(tmpdir)
            assert stats['new'] == 0
            assert stats['updated'] == 0
            assert stats['unchanged'] == 2
            assert stats['removed'] == 0

    @pytest.mark.asyncio
    async def test_updated_on_size_change(self, scanner):
        """文件体积变化才计为 updated"""
        with tempfile.TemporaryDirectory() as tmpdir:
            f = Path(tmpdir, "a.jpg")
            f.write_bytes(b"x")
            await scanner.scan_directory(tmpdir)
            f.write_bytes(b"xy")
            stats = await scanner.scan_directory(tmpdir)
            assert stats['updated'] == 1
            assert stats['unchanged'] == 0

    @pytest.mark.asyncio
    async def test_total_equals_images_videos_errors(self, scanner):
        """total = images + videos + errors，口径一致"""
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "a.jpg").touch()
            Path(tmpdir, "b.mp4").touch()
            Path(tmpdir, "c.txt").touch()
            stats = await scanner.scan_directory(tmpdir)
            assert stats['total'] == stats['images'] + stats['videos'] + stats['errors']
            assert stats['total'] == 2


class TestReconcile:
    """对账预览：不写库，准确报告 DB 与磁盘差异"""

    @pytest.fixture
    async def scanner(self):
        db = Database(":memory:")
        await db.init()
        scanner = MediaScanner(db)
        yield scanner
        await db.close()

    @pytest.mark.asyncio
    async def test_reconcile_consistent(self, scanner):
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "a.jpg").touch()
            Path(tmpdir, "b.mp4").touch()
            await scanner.scan_directory(tmpdir)
            r = await scanner.reconcile(tmpdir)
            assert r['consistent'] is True
            assert r['diff'] == {'phantom': 0, 'missing': 0,
                                 'revivable': 0, 'type_mismatch': 0}
            assert r['disk']['total'] == 2
            assert r['db']['total'] == 2

    @pytest.mark.asyncio
    async def test_reconcile_detects_phantom(self, scanner):
        """文件消失后对账报 phantom，且不写库"""
        with tempfile.TemporaryDirectory() as tmpdir:
            f1 = Path(tmpdir, "a.jpg")
            f1.touch()
            await scanner.scan_directory(tmpdir)
            f1.unlink()
            r = await scanner.reconcile(tmpdir)
            assert r['consistent'] is False
            assert r['diff']['phantom'] == 1
            # dry-run：数据库未被修改
            assert await scanner.db.fetchval(
                "SELECT COUNT(*) FROM media_files WHERE is_deleted=FALSE") == 1

    @pytest.mark.asyncio
    async def test_reconcile_detects_missing(self, scanner):
        """扫描后新增的文件对账报 missing"""
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "a.jpg").touch()
            await scanner.scan_directory(tmpdir)
            Path(tmpdir, "b.jpg").touch()  # 未重扫
            r = await scanner.reconcile(tmpdir)
            assert r['consistent'] is False
            assert r['diff']['missing'] == 1

    @pytest.mark.asyncio
    async def test_reconcile_detects_revivable(self, scanner):
        """软删除后文件回归，对账报 revivable（计数此时偏少）"""
        with tempfile.TemporaryDirectory() as tmpdir:
            f1 = Path(tmpdir, "a.jpg")
            f1.touch()
            await scanner.scan_directory(tmpdir)
            f1.unlink()
            await scanner.scan_directory(tmpdir)  # 软删除
            f1.touch()  # 文件回来但未重扫
            r = await scanner.reconcile(tmpdir)
            assert r['consistent'] is False
            assert r['diff']['revivable'] == 1
            assert r['db']['soft_deleted'] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
