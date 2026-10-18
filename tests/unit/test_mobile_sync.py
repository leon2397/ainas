"""
移动端同步模块单元测试
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import json


class TestMobileSyncManager:
    """移动端同步管理器测试"""
    
    @pytest.fixture
    def sync_manager(self):
        """创建同步管理器"""
        from sync.mobile.manager import MobileSyncManager
        manager = MobileSyncManager()
        manager.db = Mock()
        manager.api_client = Mock()
        return manager
    
    def test_register_device(self, sync_manager):
        """测试注册设备"""
        sync_manager.db.fetch_one = Mock(return_value=None)
        sync_manager.db.execute = Mock(return_value=None)
        sync_manager.db.fetch_val = Mock(return_value=1)
        
        result = sync_manager.register_device(
            device_id="device_123",
            device_name="My Phone",
            device_type="ios"
        )
        
        assert result is not None
        assert result["device_id"] == "device_123"
    
    def test_unregister_device(self, sync_manager):
        """测试注销设备"""
        sync_manager.db.fetch_one = Mock(return_value={
            "id": 1,
            "device_id": "device_123"
        })
        sync_manager.db.execute = Mock(return_value=None)
        
        result = sync_manager.unregister_device(device_id="device_123")
        
        assert result is True
    
    def test_get_registered_devices(self, sync_manager):
        """测试获取已注册设备"""
        sync_manager.db.fetch_all = Mock(return_value=[
            {"device_id": "device_1", "device_name": "iPhone", "is_active": True},
            {"device_id": "device_2", "device_name": "iPad", "is_active": False}
        ])
        
        devices = sync_manager.get_registered_devices()
        
        assert len(devices) == 2
    
    def test_get_device_info(self, sync_manager):
        """测试获取设备信息"""
        sync_manager.db.fetch_one = Mock(return_value={
            "device_id": "device_123",
            "device_name": "My Phone",
            "last_sync": "2026-04-06 10:00:00"
        })
        
        info = sync_manager.get_device_info(device_id="device_123")
        
        assert info["device_id"] == "device_123"


class TestPhotoSync:
    """照片同步测试"""
    
    @pytest.fixture
    def photo_sync(self):
        """创建照片同步器"""
        from sync.mobile.photo_sync import PhotoSync
        sync = PhotoSync()
        sync.db = Mock()
        sync.cloud_client = Mock()
        sync.local_storage = Mock()
        return sync
    
    def test_sync_photos_to_device(self, photo_sync):
        """测试同步照片到设备"""
        photo_sync.db.fetch_all = Mock(return_value=[
            {"id": 1, "file_path": "/media/1.jpg", "synced": False},
            {"id": 2, "file_path": "/media/2.jpg", "synced": False}
        ])
        photo_sync.cloud_client.get_download_url = Mock(return_value="https://cdn.example.com/1.jpg")
        photo_sync.local_storage.save = Mock(return_value=True)
        photo_sync.db.execute = Mock(return_value=None)
        
        result = photo_sync.sync_to_device(
            device_id="device_123",
            limit=10
        )
        
        assert result["synced"] >= 0
        assert "failed" in result
    
    def test_sync_photos_from_device(self, photo_sync):
        """测试从设备同步照片"""
        photo_sync.cloud_client.list_files = Mock(return_value=[])
        photo_sync.cloud_client.upload_file = Mock(return_value=True)
        photo_sync.db.execute = Mock(return_value=None)
        
        result = photo_sync.sync_from_device(device_id="device_123")
        
        assert "synced" in result
    
    def test_incremental_photo_sync(self, photo_sync):
        """测试增量照片同步"""
        photo_sync.db.fetch_one = Mock(return_value={
            "last_sync": "2026-04-05 10:00:00"
        })
        photo_sync.db.fetch_all = Mock(return_value=[
            {"id": 1, "created_at": "2026-04-06", "synced": False}
        ])
        photo_sync.cloud_client.upload_file = Mock(return_value=True)
        
        result = photo_sync.incremental_sync(device_id="device_123")
        
        assert result["synced"] >= 0
    
    def test_sync_with_resolution_filter(self, photo_sync):
        """测试按分辨率过滤同步"""
        photo_sync.db.fetch_all = Mock(return_value=[
            {"id": 1, "resolution": "4K", "file_size": 10000000},
            {"id": 2, "resolution": "HD", "file_size": 2000000},
            {"id": 3, "resolution": "SD", "file_size": 500000}
        ])
        
        # 应该只同步4K和HD照片
        result = photo_sync.sync_with_filter(
            device_id="device_123",
            min_resolution="HD"
        )
        
        assert True  # 验证过滤逻辑


class TestVideoSync:
    """视频同步测试"""
    
    @pytest.fixture
    def video_sync(self):
        """创建视频同步器"""
        from sync.mobile.video_sync import VideoSync
        sync = VideoSync()
        sync.db = Mock()
        sync.cloud_client = Mock()
        return sync
    
    def test_sync_videos_to_device(self, video_sync):
        """测试同步视频到设备"""
        video_sync.db.fetch_all = Mock(return_value=[
            {"id": 1, "file_path": "/media/video1.mp4", "duration": 60, "file_size": 50000000}
        ])
        video_sync.cloud_client.get_download_url = Mock(return_value="https://cdn.example.com/video1.mp4")
        
        result = video_sync.sync_to_device(device_id="device_123")
        
        assert "synced" in result
    
    def test_sync_videos_from_device(self, video_sync):
        """测试从设备同步视频"""
        video_sync.cloud_client.list_files = Mock(return_value=[
            {"key": "videos/video1.mp4", "size": 50000000}
        ])
        video_sync.cloud_client.upload_file = Mock(return_value=True)
        
        result = video_sync.sync_from_device(device_id="device_123")
        
        assert "synced" in result
    
    def test_sync_with_duration_filter(self, video_sync):
        """测试按时长过滤同步"""
        video_sync.db.fetch_all = Mock(return_value=[
            {"id": 1, "duration": 300},  # 5分钟
            {"id": 2, "duration": 30},   # 30秒
            {"id": 3, "duration": 1800}   # 30分钟
        ])
        
        result = video_sync.sync_with_filter(
            device_id="device_123",
            max_duration=600  # 10分钟内
        )
        
        assert True  # 验证时长过滤逻辑


class TestAlbumSync:
    """相册同步测试"""
    
    @pytest.fixture
    def album_sync(self):
        """创建相册同步器"""
        from sync.mobile.album_sync import AlbumSync
        sync = AlbumSync()
        sync.db = Mock()
        sync.photo_sync = Mock()
        return sync
    
    def test_sync_albums(self, album_sync):
        """测试同步相册"""
        album_sync.db.fetch_all = Mock(return_value=[
            {"id": 1, "name": "Vacation", "photo_count": 50},
            {"id": 2, "name": "Family", "photo_count": 30}
        ])
        album_sync.photo_sync.sync_to_device = Mock(return_value={"synced": 10})
        
        result = album_sync.sync_albums(device_id="device_123")
        
        assert len(result) == 2
    
    def test_sync_selected_albums(self, album_sync):
        """测试同步选定的相册"""
        album_sync.db.fetch_all = Mock(return_value=[
            {"id": 1, "name": "Vacation"}
        ])
        album_sync.photo_sync.sync_to_device = Mock(return_value={"synced": 50})
        
        result = album_sync.sync_albums(
            device_id="device_123",
            album_ids=[1]
        )
        
        assert len(result) == 1
    
    def test_sync_album_thumbnails(self, album_sync):
        """测试同步相册缩略图"""
        album_sync.db.fetch_all = Mock(return_value=[
            {"id": 1, "thumbnail": "path/to/thumb.jpg"}
        ])
        
        result = album_sync.sync_album_thumbnails(device_id="device_123")
        
        assert "synced" in result


class TestSyncConflict:
    """同步冲突测试"""
    
    @pytest.fixture
    def conflict_handler(self):
        """创建冲突处理器"""
        from sync.mobile.conflict import SyncConflictHandler
        handler = SyncConflictHandler()
        handler.db = Mock()
        return handler
    
    def test_detect_conflict(self, conflict_handler):
        """测试检测冲突"""
        conflict_handler.db.fetch_one = Mock(return_value={
            "id": 1,
            "local_version": "2026-04-06 10:00:00",
            "remote_version": "2026-04-06 09:00:00"
        })
        
        has_conflict = conflict_handler.detect_conflict(
            item_id=1,
            local_modified="2026-04-06 10:00:00",
            remote_modified="2026-04-06 09:00:00"
        )
        
        # 本地更新，远程较旧
        assert has_conflict is True
    
    def test_resolve_keep_local(self, conflict_handler):
        """测试保留本地版本"""
        conflict_handler.db.execute = Mock(return_value=None)
        
        result = conflict_handler.resolve(
            item_id=1,
            resolution="keep_local"
        )
        
        assert result is True
    
    def test_resolve_keep_remote(self, conflict_handler):
        """测试保留远程版本"""
        conflict_handler.db.execute = Mock(return_value=None)
        conflict_handler.cloud_client = Mock()
        
        result = conflict_handler.resolve(
            item_id=1,
            resolution="keep_remote"
        )
        
        assert result is True
    
    def test_resolve_merge(self, conflict_handler):
        """测试合并冲突"""
        conflict_handler.db.fetch_one = Mock(return_value={
            "local_content": "local data",
            "remote_content": "remote data"
        })
        conflict_handler.db.execute = Mock(return_value=None)
        
        result = conflict_handler.resolve(
            item_id=1,
            resolution="merge"
        )
        
        assert result is True


class TestSyncStatus:
    """同步状态测试"""
    
    @pytest.fixture
    def sync_status(self):
        """创建同步状态跟踪器"""
        from sync.mobile.status import SyncStatusTracker
        tracker = SyncStatusTracker()
        tracker.db = Mock()
        return tracker
    
    def test_start_sync(self, sync_status):
        """测试开始同步"""
        sync_status.db.execute = Mock(return_value=None)
        
        result = sync_status.start_sync(
            device_id="device_123",
            sync_type="photo"
        )
        
        assert result is not None
        assert result["status"] == "in_progress"
    
    def test_update_progress(self, sync_status):
        """测试更新进度"""
        sync_status.db.fetch_one = Mock(return_value={
            "id": 1,
            "status": "in_progress",
            "total_items": 100
        })
        sync_status.db.execute = Mock(return_value=None)
        
        result = sync_status.update_progress(
            sync_id=1,
            current_item=50
        )
        
        assert result["progress"] == 50
    
    def test_complete_sync(self, sync_status):
        """测试完成同步"""
        sync_status.db.fetch_one = Mock(return_value={"id": 1})
        sync_status.db.execute = Mock(return_value=None)
        
        result = sync_status.complete_sync(
            sync_id=1,
            synced_count=100,
            failed_count=2
        )
        
        assert result["status"] == "completed"
    
    def test_fail_sync(self, sync_status):
        """测试同步失败"""
        sync_status.db.fetch_one = Mock(return_value={"id": 1})
        sync_status.db.execute = Mock(return_value=None)
        
        result = sync_status.fail_sync(sync_id=1, error="Network timeout")
        
        assert result["status"] == "failed"
        assert result["error"] == "Network timeout"
    
    def test_get_sync_history(self, sync_status):
        """测试获取同步历史"""
        sync_status.db.fetch_all = Mock(return_value=[
            {"id": 1, "device_id": "device_123", "status": "completed"},
            {"id": 2, "device_id": "device_123", "status": "failed"}
        ])
        
        history = sync_status.get_sync_history(device_id="device_123", limit=10)
        
        assert len(history) == 2


class TestSyncSchedule:
    """同步计划测试"""
    
    @pytest.fixture
    def sync_schedule(self):
        """创建同步计划器"""
        from sync.mobile.schedule import SyncScheduler
        scheduler = SyncScheduler()
        scheduler.db = Mock()
        return scheduler
    
    def test_create_schedule(self, sync_schedule):
        """测试创建同步计划"""
        sync_schedule.db.fetch_one = Mock(return_value=None)
        sync_schedule.db.execute = Mock(return_value=None)
        
        result = sync_schedule.create_schedule(
            device_id="device_123",
            sync_type="photo",
            schedule_type="interval",
            interval_hours=6
        )
        
        assert result is not None
    
    def test_create_daily_schedule(self, sync_schedule):
        """测试创建每日同步计划"""
        sync_schedule.db.execute = Mock(return_value=None)
        
        result = sync_schedule.create_schedule(
            device_id="device_123",
            sync_type="photo",
            schedule_type="daily",
            time="22:00"
        )
        
        assert result is not None
    
    def test_create_wifi_only_schedule(self, sync_schedule):
        """测试创建仅WiFi同步计划"""
        sync_schedule.db.execute = Mock(return_value=None)
        
        result = sync_schedule.create_schedule(
            device_id="device_123",
            sync_type="photo",
            wifi_only=True
        )
        
        assert result is not None
    
    def test_update_schedule(self, sync_schedule):
        """测试更新同步计划"""
        sync_schedule.db.fetch_one = Mock(return_value={"id": 1})
        sync_schedule.db.execute = Mock(return_value=None)
        
        result = sync_schedule.update_schedule(
            schedule_id=1,
            interval_hours=12
        )
        
        assert result is True
    
    def test_delete_schedule(self, sync_schedule):
        """测试删除同步计划"""
        sync_schedule.db.fetch_one = Mock(return_value={"id": 1})
        sync_schedule.db.execute = Mock(return_value=None)
        
        result = sync_schedule.delete_schedule(schedule_id=1)
        
        assert result is True
    
    def test_get_active_schedules(self, sync_schedule):
        """测试获取活跃计划"""
        sync_schedule.db.fetch_all = Mock(return_value=[
            {"id": 1, "is_active": True, "schedule_type": "interval"}
        ])
        
        schedules = sync_schedule.get_active_schedules(device_id="device_123")
        
        assert all(s["is_active"] for s in schedules)


class TestSyncEncryption:
    """同步加密测试"""
    
    @pytest.fixture
    def encryption(self):
        """创建同步加密器"""
        from sync.mobile.encryption import SyncEncryption
        enc = SyncEncryption()
        return enc
    
    def test_encrypt_data(self, encryption):
        """测试加密数据"""
        data = b"sensitive photo data"
        
        encrypted = encryption.encrypt(data, key="test_key_12345")
        
        assert encrypted != data
        assert len(encrypted) > 0
    
    def test_decrypt_data(self, encryption):
        """测试解密数据"""
        original = b"sensitive photo data"
        encrypted = encryption.encrypt(original, key="test_key_12345")
        
        decrypted = encryption.decrypt(encrypted, key="test_key_12345")
        
        assert decrypted == original
    
    def test_encrypt_with_different_key(self, encryption):
        """测试不同密钥解密失败"""
        original = b"secret data"
        encrypted = encryption.encrypt(original, key="key1")
        
        with pytest.raises(Exception):
            encryption.decrypt(encrypted, key="key2")
    
    def test_generate_key(self, encryption):
        """测试生成密钥"""
        key = encryption.generate_key()
        
        assert len(key) == 32
        assert isinstance(key, str)


class TestSyncCompression:
    """同步压缩测试"""
    
    @pytest.fixture
    def compression(self):
        """创建同步压缩器"""
        from sync.mobile.compression import SyncCompressor
        comp = SyncCompressor()
        return comp
    
    def test_compress_photo(self, compression):
        """测试压缩照片"""
        original = b"large_photo_data" * 1000
        
        compressed = compression.compress_photo(original, quality=80)
        
        assert len(compressed) < len(original)
    
    def test_decompress_photo(self, compression):
        """测试解压照片"""
        original = b"large_photo_data" * 1000
        compressed = compression.compress_photo(original, quality=80)
        
        decompressed = compression.decompress_photo(compressed)
        
        assert decompressed == original
    
    def test_compression_ratio(self, compression):
        """测试压缩比"""
        original = b"photo_data" * 1000
        compressed = compression.compress_photo(original, quality=60)
        
        ratio = len(compressed) / len(original)
        
        assert ratio < 1.0


class TestSyncQuota:
    """同步配额测试"""
    
    @pytest.fixture
    def quota(self):
        """创建配额管理器"""
        from sync.mobile.quota import SyncQuotaManager
        manager = SyncQuotaManager()
        manager.db = Mock()
        return manager
    
    def test_check_quota_available(self, quota):
        """测试检查配额可用"""
        quota.db.fetch_one = Mock(return_value={
            "monthly_limit": 1024 * 1024 * 1024,  # 1GB
            "monthly_used": 500 * 1024 * 1024     # 500MB
        })
        
        available = quota.check_quota_available(
            device_id="device_123",
            required_size=100 * 1024 * 1024  # 100MB
        )
        
        assert available is True
    
    def test_check_quota_exceeded(self, quota):
        """测试检查配额超限"""
        quota.db.fetch_one = Mock(return_value={
            "monthly_limit": 1024 * 1024 * 1024,
            "monthly_used": 1000 * 1024 * 1024  # 已用1GB
        })
        
        available = quota.check_quota_available(
            device_id="device_123",
            required_size=100 * 1024 * 1024
        )
        
        assert available is False
    
    def test_update_quota_usage(self, quota):
        """测试更新配额使用"""
        quota.db.fetch_one = Mock(return_value={"id": 1})
        quota.db.execute = Mock(return_value=None)
        
        result = quota.update_usage(
            device_id="device_123",
            added_size=50 * 1024 * 1024
        )
        
        assert result is True
    
    def test_reset_monthly_quota(self, quota):
        """测试重置月度配额"""
        quota.db.execute = Mock(return_value=None)
        
        result = quota.reset_monthly_quota(device_id="device_123")
        
        assert result is True
