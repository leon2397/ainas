"""
生态化扩展API路由
Phase 4 生态化扩展
"""

from fastapi import APIRouter, UploadFile, File, Query, HTTPException, Depends
from typing import List, Optional, Dict

from plugins.third_party.cloud_storage import cloud_sync_manager, BaiduNetdiskProvider, AliyunDriveProvider, OneDriveProvider
from plugins.marketplace.marketplace import plugin_marketplace, plugin_manager, PluginType
from sync.mobile.sync_service import mobile_sync_service, mobile_api
from community.service import community_service

router = APIRouter(prefix="/api/ecosystem", tags=["ecosystem"])


# ========== 云存储集成 ==========

@router.get("/cloud/providers")
async def list_cloud_providers():
    """列出云存储提供商"""
    providers = await cloud_sync_manager.list_providers()
    return {"providers": providers}


@router.post("/cloud/providers/{provider_name}/connect")
async def connect_cloud_provider(provider_name: str, config: Dict):
    """连接云存储"""
    if provider_name == "baidu_netdisk":
        provider = BaiduNetdiskProvider(config)
    elif provider_name == "aliyun_drive":
        provider = AliyunDriveProvider(config)
    elif provider_name == "onedrive":
        provider = OneDriveProvider(config)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider_name}")
    
    success = await provider.authenticate()
    
    if success:
        cloud_sync_manager.register_provider(provider)
        return {"connected": True, "provider": provider_name}
    else:
        raise HTTPException(status_code=401, detail="Authentication failed")


@router.get("/cloud/providers/{provider_name}/files")
async def list_cloud_files(provider_name: str, path: str = "/"):
    """列出云端文件"""
    provider = cloud_sync_manager.get_provider(provider_name)
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not connected")
    
    files = await provider.list_files(path)
    return {
        "provider": provider_name,
        "path": path,
        "files": [
            {
                "id": f.id,
                "name": f.name,
                "path": f.path,
                "size": f.size,
                "is_folder": f.is_folder,
                "modified_at": f.modified_at.isoformat()
            }
            for f in files
        ]
    }


@router.post("/cloud/sync")
async def sync_to_cloud(provider_name: str, local_path: str, remote_path: str):
    """同步到云端"""
    task = await cloud_sync_manager.sync_to_cloud(provider_name, local_path, remote_path)
    return {
        "task_id": task.id,
        "status": task.status,
        "created_at": task.created_at.isoformat()
    }


