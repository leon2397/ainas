"""
Media Files API Routes
"""

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import StreamingResponse, Response, FileResponse
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
import json
import os
import io
import tempfile
import subprocess

from database.db import Database, get_db

router = APIRouter(prefix="/api/media", tags=["Media"])


# ============ Request/Response Models ============

class MediaFileResponse(BaseModel):
    id: int
    file_path: str
    file_name: str
    file_type: str
    file_size: Optional[int] = None
    taken_at: Optional[str] = None
    tags: Optional[List[str]] = []
    ai_confidence: Optional[float] = None
    ai_processed: bool = False
    is_archived: bool = False
    
    class Config:
        from_attributes = True


class MediaSearchRequest(BaseModel):
    keyword: str
    file_type: Optional[str] = None
    limit: int = 50


class AdvancedSearchRequest(BaseModel):
    """高级搜索：支持多维度组合查询"""
    keyword: Optional[str] = None           # 关键词（FTS全文搜索）
    file_type: Optional[str] = None         # image, video
    tags: Optional[List[str]] = None        # 标签筛选（AND 逻辑，文件必须包含所有标签）
    tag_mode: str = "and"                   # and: 所有标签 / or: 任一标签
    date_from: Optional[str] = None         # 起始日期 YYYY-MM-DD
    date_to: Optional[str] = None           # 截止日期 YYYY-MM-DD
    device_id: Optional[str] = None         # 设备筛选
    ai_processed: Optional[bool] = None     # 是否已 AI 分析
    min_size: Optional[int] = None          # 最小文件大小（字节）
    max_size: Optional[int] = None          # 最大文件大小（字节）
    sort_by: str = "taken_at"               # taken_at, file_name, file_size, created_at
    sort_order: str = "desc"                # asc, desc
    skip: int = 0
    limit: int = 50


class MediaUpdateTagsRequest(BaseModel):
    file_id: int
    tags: List[str]


class MediaAddTagRequest(BaseModel):
    """单个文件添加标签"""
    file_id: int
    tag: str


class MediaRemoveTagRequest(BaseModel):
    """单个文件移除标签"""
    file_id: int
    tag: str


# ============ Routes ============

@router.get("/", response_model=List[MediaFileResponse])
async def list_media(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    file_type: Optional[str] = Query(None, description="Filter by file type: image, video"),
    device_id: Optional[str] = Query(None),
    db: Database = Depends(get_db)
):
    """List all media files with pagination"""
    if file_type:
        sql = """
            SELECT * FROM media_files 
            WHERE file_type = ? AND is_deleted = FALSE 
            ORDER BY taken_at DESC 
            LIMIT ? OFFSET ?
        """
        files = await db.fetchall(sql, (file_type, limit, skip))
    elif device_id:
        sql = """
            SELECT * FROM media_files 
            WHERE device_id = ? AND is_deleted = FALSE 
            ORDER BY taken_at DESC 
            LIMIT ? OFFSET ?
        """
        files = await db.fetchall(sql, (device_id, limit, skip))
    else:
        sql = """
            SELECT * FROM media_files 
            WHERE is_deleted = FALSE 
            ORDER BY taken_at DESC 
            LIMIT ? OFFSET ?
        """
        files = await db.fetchall(sql, (limit, skip))
    
    # Parse tags JSON
    for f in files:
        if f.get('tags'):
            f['tags'] = json.loads(f['tags'])
    
    return files


@router.get("/{file_id}", response_model=MediaFileResponse)
async def get_media(file_id: int, db: Database = Depends(get_db)):
    """Get a specific media file by ID"""
    file = await db.fetchone("SELECT * FROM media_files WHERE id = ? AND is_deleted = FALSE", (file_id,))
    if not file:
        raise HTTPException(status_code=404, detail="Media file not found")
    
    if file.get('tags'):
        file['tags'] = json.loads(file['tags'])
    
    return file


@router.get("/count/by-type")
async def count_media_by_type(db: Database = Depends(get_db)):
    """Get media file counts grouped by type"""
    images = await db.fetchone("SELECT COUNT(*) as cnt FROM media_files WHERE file_type='image' AND is_deleted=FALSE")
    videos = await db.fetchone("SELECT COUNT(*) as cnt FROM media_files WHERE file_type='video' AND is_deleted=FALSE")
    return {"images": images['cnt'] if images else 0, "videos": videos['cnt'] if videos else 0}


@router.get("/search/", response_model=List[MediaFileResponse])
async def search_media(
    keyword: str = Query(..., min_length=1),
    file_type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    db: Database = Depends(get_db)
):
    """Search media files by keyword using FTS5"""
    results = await db.search_media(keyword, file_type, limit)
    
    for f in results:
        if f.get('tags'):
            f['tags'] = json.loads(f['tags'])
    
    return results


