"""
媒体编辑API路由
支持旋转、裁剪、翻转、调整尺寸等基础编辑功能
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional

from database.db import Database, get_db
from services.media_editor import get_media_editor

router = APIRouter(prefix="/api/media", tags=["Media Edit"])


# ============ Request Models ============

class RotateRequest(BaseModel):
    file_id: int
    angle: float
    expand: bool = True
    save_original: bool = True


class CropRequest(BaseModel):
    file_id: int
    x: int
    y: int
    width: int
    height: int
    save_original: bool = True


class FlipRequest(BaseModel):
    file_id: int
    direction: str = "horizontal"  # horizontal / vertical
    save_original: bool = True


class ResizeRequest(BaseModel):
    file_id: int
    width: Optional[int] = None
    height: Optional[int] = None
    keep_aspect: bool = True
    save_original: bool = True


class RestoreRequest(BaseModel):
    file_id: int
    backup_path: str


# ============ Routes ============

@router.post("/{file_id}/rotate")
async def rotate_media(
    file_id: int,
    request: RotateRequest,
    db: Database = Depends(get_db)
):
    """
    旋转图片
    
    - angle: 旋转角度（顺时针，90/180/270 或任意角度）
    - expand: 是否扩展画布以容纳旋转后的图片
    - save_original: 是否保存原始文件备份
    """
    # 获取文件信息
    file = await db.fetchone(
        "SELECT * FROM media_files WHERE id = ? AND is_deleted = FALSE",
        (file_id,)
    )
    if not file:
        raise HTTPException(status_code=404, detail="媒体文件不存在")
    
    if file['file_type'] != 'image':
        raise HTTPException(status_code=400, detail="仅支持图片编辑")
    
    file_path = file['file_path']
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="文件不存在于磁盘")
    
    try:
        editor = get_media_editor()
        result = editor.rotate(
            file_path=file_path,
            angle=request.angle,
            expand=request.expand,
            save_original=request.save_original
        )
        
        # 更新数据库中的文件信息（文件大小可能变化）
        import os
        new_size = os.path.getsize(file_path)
        await db.execute(
            "UPDATE media_files SET file_size = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (new_size, file_id)
        )
        
        # 清除缩略图缓存
        from services.thumbnail_cache import thumbnail_cache
        thumbnail_cache.invalidate(file_id)
        
        return {
            "status": "success",
            "file_id": file_id,
            "operation": "rotate",
            "angle": request.angle,
            "backup_path": result.get("backup_path"),
            "message": result["message"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"旋转失败: {str(e)}")


@router.post("/{file_id}/crop")
async def crop_media(
    file_id: int,
    request: CropRequest,
    db: Database = Depends(get_db)
):
    """
    裁剪图片
    
    - x, y: 裁剪区域左上角坐标
    - width, height: 裁剪区域宽高
    - save_original: 是否保存原始文件备份
    """
    file = await db.fetchone(
        "SELECT * FROM media_files WHERE id = ? AND is_deleted = FALSE",
        (file_id,)
    )
    if not file:
        raise HTTPException(status_code=404, detail="媒体文件不存在")
    
    if file['file_type'] != 'image':
        raise HTTPException(status_code=400, detail="仅支持图片编辑")
    
    file_path = file['file_path']
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="文件不存在于磁盘")
    
    try:
        editor = get_media_editor()
        result = editor.crop(
            file_path=file_path,
            x=request.x,
            y=request.y,
            width=request.width,
            height=request.height,
            save_original=request.save_original
        )
        
        # 更新数据库
        import os
        new_size = os.path.getsize(file_path)
        await db.execute(
            "UPDATE media_files SET file_size = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (new_size, file_id)
        )
        
        # 清除缩略图缓存
        from services.thumbnail_cache import thumbnail_cache
        thumbnail_cache
        cache.invalidate(file_id)
        
        return {
            "status": "success",
            "file_id": file_id,
            "operation": "crop",
            "crop_region": result["crop_region"],
            "original_size": result["original_size"],
            "new_size": result["new_size"],
            "backup_path": result.get("backup_path"),
            "message": result["message"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"裁剪失败: {str(e)}")


@router.post("/{file_id}/flip")
async def flip_media(
    file_id: int,
    request: FlipRequest,
    db: Database = Depends(get_db)
):
    """
    翻转图片
    
    - direction: 翻转方向 horizontal（水平）/ vertical（垂直）
    - save_original: 是否保存原始文件备份
    """
    if request.direction not in ["horizontal", "vertical"]:
        raise HTTPException(status_code=400, detail="direction 必须是 horizontal 或 vertical")
    
    file = await db.fetchone(
        "SELECT * FROM media_files WHERE id = ? AND is_deleted = FALSE",
        (file_id,)
    )
    if not file:
        raise HTTPException(status_code=404, detail="媒体文件不存在")
    
    if file['file_type'] != 'image':
        raise HTTPException(status_code=400, detail="仅支持图片编辑")
    
    file_path = file['file_path']
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="文件不存在于磁盘")
    
    try:
        editor = get_media_editor()
        result = editor.flip(
            file_path=file_path,
            direction=request.direction,
            save_original=request.save_original
        )
        
        # 清除缩略图缓存
        from services.thumbnail_cache import thumbnail_cache
        thumbnail_cache
        cache.invalidate(file_id)
        
        return {
            "status": "success",
            "file_id": file_id,
            "operation": "flip",
            "direction": request.direction,
            "backup_path": result.get("backup_path"),
            "message": result["message"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"翻转失败: {str(e)}")


@router.post("/{file_id}/resize")
async def resize_media(
    file_id: int,
    request: ResizeRequest,
    db: Database = Depends(get_db)
):
    """
    调整图片尺寸
    
    - width: 目标宽度（可选）
    - height: 目标高度（可选）
    - keep_aspect: 是否保持宽高比
    - save_original: 是否保存原始文件备份
    """
    if request.width is None and request.height is None:
        raise HTTPException(status_code=400, detail="必须指定 width 或 height")
    
    file = await db.fetchone(
        "SELECT * FROM media_files WHERE id = ? AND is_deleted = FALSE",
        (file_id,)
    )
    if not file:
        raise HTTPException(status_code=404, detail="媒体文件不存在")
    
    if file['file_type'] != 'image':
        raise HTTPException(status_code=400, detail="仅支持图片编辑")
    
    file_path = file['file_path']
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="文件不存在于磁盘")
    
    try:
        editor = get_media_editor()
        result = editor.resize(
            file_path=file_path,
            width=request.width,
            height=request.height,
            keep_aspect=request.keep_aspect,
            save_original=request.save_original
        )
        
        # 更新数据库
        import os
        new_size = os.path.getsize(file_path)
        await db.execute(
            "UPDATE media_files SET file_size = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (new_size, file_id)
        )
        
        # 清除缩略图缓存
        from services.thumbnail_cache import thumbnail_cache
        thumbnail_cache
        cache.invalidate(file_id)
        
        return {
            "status": "success",
            "file_id": file_id,
            "operation": "resize",
            "original_size": result["original_size"],
            "new_size": result["new_size"],
            "backup_path": result.get("backup_path"),
            "message": result["message"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"调整尺寸失败: {str(e)}")


@router.post("/{file_id}/auto-orient")
async def auto_orient_media(
    file_id: int,
    save_original: bool = True,
    db: Database = Depends(get_db)
):
    """
    自动根据EXIF方向调整图片
    
    根据照片的EXIF方向标签自动旋转图片到正确方向
    """
    file = await db.fetchone(
        "SELECT * FROM media_files WHERE id = ? AND is_deleted = FALSE",
        (file_id,)
    )
    if not file:
        raise HTTPException(status_code=404, detail="媒体文件不存在")
    
    if file['file_type'] != 'image':
        raise HTTPException(status_code=400, detail="仅支持图片编辑")
    
    file_path = file['file_path']
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="文件不存在于磁盘")
    
    try:
        editor = get_media_editor()
        result = editor.auto_orient(
            file_path=file_path,
            save_original=save_original
        )
        
        if result["status"] == "no_change":
            return {
                "status": "no_change",
                "file_id": file_id,
                "message": result["message"]
            }
        
        # 更新数据库
        import os
        new_size = os.path.getsize(file_path)
        await db.execute(
            "UPDATE media_files SET file_size = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (new_size, file_id)
        )
        
        # 清除缩略图缓存
        from services.thumbnail_cache import thumbnail_cache
        thumbnail_cache
        cache.invalidate(file_id)
        
        return {
            "status": "success",
            "file_id": file_id,
            "operation": "auto_orient",
            "backup_path": result.get("backup_path"),
            "message": result["message"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"自动调整方向失败: {str(e)}")


@router.post("/{file_id}/restore")
async def restore_backup(
    file_id: int,
    request: RestoreRequest,
    db: Database = Depends(get_db)
):
    """
    从备份恢复原始文件
    """
    file = await db.fetchone(
        "SELECT * FROM media_files WHERE id = ? AND is_deleted = FALSE",
        (file_id,)
    )
    if not file:
        raise HTTPException(status_code=404, detail="媒体文件不存在")
    
    file_path = file['file_path']
    if not file_path:
        raise HTTPException(status_code=404, detail="文件路径不存在")
    
    try:
        editor = get_media_editor()
        result = editor.restore_backup(
            backup_path=request.backup_path,
            original_path=file_path
        )
        
        # 更新数据库
        import os
        new_size = os.path.getsize(file_path)
        await db.execute(
            "UPDATE media_files SET file_size = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (new_size, file_id)
        )
        
        # 清除缩略图缓存
        from services.thumbnail_cache import thumbnail_cache
        thumbnail_cache
        cache.invalidate(file_id)
        
        return {
            "status": "success",
            "file_id": file_id,
            "operation": "restore",
            "backup_path": request.backup_path,
            "message": result["message"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"恢复失败: {str(e)}")


@router.get("/{file_id}/edit/history")
async def get_edit_history(
    file_id: int,
    db: Database = Depends(get_db)
):
    """
    获取文件的编辑历史（备份列表）
    """
    file = await db.fetchone(
        "SELECT file_name FROM media_files WHERE id = ?",
        (file_id,)
    )
    if not file:
        raise HTTPException(status_code=404, detail="媒体文件不存在")
    
    import os
    backup_dir = "./data/media_edits/backups"
    
    if not os.path.exists(backup_dir):
        return {"backups": [], "count": 0}
    
    # 查找该文件的所有备份
    file_name = file['file_name']
    backups = []
    
    for f in os.listdir(backup_dir):
        if f.startswith(file_name + ".bak."):
            backup_path = os.path.join(backup_dir, f)
            stat = os.stat(backup_path)
            backups.append({
                "path": backup_path,
                "created_at": stat.st_mtime,
                "size": stat.st_size
            })
    
    # 按时间排序
    backups.sort(key=lambda x: x["created_at"], reverse=True)
    
    return {
        "file_id": file_id,
        "file_name": file_name,
        "backups": backups,
        "count": len(backups)
    }


import os