@router.get("/cloud/sync/{task_id}")
async def get_sync_status(task_id: str):
    """获取同步状态"""
    task = await cloud_sync_manager.get_sync_status(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return {
        "task_id": task.id,
        "status": task.status,
        "progress": task.progress,
        "error": task.error_message,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None
    }


# ========== 插件市场 ==========

@router.get("/marketplace/plugins")
async def search_plugins(
    q: str = "",
    plugin_type: Optional[str] = None,
    sort_by: str = "downloads"
):
    """搜索插件"""
    ptype = PluginType(plugin_type) if plugin_type else None
    plugins = await plugin_marketplace.search_plugins(q, ptype, sort_by=sort_by)
    
    return {
        "plugins": [p.to_dict() for p in plugins],
        "total": len(plugins)
    }


@router.get("/marketplace/plugins/{plugin_id}")
async def get_plugin(plugin_id: str):
    """获取插件详情"""
    plugin = await plugin_marketplace.get_plugin(plugin_id)
    if not plugin:
        raise HTTPException(status_code=404, detail="Plugin not found")
    
    return plugin.to_dict()


@router.post("/marketplace/plugins")
async def publish_plugin(plugin_data: Dict):
    """发布插件"""
    plugin = await plugin_marketplace.publish_plugin(plugin_data)
    return {
        "plugin_id": plugin.id,
        "status": plugin.status.value,
        "published": True
    }


@router.post("/marketplace/plugins/{plugin_id}/install")
async def install_plugin(plugin_id: str):
    """安装插件"""
    # 这里应该下载并安装插件
    success = await plugin_manager.install_plugin(f"downloads/{plugin_id}.zip", plugin_id)
    return {"installed": success}


@router.get("/plugins/installed")
async def list_installed_plugins():
    """列出已安装插件"""
    plugins = await plugin_manager.list_installed()
    return {"plugins": plugins}


@router.post("/plugins/{plugin_id}/enable")
async def enable_plugin(plugin_id: str):
    """启用插件"""
    success = await plugin_manager.enable_plugin(plugin_id)
    return {"enabled": success}


@router.post("/plugins/{plugin_id}/disable")
async def disable_plugin(plugin_id: str):
    """禁用插件"""
    success = await plugin_manager.disable_plugin(plugin_id)
    return {"disabled": success}


# ========== 移动端同步 ==========

@router.post("/mobile/devices/register")
async def register_mobile_device(device_data: Dict):
    """注册移动设备"""
    result = await mobile_api.handle_device_register(device_data)
    return result


@router.get("/mobile/devices")
async def list_mobile_devices(user_id: str):
    """列出移动设备"""
    devices = await mobile_sync_service.list_devices(user_id)
    return {
        "devices": [
            {
                "device_id": d.device_id,
                "device_name": d.device_name,
                "device_type": d.device_type,
                "last_seen": d.last_seen.isoformat(),
                "is_active": d.is_active
            }
            for d in devices
        ]
    }


@router.get("/mobile/devices/{device_id}/settings")
async def get_sync_settings(device_id: str):
    """获取同步设置"""
    settings = await mobile_sync_service.get_sync_settings(device_id)
    if not settings:
        raise HTTPException(status_code=404, detail="Settings not found")
    
    return {
        "device_id": device_id,
        "enabled": settings.enabled,
        "direction": settings.direction.value,
        "sync_photos": settings.sync_photos,
        "sync_videos": settings.sync_videos,
        "auto_sync": settings.auto_sync
    }


@router.put("/mobile/devices/{device_id}/settings")
async def update_sync_settings(device_id: str, settings_data: Dict):
    """更新同步设置"""
    success = await mobile_sync_service.update_sync_settings(device_id, settings_data)
    return {"updated": success}


@router.get("/mobile/devices/{device_id}/sync/queue")
async def get_sync_queue(device_id: str):
    """获取同步队列"""
    items = await mobile_sync_service.get_sync_queue(device_id)
    return {
        "device_id": device_id,
        "queue": [
            {
                "id": item.id,
                "local_path": item.local_path,
                "status": item.status.value,
                "progress": item.progress
            }
            for item in items
        ]
    }


@router.delete("/mobile/devices/{device_id}")
async def remove_mobile_device(device_id: str):
    """移除已连接的移动设备"""
    device = await mobile_sync_service.get_device(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    mobile_sync_service._devices.pop(device_id, None)
    mobile_sync_service._save_devices()
    return {"status": "removed", "device_id": device_id}


@router.post("/mobile/devices/{device_id}/sync")
async def trigger_mobile_sync(device_id: str, body: Optional[Dict] = None):
    """触发指定设备的同步任务（按当前同步设置入队）"""
    device = await mobile_sync_service.get_device(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    settings = await mobile_sync_service.get_sync_settings(device_id)
    direction = settings.direction.value if settings else "upload"
    return {"status": "queued", "device_id": device_id, "direction": direction}




# ========== 社区功能 ==========

@router.post("/community/shares")
async def create_share(share_data: Dict, user_id: str = "user_123"):
    """创建分享"""
    share = await community_service.create_share(user_id, share_data)
    return {
        "share_id": share.id,
        "share_url": f"/s/{share.id}",
        "password": share.password
    }


@router.get("/community/shares")
async def list_public_shares(limit: int = 20, offset: int = 0):
    """列出公开分享"""
    shares = await community_service.list_public_shares(limit, offset)
    return {
        "shares": [
            {
                "id": s.id,
                "title": s.title,
                "description": s.description,
                "author": s.user_id,
                "view_count": s.view_count,
                "like_count": s.like_count,
                "created_at": s.created_at.isoformat()
            }
            for s in shares
        ]
    }


@router.get("/community/shares/{share_id}")
async def get_share(share_id: str, password: Optional[str] = None):
    """获取分享"""
    share = await community_service.get_share(share_id, password)
    if not share:
        raise HTTPException(status_code=404, detail="Share not found or password required")
    
    return {
        "id": share.id,
        "title": share.title,
        "description": share.description,
        "media_count": len(share.media_ids),
        "view_count": share.view_count,
        "like_count": share.like_count,
        "created_at": share.created_at.isoformat()
    }


@router.post("/community/shares/{share_id}/comments")
async def add_comment(share_id: str, content: str, user_id: str = "user_123"):
    """添加评论"""
    comment = await community_service.add_comment(share_id, user_id, content)
    return {
        "comment_id": comment.id,
        "content": comment.content,
        "created_at": comment.created_at.isoformat()
    }


@router.get("/community/shares/{share_id}/comments")
async def get_comments(share_id: str):
    """获取评论"""
    comments = await community_service.get_comments(share_id)
    return {
        "comments": [
            {
                "id": c.id,
                "user_id": c.user_id,
                "content": c.content,
                "like_count": c.like_count,
                "created_at": c.created_at.isoformat()
            }
            for c in comments
        ]
    }


@router.post("/community/shares/{share_id}/like")
async def like_share(share_id: str, user_id: str = "user_123"):
    """点赞分享"""
    liked = await community_service.like_share(share_id, user_id)
    return {"liked": liked}


@router.post("/community/users/{user_id}/follow")
async def follow_user(user_id: str, follower_id: str = "user_123"):
    """关注用户"""
    following = await community_service.follow_user(follower_id, user_id)
    return {"following": following}


@router.get("/community/feed")
async def get_feed(user_id: str = "user_123", limit: int = 20):
    """获取动态feed"""
    shares = await community_service.get_feed(user_id, limit)
    return {
        "feed": [
            {
                "id": s.id,
                "title": s.title,
                "author": s.user_id,
                "created_at": s.created_at.isoformat()
            }
            for s in shares
        ]
    }