@router.post("/search/advanced")
async def advanced_search(
    request: AdvancedSearchRequest,
    db: Database = Depends(get_db)
):
    """高级多维度组合搜索"""
    conditions = ["m.is_deleted = FALSE"]
    params = []
    
    # FTS 全文搜索
    use_fts = False
    if request.keyword:
        use_fts = True
    
    # 文件类型
    if request.file_type:
        conditions.append("m.file_type = ?")
        params.append(request.file_type)
    
    # 标签筛选
    if request.tags:
        for tag in request.tags:
            if request.tag_mode == "or":
                conditions.append("(m.tags LIKE ?)")
                params.append(f'%"{tag}"%')
            else:
                conditions.append("(m.tags LIKE ?)")
                params.append(f'%"{tag}"%')
    
    # 日期范围
    if request.date_from:
        conditions.append("m.taken_at >= ?")
        params.append(request.date_from)
    if request.date_to:
        conditions.append("m.taken_at <= ?")
        params.append(request.date_to + " 23:59:59")
    
    # 设备
    if request.device_id:
        conditions.append("m.device_id = ?")
        params.append(request.device_id)
    
    # AI 状态
    if request.ai_processed is not None:
        conditions.append("m.ai_processed = ?")
        params.append(1 if request.ai_processed else 0)
    
    # 文件大小
    if request.min_size is not None:
        conditions.append("m.file_size >= ?")
        params.append(request.min_size)
    if request.max_size is not None:
        conditions.append("m.file_size <= ?")
        params.append(request.max_size)
    
    where_clause = " AND ".join(conditions)
    
    # 排序
    sort_map = {
        "taken_at": "m.taken_at",
        "file_name": "m.file_name",
        "file_size": "m.file_size",
        "created_at": "m.created_at",
    }
    order_col = sort_map.get(request.sort_by, "m.taken_at")
    order_dir = "DESC" if request.sort_order == "desc" else "ASC"
    
    if use_fts:
        sql = f"""
            SELECT m.* FROM media_files m
            JOIN media_fts f ON m.id = f.rowid
            WHERE media_fts MATCH ? AND {where_clause}
            ORDER BY {order_col} {order_dir}
            LIMIT ? OFFSET ?
        """
        results = await db.fetchall(sql, [request.keyword] + params + [request.limit, request.skip])
    else:
        sql = f"""
            SELECT m.* FROM media_files m
            WHERE {where_clause}
            ORDER BY {order_col} {order_dir}
            LIMIT ? OFFSET ?
        """
        results = await db.fetchall(sql, params + [request.limit, request.skip])
    
    for f in results:
        if f.get('tags'):
            f['tags'] = json.loads(f['tags'])
    
    # 获取总数
    if use_fts:
        count_sql = f"""
            SELECT COUNT(*) as cnt FROM media_files m
            JOIN media_fts f ON m.id = f.rowid
            WHERE media_fts MATCH ? AND {where_clause}
        """
        total = await db.fetchone(count_sql, [request.keyword] + params)
    else:
        count_sql = f"SELECT COUNT(*) as cnt FROM media_files m WHERE {where_clause}"
        total = await db.fetchone(count_sql, params)
    
    return {
        "results": results,
        "total": total['cnt'] if total else 0,
        "skip": request.skip,
        "limit": request.limit
    }


@router.get("/date/{year}", response_model=List[MediaFileResponse])
async def get_media_by_year(
    year: int,
    month: Optional[int] = Query(None, ge=1, le=12),
    db: Database = Depends(get_db)
):
    """Get media files by year or year/month"""
    results = await db.get_media_by_date(year, month)
    
    for f in results:
        if f.get('tags'):
            f['tags'] = json.loads(f['tags'])
    
    return results


@router.post("/upload")
async def upload_media(
    file: UploadFile = File(...),
    device_id: str = Query(...),
    db: Database = Depends(get_db)
):
    """Upload a media file and add to database (流式写入，防大文件撑爆内存)"""
    import os
    import tempfile

    # Determine file type
    file_type = "image"
    if file.filename.lower().endswith(('.mp4', '.mov', '.avi', '.mkv', '.flv', '.webm')):
        file_type = "video"

    upload_dir = f"./data/uploads/{device_id}"
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, file.filename)

    # Stream write in chunks (避免 file.read() 全量读内存)
    file_size = 0
    CHUNK_SIZE = 1024 * 1024  # 1 MB per chunk
    with open(file_path, 'wb') as f:
        while True:
            chunk = await file.read(CHUNK_SIZE)
            if not chunk:
                break
            f.write(chunk)
            file_size += len(chunk)
    
    # Add to database
    file_data = {
        'file_path': file_path,
        'file_name': file.filename,
        'file_type': file_type,
        'file_size': file_size,
        'mime_type': file.content_type,
        'device_id': device_id,
        'taken_at': datetime.now().isoformat()
    }
    
    file_id = await db.add_media_file(file_data)
    
    return {"id": file_id, "file_path": file_path, "status": "uploaded"}


