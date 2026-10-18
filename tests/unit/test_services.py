"""
服务层单元测试
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta


class TestClassifier:
    """AI分类器测试"""
    
    @pytest.fixture
    def classifier(self):
        """创建分类器实例"""
        from services.classifier import MediaClassifier
        return MediaClassifier()
    
    @pytest.mark.asyncio
    async def test_classify_image(self, classifier):
        """测试图片分类"""
        # Mock AI引擎
        classifier.ai_engine = Mock()
        classifier.ai_engine.classify = AsyncMock(return_value=[
            {"label": "风景", "confidence": 0.95},
            {"label": "日落", "confidence": 0.87}
        ])
        
        result = await classifier.classify_image("/path/to/image.jpg")
        
        assert len(result) == 2
        assert result[0]["label"] == "风景"
        assert result[0]["confidence"] > 0.9
    
    @pytest.mark.asyncio
    async def test_extract_features(self, classifier):
        """测试特征提取"""
        classifier.ai_engine = Mock()
        classifier.ai_engine.extract_features = AsyncMock(return_value=[0.1, 0.2, 0.3])
        
        features = await classifier.extract_features("/path/to/image.jpg")
        
        assert len(features) == 3
        assert all(isinstance(f, float) for f in features)
    
    @pytest.mark.asyncio
    async def test_find_similar_images(self, classifier):
        """测试查找相似图片"""
        # Mock向量数据库
        classifier.vector_db = Mock()
        classifier.vector_db.search_similar = AsyncMock(return_value=[
            {"id": 1, "score": 0.95},
            {"id": 2, "score": 0.87},
            {"id": 3, "score": 0.82}
        ])
        
        similar = await classifier.find_similar(1, limit=3)
        
        assert len(similar) == 3
        assert similar[0]["score"] > similar[1]["score"]


class TestScanner:
    """扫描器测试"""
    
    @pytest.fixture
    def scanner(self):
        """创建扫描器实例"""
        from services.scanner import MediaScanner
        return MediaScanner()
    
    @pytest.mark.asyncio
    async def test_scan_with_progress(self, scanner, temp_dir):
        """测试带进度扫描"""
        # 创建测试文件
        (temp_dir / "img1.jpg").touch()
        (temp_dir / "img2.jpg").touch()
        (temp_dir / "subdir").mkdir()
        (temp_dir / "subdir" / "img3.jpg").touch()
        
        progress_updates = []
        
        async def progress_callback(current, total):
            progress_updates.append((current, total))
        
        scanner.db = Mock()
        scanner.db.execute = AsyncMock()
        
        result = await scanner.scan_directory(
            str(temp_dir),
            progress_callback=progress_callback
        )
        
        assert result["total"] == 3
        assert result["added"] == 3
        assert len(progress_updates) > 0
    
    @pytest.mark.asyncio
    async def test_scan_respects_file_types(self, scanner, temp_dir):
        """测试扫描遵守文件类型"""
        (temp_dir / "image.jpg").touch()
        (temp_dir / "video.mp4").touch()
        (temp_dir / "document.txt").touch()
        
        scanner.db = Mock()
        scanner.db.execute = AsyncMock()
        
        # 只扫描图片
        result = await scanner.scan_directory(
            str(temp_dir),
            file_types=["image"]
        )
        
        assert result["found"] == 1


class TestDedup:
    """去重服务测试"""
    
    @pytest.fixture
    def dedup_service(self):
        """创建去重服务实例"""
        from services.dedup import DedupService
        return DedupService()
    
    @pytest.mark.asyncio
    async def test_find_duplicates_by_hash(self, dedup_service):
        """测试通过哈希查找重复"""
        dedup_service.db = Mock()
        dedup_service.db.fetch_all = AsyncMock(return_value=[
            {"file_hash": "abc123", "file_path": "/path/1.jpg", "id": 1},
            {"file_hash": "abc123", "file_path": "/path/2.jpg", "id": 2},
            {"file_hash": "def456", "file_path": "/path/3.jpg", "id": 3},
        ])
        
        duplicates = await dedup_service.find_duplicates(method="hash")
        
        # 应该找到1组重复（abc123）
        assert len(duplicates) == 1
        assert len(duplicates[0]) == 2
    
    @pytest.mark.asyncio
    async def test_find_similar_by_perceptual_hash(self, dedup_service):
        """测试通过感知哈希查找相似"""
        dedup_service.db = Mock()
        dedup_service.db.fetch_all = AsyncMock(return_value=[
            {"id": 1, "phash": "aabbccdd"},
            {"id": 2, "phash": "aabbccde"},  # 相似
            {"id": 3, "phash": "11223344"},  # 不相似
        ])
        
        similar = await dedup_service.find_similar(threshold=0.9)
        
        # 应该找到1对相似
        assert len(similar) >= 1


class TestDeviceMonitor:
    """设备监控测试"""
    
    @pytest.fixture
    def monitor(self):
        """创建监控器实例"""
        from services.device_monitor import DeviceMonitor
        return DeviceMonitor()
    
    @pytest.mark.asyncio
    async def test_check_device_health(self, monitor):
        """测试检查设备健康状态"""
        monitor.db = Mock()
        monitor.db.fetch_one = AsyncMock(return_value={
            "device_id": "test-device",
            "last_heartbeat": datetime.now().isoformat(),
            "cpu_usage": 45.5,
            "memory_usage": 60.2
        })
        
        health = await monitor.check_device_health("test-device")
        
        assert health["status"] == "healthy"
        assert "cpu_usage" in health
    
    @pytest.mark.asyncio
    async def test_detect_offline_device(self, monitor):
        """测试检测离线设备"""
        old_time = datetime.now() - timedelta(minutes=10)
        
        monitor.db = Mock()
        monitor.db.fetch_one = AsyncMock(return_value={
            "device_id": "test-device",
            "last_heartbeat": old_time.isoformat()
        })
        
        health = await monitor.check_device_health("test-device")
        
        assert health["status"] == "offline"


class TestAlertManager:
    """告警管理器测试"""
    
    @pytest.fixture
    def alert_manager(self):
        """创建告警管理器实例"""
        from services.alert_manager import AlertManager
        return AlertManager()
    
    @pytest.mark.asyncio
    async def test_create_alert(self, alert_manager):
        """测试创建告警"""
        alert_manager.db = Mock()
        alert_manager.db.execute = AsyncMock()
        
        alert_id = await alert_manager.create_alert(
            level="warning",
            message="磁盘空间不足",
            source="system"
        )
        
        assert alert_id is not None
    
    @pytest.mark.asyncio
    async def test_get_active_alerts(self, alert_manager):
        """测试获取活动告警"""
        alert_manager.db = Mock()
        alert_manager.db.fetch_all = AsyncMock(return_value=[
            {"id": 1, "level": "error", "message": "服务异常"},
            {"id": 2, "level": "warning", "message": "磁盘空间低"}
        ])
        
        alerts = await alert_manager.get_active_alerts()
        
        assert len(alerts) == 2
        assert alerts[0]["level"] == "error"
    
    @pytest.mark.asyncio
    async def test_acknowledge_alert(self, alert_manager):
        """测试确认告警"""
        alert_manager.db = Mock()
        alert_manager.db.execute = AsyncMock()
        
        result = await alert_manager.acknowledge_alert(1, user_id=1)
        
        assert result is True
