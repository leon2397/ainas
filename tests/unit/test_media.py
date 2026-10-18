"""
媒体模块单元测试
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime


class TestMediaService:
    """媒体服务测试"""
    
    @pytest.fixture
    def media_service(self):
        """创建媒体服务实例"""
        from services.media_utils import MediaService
        return MediaService()
    
    @pytest.mark.asyncio
    async def test_scan_directory(self, media_service, temp_dir):
        """测试扫描目录"""
        # 创建测试文件
        (temp_dir / "test1.jpg").touch()
        (temp_dir / "test2.png").touch()
        (temp_dir / "test3.txt").touch()  # 非媒体文件
        
        # Mock数据库
        media_service.db = Mock()
        media_service.db.execute = AsyncMock()
        
        result = await media_service.scan_directory(str(temp_dir))
        
        # 应该找到2个媒体文件
        assert result["found"] == 2
        assert result["added"] == 2
    
    @pytest.mark.asyncio
    async def test_generate_thumbnail(self, media_service, temp_dir):
        """测试生成缩略图"""
        from PIL import Image
        
        # 创建测试图片
        img_path = temp_dir / "test.jpg"
        img = Image.new('RGB', (200, 200), color='blue')
        img.save(img_path)
        
        thumbnail_path = await media_service.generate_thumbnail(str(img_path))
        
        # 验证缩略图生成
        assert thumbnail_path is not None
        assert Path(thumbnail_path).exists()
        
        # 验证缩略图尺寸
        thumb = Image.open(thumbnail_path)
        assert thumb.width <= 300
        assert thumb.height <= 300
    
    @pytest.mark.asyncio
    async def test_calculate_file_hash(self, media_service, temp_dir):
        """测试计算文件哈希"""
        # 创建测试文件
        test_file = temp_dir / "test.txt"
        test_file.write_text("Hello, World!")
        
        hash1 = await media_service.calculate_file_hash(str(test_file))
        hash2 = await media_service.calculate_file_hash(str(test_file))
        
        # 相同文件应该产生相同哈希
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256
    
    @pytest.mark.asyncio
    async def test_detect_duplicate(self, media_service):
        """测试重复文件检测"""
        # Mock数据库返回相同哈希的文件
        media_service.db = Mock()
        media_service.db.fetch_one = AsyncMock(return_value={
            "id": 1,
            "file_path": "/path/to/existing.jpg"
        })
        
        is_duplicate = await media_service.check_duplicate("abc123hash")
        
        assert is_duplicate is True
    
    @pytest.mark.asyncio
    async def test_get_media_by_id(self, media_service):
        """测试根据ID获取媒体"""
        media_service.db = Mock()
        media_service.db.fetch_one = AsyncMock(return_value={
            "id": 1,
            "file_path": "/path/to/image.jpg",
            "file_type": "image",
            "created_at": "2024-01-01"
        })
        
        media = await media_service.get_media_by_id(1)
        
        assert media is not None
        assert media["id"] == 1
        assert media["file_type"] == "image"
    
    @pytest.mark.asyncio
    async def test_update_media_tags(self, media_service):
        """测试更新媒体标签"""
        media_service.db = Mock()
        media_service.db.execute = AsyncMock()
        
        result = await media_service.update_tags(1, ["风景", "日落"])
        
        assert result is True
        media_service.db.execute.assert_called_once()


class TestMediaUtils:
    """媒体工具函数测试"""
    
    def test_get_file_extension(self):
        """测试获取文件扩展名"""
        from services.media_utils import get_file_extension
        
        assert get_file_extension("/path/to/image.jpg") == ".jpg"
        assert get_file_extension("/path/to/VIDEO.MP4") == ".mp4"
        assert get_file_extension("/path/to/file") == ""
    
    def test_is_media_file(self):
        """测试判断是否为媒体文件"""
        from services.media_utils import is_media_file
        
        # 图片
        assert is_media_file("/path/to/photo.jpg") is True
        assert is_media_file("/path/to/photo.png") is True
        
        # 视频
        assert is_media_file("/path/to/video.mp4") is True
        assert is_media_file("/path/to/video.avi") is True
        
        # 非媒体
        assert is_media_file("/path/to/document.txt") is False
        assert is_media_file("/path/to/archive.zip") is False
    
    def test_get_media_type(self):
        """测试获取媒体类型"""
        from services.media_utils import get_media_type
        
        assert get_media_type("/path/to/photo.jpg") == "image"
        assert get_media_type("/path/to/photo.jpeg") == "image"
        assert get_media_type("/path/to/video.mp4") == "video"
        assert get_media_type("/path/to/video.mov") == "video"
        assert get_media_type("/path/to/file.txt") is None
    
    def test_sanitize_filename(self):
        """测试文件名清理"""
        from services.media_utils import sanitize_filename
        
        assert sanitize_filename("hello world.jpg") == "hello_world.jpg"
        assert sanitize_filename("file<name>.txt") == "file_name_.txt"
        assert sanitize_filename("../../../etc/passwd") == "etc_passwd"


class TestVideoProcessor:
    """视频处理器测试"""
    
    @pytest.fixture
    def video_processor(self):
        """创建视频处理器实例"""
        from services.video_processor import VideoProcessor
        return VideoProcessor()
    
    @pytest.mark.asyncio
    async def test_extract_thumbnail(self, video_processor, temp_dir):
        """测试提取视频缩略图"""
        # 注意：这需要实际的视频文件
        # 在实际测试中可以使用小样本视频
        
        video_path = temp_dir / "test_video.mp4"
        
        # Mock FFmpeg
        with patch('services.video_processor.asyncio.create_subprocess_exec') as mock_exec:
            mock_proc = AsyncMock()
            mock_proc.returncode = 0
            mock_proc.communicate = AsyncMock(return_value=(b'', b''))
            mock_exec.return_value = mock_proc
            
            result = await video_processor.extract_thumbnail(str(video_path))
            
            assert result is not None
    
    def test_get_video_duration_mock(self, video_processor):
        """测试获取视频时长（Mock）"""
        with patch('services.video_processor.FFProbe') as mock_probe:
            mock_probe.return_value.get_duration.return_value = 120.5
            
            duration = video_processor.get_duration("/path/to/video.mp4")
            
            assert duration == 120.5