@router.post("/update-tags")
async def update_tags(
    request: MediaUpdateTagsRequest,
    db: Database = Depends(get_db)
):
    """Update tags for a media file"""
    file = await db.fetchone("SELECT * FROM media_files WHERE id = ?", (request.file_id,))
    if not file:
        raise HTTPException(status_code=404, detail="Media file not found")
    
    # Update tags
    sql = "UPDATE media_files SET tags = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
    await db.execute(sql, (json.dumps(request.tags), request.file_id))
    
    return {"status": "updated", "tags": request.tags}


@router.post("/add-tag")
async def add_tag(
    request: MediaAddTagRequest,
    db: Database = Depends(get_db)
):
    """给单个文件添加一个标签（不覆盖已有标签）"""
    file = await db.fetchone("SELECT tags FROM media_files WHERE id = ? AND is_deleted = FALSE", (request.file_id,))
    if not file:
        raise HTTPException(status_code=404, detail="Media file not found")
    
    existing = []
    if file.get('tags'):
        try:
            existing = json.loads(file['tags'])
        except (json.JSONDecodeError, TypeError):
            existing = []
    
    if request.tag not in existing:
        existing.append(request.tag)
    
    await db.execute(
        "UPDATE media_files SET tags = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (json.dumps(existing), request.file_id)
    )
    return {"status": "updated", "tags": existing}


@router.post("/remove-tag")
async def remove_tag(
    request: MediaRemoveTagRequest,
    db: Database = Depends(get_db)
):
    """从单个文件移除一个标签"""
    file = await db.fetchone("SELECT tags FROM media_files WHERE id = ? AND is_deleted = FALSE", (request.file_id,))
    if not file:
        raise HTTPException(status_code=404, detail="Media file not found")
    
    existing = []
    if file.get('tags'):
        try:
            existing = json.loads(file['tags'])
        except (json.JSONDecodeError, TypeError):
            existing = []
    
    existing = [t for t in existing if t != request.tag]
    
    await db.execute(
        "UPDATE media_files SET tags = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (json.dumps(existing), request.file_id)
    )
    return {"status": "updated", "tags": existing}


@router.delete("/{file_id}")
async def delete_media(file_id: int, db: Database = Depends(get_db)):
    """Soft delete a media file"""
    file = await db.fetchone("SELECT * FROM media_files WHERE id = ?", (file_id,))
    if not file:
        raise HTTPException(status_code=404, detail="Media file not found")
    
    await db.execute(
        "UPDATE media_files SET is_deleted = TRUE, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (file_id,)
    )
    
    return {"status": "deleted", "file_id": file_id}


# ============ Thumbnail Cache Helpers ============

THUMBNAIL_CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "thumbnails")


def _get_cache_path(file_id: int, size: int, file_type: str) -> str:
    """Get the cache file path for a thumbnail."""
    os.makedirs(THUMBNAIL_CACHE_DIR, exist_ok=True)
    return os.path.join(THUMBNAIL_CACHE_DIR, f"{file_id}_{size}_{file_type}.jpg")


def _is_cache_valid(cached_path: str, original_path: str) -> bool:
    """Check if cache exists and is newer than the original file."""
    if not os.path.exists(cached_path):
        return False
    if not os.path.exists(original_path):
        return False
    cached_mtime = os.path.getmtime(cached_path)
    original_mtime = os.path.getmtime(original_path)
    return cached_mtime >= original_mtime


# ============ Routes ============

@router.get("/{file_id}/thumbnail")
async def get_thumbnail(
    file_id: int,
    size: int = Query(200, ge=50, le=800),
    db: Database = Depends(get_db)
):
    """Get thumbnail for a media file (with persistent cache)."""
    file = await db.fetchone("SELECT * FROM media_files WHERE id = ? AND is_deleted = FALSE", (file_id,))
    if not file:
        raise HTTPException(status_code=404, detail="Media file not found")
    
    file_path = file['file_path']
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found on disk")
    
    # Try cache first
    cache_path = _get_cache_path(file_id, size, file['file_type'])
    if _is_cache_valid(cache_path, file_path):
        return FileResponse(cache_path, media_type='image/jpeg')
    
    # Generate thumbnail
    try:
        from PIL import Image
        
        if file['file_type'] == 'video':
            tmp = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
            tmp_path = tmp.name
            tmp.close()
            try:
                subprocess.run([
                    'ffmpeg', '-i', file_path, '-ss', '0', '-vframes', '1',
                    '-vf', f'scale={size}:{size}:force_original_aspect_ratio=decrease',
                    '-y', tmp_path
                ], capture_output=True, timeout=10)
                if os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 0:
                    img_data = open(tmp_path, 'rb').read()
                    open(cache_path, 'wb').write(img_data)
                    return Response(content=img_data, media_type='image/jpeg')
            finally:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
            raise HTTPException(status_code=500, detail="Video thumbnail generation failed")
        else:
            img = Image.open(file_path)
            img.thumbnail((size, size), Image.Resampling.LANCZOS)
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            img.save(cache_path, format='JPEG', quality=85)
            return FileResponse(cache_path, media_type='image/jpeg')
    except ImportError:
        raise HTTPException(status_code=503, detail="Pillow not installed")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Thumbnail error: {str(e)}")
