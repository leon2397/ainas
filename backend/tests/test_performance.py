"""
性能模块测试
"""

import pytest
import asyncio
import os
import tempfile
from PIL import Image

from services.thumbnail_cache import ThumbnailCache
from services.batch_processor import BatchProcessor, ProgressTracker
from services.memory_guard import MemoryGuard, safe_load_image


class TestThumbnailCache:
    """缩略图缓存测试"""
    
    def test_cache_key_generation(self):
        """测试缓存键生成"""
        cache = ThumbnailCache()
        
        key1 = cache._get_cache_key("test.jpg", (300, 300))
        key2 = cache._get_cache_key("test.jpg", (300, 300))
        key3 = cache._get_cache_key("test2.jpg", (300, 300))
        
        assert key1 == key2  # 相同文件+尺寸应该相同
        assert key1 != key3  # 不同文件应该不同
    
    def test_cache_path_generation(self):
        """测试缓存路径生成"""
        cache = ThumbnailCache()
        path = cache._get_cache_path("test.jpg", (300, 300))
        assert path.suffix == ".jpg"
        assert "thumbnails" in str(path)


class TestBatchProcessor:
    """批量处理器测试"""
    
    @pytest.mark.asyncio
    async def test_batch_process(self):
        """测试批量处理"""
        processor = BatchProcessor(batch_size=2, max_concurrency=2)
        
        items = [1, 2, 3, 4, 5]
        
        async def process_func(x):
            return x * 2
        
        results = await processor.process_batch(items, process_func)
        
        assert len(results) == 5
        assert 2 in results  # 1*2
        assert 10 in results  # 5*2
    
    def test_progress_tracker(self):
        """测试进度跟踪"""
        tracker = ProgressTracker(total=10)
        
        tracker.update(3)
        progress = tracker.get_progress()
        
        assert progress["current"] == 3
        assert progress["total"] == 10
        assert progress["percent"] == 30.0


class TestMemoryGuard:
    """内存保护测试"""
    
    def test_memory_info(self):
        """测试内存信息获取"""
        guard = MemoryGuard()
        info = guard.get_memory_info()
        
        assert "system_percent" in info
        assert "system_available" in info
        assert info["system_percent"] >= 0
        assert info["system_percent"] <= 100
    
    def test_memory_check(self):
        """测试内存检查"""
        guard = MemoryGuard()
        result = guard.check_memory()
        
        assert isinstance(result, bool)
    
    def test_safe_load_image_missing(self):
        """测试加载不存在的图片"""
        result = safe_load_image("nonexistent.jpg")
        assert result is None


class TestIntegration:
    """集成测试"""
    
    @pytest.mark.asyncio
    async def test_thumbnail_with_batch(self):
        """测试缩略图与批量处理集成"""
        processor = BatchProcessor(batch_size=2, max_concurrency=2)
        cache = ThumbnailCache()
        
        # 创建临时测试图片
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            img = Image.new("RGB", (100, 100), color="red")
            img.save(f.name)
            temp_path = f.name
        
        try:
            # 测试缩略图生成
            thumb_path = await cache.generate(temp_path, (50, 50))
            assert thumb_path is not None
            assert os.path.exists(thumb_path)
            
            # 测试缓存命中
            cached = cache.get(temp_path, (50, 50))
            assert cached is not None
            
        finally:
            # 清理
            if os.path.exists(temp_path):
                os.unlink(temp_path)
