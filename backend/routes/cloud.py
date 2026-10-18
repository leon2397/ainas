"""
云备份路由
提供云端同步、备份管理接口
"""

import os
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from pydantic import BaseModel

from core.auth import get_current_user, require_admin

router = APIRouter(prefix="/api/cloud", tags=["云备份"])


class CloudConfig(BaseModel):
    provider: str  # aliyun / tencent
    bucket: str
    access_key: str
    secret_key: str
    endpoint: str = ""  # OSS endpoint
    region: str = ""    # COS region
    prefix: str = "ai-nas/"


class BackupRequest(BaseModel):
    file_ids: List[int] = []
    mode: str = "original"  # original / thumbnail / all


# 全局云存储实例
_cloud_storage = None


def get_cloud_storage():
    """获取云存储实例"""
    return _cloud_storage


@router.get("/config")
async def get_cloud_config(current_user: dict = Depends(get_current_user)):
    """获取云存储配置（非敏感信息）"""
    if not _cloud_storage:
        return {"configured": False, "message": "未配置云存储"}
    return {
        "configured": True,
        "provider": _cloud_storage.provider,
        "bucket": _cloud_storage.bucket,
        "region": getattr(_cloud_storage, 'region', ''),
        "prefix": getattr(_cloud_storage, 'prefix', 'ai-nas/')
    }


@router.post("/config")
async def set_cloud_config(config: CloudConfig, current_user: dict = Depends(require_admin)):
    """配置云存储（管理员）"""
    global _cloud_storage
    from plugins.storage.cloud_storage import CloudStorage
    _cloud_storage = CloudStorage(config.dict())
    if not _cloud_storage.is_available():
        raise HTTPException(status_code=400, detail=f"SDK 未安装或配置错误。阿里云需: pip install oss2; 腾讯云需: pip install cos-python-sdk-v5")
    return {"message": "云存储配置成功", "provider": config.provider, "bucket": config.bucket}


@router.get("/status")
async def get_cloud_status(current_user: dict = Depends(get_current_user)):
    """获取云存储状态"""
    if not _cloud_storage:
        return {"configured": False, "message": "未配置云存储"}
    files = _cloud_storage.list_files()
    return {
        "configured": True,
        "provider": _cloud_storage.provider,
        "bucket": _cloud_storage.bucket,
        "available": _cloud_storage.is_available(),
        "remote_files": len(files)
    }


@router.post("/backup")
async def backup_files(request: BackupRequest, current_user: dict = Depends(get_current_user)):
    """备份文件到云端"""
    if not _cloud_storage or not _cloud_storage.is_available():
        raise HTTPException(status_code=400, detail="云存储未配置或 SDK 不可用")
    from database.db import db

    if request.file_ids:
        files = []
        for fid in request.file_ids:
            f = await db.fetchone("SELECT * FROM media_files WHERE id = ?", (fid,))
            if f: files.append(f)
    else:
        files = await db.fetchall("SELECT * FROM media_files WHERE is_deleted = FALSE LIMIT 100")

    results = {"total": len(files), "success": 0, "failed": 0, "details": []}
    for f in files:
        file_path = f.get("original_path") or f.get("file_path")
        if file_path and os.path.exists(file_path):
            ok = _cloud_storage.upload_file(file_path)
            results["success" if ok else "failed"] += 1
            results["details"].append({"name": f["file_name"], "status": "ok" if ok else "failed"})
        else:
            results["failed"] += 1
            results["details"].append({"name": f["file_name"], "status": "file_not_found"})

    return results


@router.get("/files")
async def list_cloud_files(prefix: str = "", current_user: dict = Depends(get_current_user)):
    """列出云端文件"""
    if not _cloud_storage:
        raise HTTPException(status_code=400, detail="云存储未配置")
    return {"files": _cloud_storage.list_files(prefix)}


@router.delete("/files/{remote_path:path}")
async def delete_cloud_file(remote_path: str, current_user: dict = Depends(require_admin)):
    """删除云端文件（管理员）"""
    if not _cloud_storage:
        raise HTTPException(status_code=400, detail="云存储未配置")
    ok = _cloud_storage.delete_file(remote_path)
    return {"message": "删除成功" if ok else "删除失败"}