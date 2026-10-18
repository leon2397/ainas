"""
移动端同步服务
生态化扩展 - Phase 4.3
支持手机端照片自动同步、备份
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import asyncio
import json
from pathlib import Path


class SyncStatus(Enum):
    """同步状态"""
    PENDING = "pending"
    SYNCING = "syncing"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


class SyncDirection(Enum):
    """同步方向"""
    UPLOAD_ONLY = "upload_only"  # 仅上传
    DOWNLOAD_ONLY = "download_only"  # 仅下载
    BIDIRECTIONAL = "bidirectional"  # 双向同步


@dataclass
class MobileDevice:
    """移动设备"""
    device_id: str
    user_id: str
    device_name: str
    device_type: str  # ios, android
    os_version: str
    app_version: str
    last_seen: datetime
    is_active: bool


@dataclass
class SyncSettings:
    """同步设置"""
    device_id: str
    enabled: bool
    direction: SyncDirection
    sync_photos: bool
    sync_videos: bool
    sync_on_wifi_only: bool
    sync_on_charging_only: bool
    auto_sync: bool
    sync_interval: int  # 分钟
    local_folders: List[str]
    remote_folder: str
    exclude_patterns: List[str]


@dataclass
class SyncItem:
    """同步项"""
    id: str
    device_id: str
    local_path: str
    remote_path: str
    file_size: int
    file_hash: str
    media_type: str  # photo, video
    created_at: datetime
    status: SyncStatus
    progress: float
    error_message: Optional[str] = None
    completed_at: Optional[datetime] = None


class MobileSyncService:
    """移动同步服务"""
    
    def __init__(self, storage_path: str = "data/mobile_sync"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self._devices: Dict[str, MobileDevice] = {}
        self._settings: Dict[str, SyncSettings] = {}
        self._sync_items: Dict[str, SyncItem] = {}
        
        self._load_data()
    
    def _load_data(self):
        """加载数据"""
        # 加载设备
        devices_file = self.storage_path / "devices.json"
        if devices_file.exists():
            with open(devices_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for d in data:
                    device = MobileDevice(
                        device_id=d["device_id"],
                        user_id=d["user_id"],
                        device_name=d["device_name"],
                        device_type=d["device_type"],
                        os_version=d["os_version"],
                        app_version=d["app_version"],
                        last_seen=datetime.fromisoformat(d["last_seen"]),
                        is_active=d["is_active"]
                    )
                    self._devices[device.device_id] = device
        
        # 加载设置
        settings_file = self.storage_path / "settings.json"
        if settings_file.exists():
            with open(settings_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for s in data:
                    settings = SyncSettings(
                        device_id=s["device_id"],
                        enabled=s["enabled"],
                        direction=SyncDirection(s["direction"]),
                        sync_photos=s["sync_photos"],
                        sync_videos=s["sync_videos"],
                        sync_on_wifi_only=s["sync_on_wifi_only"],
                        sync_on_charging_only=s["sync_on_charging_only"],
                        auto_sync=s["auto_sync"],
                        sync_interval=s["sync_interval"],
                        local_folders=s["local_folders"],
                        remote_folder=s["remote_folder"],
                        exclude_patterns=s["exclude_patterns"]
                    )
                    self._settings[settings.device_id] = settings
    
    def _save_devices(self):
        """保存设备"""
        devices_file = self.storage_path / "devices.json"
        data = [
            {
                "device_id": d.device_id,
                "user_id": d.user_id,
                "device_name": d.device_name,
                "device_type": d.device_type,
                "os_version": d.os_version,
                "app_version": d.app_version,
                "last_seen": d.last_seen.isoformat(),
                "is_active": d.is_active
            }
            for d in self._devices.values()
        ]
        with open(devices_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _save_settings(self):
        """保存设置"""
        settings_file = self.storage_path / "settings.json"
        data = [
            {
                "device_id": s.device_id,
                "enabled": s.enabled,
                "direction": s.direction.value,
                "sync_photos": s.sync_photos,
                "sync_videos": s.sync_videos,
                "sync_on_wifi_only": s.sync_on_wifi_only,
                "sync_on_charging_only": s.sync_on_charging_only,
                "auto_sync": s.auto_sync,
                "sync_interval": s.sync_interval,
                "local_folders": s.local_folders,
                "remote_folder": s.remote_folder,
                "exclude_patterns": s.exclude_patterns
            }
            for s in self._settings.values()
        ]
        with open(settings_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    async def register_device(self, device_data: Dict) -> MobileDevice:
        """注册设备"""
        import uuid
        
        device_id = device_data.get("device_id") or str(uuid.uuid4())
        
        device = MobileDevice(
            device_id=device_id,
            user_id=device_data["user_id"],
            device_name=device_data["device_name"],
            device_type=device_data["device_type"],
            os_version=device_data.get("os_version", ""),
            app_version=device_data.get("app_version", ""),
            last_seen=datetime.utcnow(),
            is_active=True
        )
        
        self._devices[device_id] = device
        self._save_devices()
        
        # 创建默认同步设置
        if device_id not in self._settings:
            default_settings = SyncSettings(
                device_id=device_id,
                enabled=False,
                direction=SyncDirection.UPLOAD_ONLY,
                sync_photos=True,
                sync_videos=True,
                sync_on_wifi_only=True,
                sync_on_charging_only=False,
                auto_sync=True,
                sync_interval=60,
                local_folders=["/DCIM/Camera", "/Pictures"],
                remote_folder=f"/mobile/{device_id}",
                exclude_patterns=[".*", "thumb*"]
            )
            self._settings[device_id] = default_settings
            self._save_settings()
        
        return device
    
    async def update_device_status(self, device_id: str, is_active: bool = True):
        """更新设备状态"""
        if device_id in self._devices:
            self._devices[device_id].last_seen = datetime.utcnow()
            self._devices[device_id].is_active = is_active
            self._save_devices()
    
    async def get_device(self, device_id: str) -> Optional[MobileDevice]:
        """获取设备"""
        return self._devices.get(device_id)
    
    async def list_devices(self, user_id: str = None) -> List[MobileDevice]:
        """列出设备"""
        devices = list(self._devices.values())
        if user_id:
            devices = [d for d in devices if d.user_id == user_id]
        return devices
    
    async def get_sync_settings(self, device_id: str) -> Optional[SyncSettings]:
        """获取同步设置"""
        return self._settings.get(device_id)
    
    async def update_sync_settings(self, device_id: str, settings_data: Dict) -> bool:
        """更新同步设置"""
        if device_id not in self._settings:
            return False
        
        settings = self._settings[device_id]
        
        if "enabled" in settings_data:
            settings.enabled = settings_data["enabled"]
        if "direction" in settings_data:
            settings.direction = SyncDirection(settings_data["direction"])
        if "sync_photos" in settings_data:
            settings.sync_photos = settings_data["sync_photos"]
        if "sync_videos" in settings_data:
            settings.sync_videos = settings_data["sync_videos"]
        if "sync_on_wifi_only" in settings_data:
            settings.sync_on_wifi_only = settings_data["sync_on_wifi_only"]
        if "auto_sync" in settings_data:
            settings.auto_sync = settings_data["auto_sync"]
        if "sync_interval" in settings_data:
            settings.sync_interval = settings_data["sync_interval"]
        
        self._save_settings()
        return True
    
    async def create_sync_item(self, device_id: str, file_data: Dict) -> SyncItem:
        """创建同步项"""
        import uuid
        
        item_id = str(uuid.uuid4())
        
        item = SyncItem(
            id=item_id,
            device_id=device_id,
            local_path=file_data["local_path"],
            remote_path=file_data["remote_path"],
            file_size=file_data["file_size"],
            file_hash=file_data["file_hash"],
            media_type=file_data["media_type"],
            created_at=datetime.utcnow(),
            status=SyncStatus.PENDING,
            progress=0.0
        )
        
        self._sync_items[item_id] = item
        
        return item
    
    async def update_sync_progress(self, item_id: str, progress: float):
        """更新同步进度"""
        if item_id in self._sync_items:
            self._sync_items[item_id].progress = progress
            if progress >= 100:
                self._sync_items[item_id].status = SyncStatus.COMPLETED
                self._sync_items[item_id].completed_at = datetime.utcnow()
    
    async def get_sync_queue(self, device_id: str) -> List[SyncItem]:
        """获取同步队列"""
        return [
            item for item in self._sync_items.values()
            if item.device_id == device_id and item.status in [SyncStatus.PENDING, SyncStatus.SYNCING]
        ]
    
    async def get_sync_stats(self, device_id: str) -> Dict:
        """获取同步统计"""
        items = [item for item in self._sync_items.values() if item.device_id == device_id]
        
        return {
            "total": len(items),
            "pending": len([i for i in items if i.status == SyncStatus.PENDING]),
            "syncing": len([i for i in items if i.status == SyncStatus.SYNCING]),
            "completed": len([i for i in items if i.status == SyncStatus.COMPLETED]),
            "failed": len([i for i in items if i.status == SyncStatus.FAILED]),
            "total_size": sum(i.file_size for i in items)
        }
    
    async def get_photos_to_sync(self, device_id: str, limit: int = 100) -> List[Dict]:
        """获取待同步的照片列表"""
        settings = self._settings.get(device_id)
        if not settings or not settings.enabled:
            return []
        
        # 这里应该查询设备上的照片
        # 返回需要同步的照片列表
        return []


class MobileAPI:
    """移动端API"""
    
    def __init__(self, sync_service: MobileSyncService):
        self.sync_service = sync_service
    
    async def handle_device_register(self, request_data: Dict) -> Dict:
        """处理设备注册"""
        device = await self.sync_service.register_device(request_data)
        return {
            "device_id": device.device_id,
            "registered": True,
            "settings": {
                "enabled": False,
                "direction": "upload_only"
            }
        }
    
    async def handle_sync_request(self, device_id: str, request_data: Dict) -> Dict:
        """处理同步请求"""
        # 获取待同步列表
        photos = await self.sync_service.get_photos_to_sync(device_id)
        
        return {
            "device_id": device_id,
            "photos_to_sync": photos,
            "sync_enabled": True
        }
    
    async def handle_upload_complete(self, device_id: str, upload_data: Dict) -> Dict:
        """处理上传完成"""
        # 更新同步状态
        return {
            "success": True,
            "file_id": upload_data.get("file_id")
        }


# 全局实例
mobile_sync_service = MobileSyncService()
mobile_api = MobileAPI(mobile_sync_service)
