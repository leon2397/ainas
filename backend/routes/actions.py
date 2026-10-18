"""
Actions API Routes
High-level operations: scan, classify, deduplicate
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional
import json

from database.db import Database, get_db
from services.scanner import MediaScanner, get_scanner
from services.classifier import AIClassifier, get_classifier
from services.dedup import Deduplicator, get_deduplicator

router = APIRouter(prefix="/api/actions", tags=["Actions"])


# ============ Request Models ============

class ScanRequest(BaseModel):
    path: str
    recursive: bool = True
    file_type: Optional[str] = None  # image, video, all

class ClassifyRequest(BaseModel):
    file_id: Optional[int] = None
    device_id: Optional[str] = None
    force: bool = False

class DedupRequest(BaseModel):
    scope_path: Optional[str] = None
    threshold: float = 0.85
    method: str = "hash"  # hash, similar


class BatchDeleteRequest(BaseModel):
    """批量删除媒体文件"""
    file_ids: List[int]


class BatchAddTagsRequest(BaseModel):
    """批量添加标签"""
    file_ids: List[int]
    tags: List[str]


class BatchRemoveTagsRequest(BaseModel):
    """批量移除标签"""
    file_ids: List[int]
    tags: List[str]


class BatchAddToAlbumRequest(BaseModel):
    """批量添加到相册"""
    file_ids: List[int]
    album_id: int


# ============ Scan Routes ============

@router.post("/scan")
async def start_scan(
    request: ScanRequest,
    background_tasks: BackgroundTasks,
    db: Database = Depends(get_db)
):
    """Start a media scan task"""
    import uuid
    
    # Create task
    task_id = str(uuid.uuid4())
    await db.create_task(
        task_id=task_id,
        task_type="scan",
        device_id="local",
        params={"path": request.path, "recursive": request.recursive}
    )
    
    # Start scan in background
    async def run_scan():
        scanner = await get_scanner(db)
        result = await scanner.scan_directory(
            root_path=request.path,
            recursive=request.recursive,
            file_type=request.file_type,
        )
        if 'error' in result:
            await db.update_task_status(task_id, "failed",
                                        error_msg=result['error'])
        else:
            await db.update_task_status(
                task_id, "success", progress=100,
                result=json.dumps(result, ensure_ascii=False))
        return result
    
    background_tasks.add_task(run_scan)
    
    return {
        "task_id": task_id,
        "status": "started",
        "message": f"Scanning {request.path}"
    }


@router.post("/scan/sync")
async def sync_scan(
    request: ScanRequest,
    db: Database = Depends(get_db)
):
    """Synchronous scan (blocking)"""
    scanner = await get_scanner(db)
    result = await scanner.scan_directory(
        root_path=request.path,
        recursive=request.recursive,
        file_type=request.file_type,
    )

    if 'error' in result:
        raise HTTPException(status_code=400, detail=result['error'])

    return {
        "status": "completed",
        "result": result
    }


# ============ AI Classify Routes ============

@router.post("/classify")
async def start_classify(
    request: ClassifyRequest,
    background_tasks: BackgroundTasks,
    db: Database = Depends(get_db)
):
    """Start AI classification task"""
    import uuid
    
    task_id = str(uuid.uuid4())
    await db.create_task(
        task_id=task_id,
        task_type="ai_classify",
        device_id=request.device_id or "local",
        params={"file_id": request.file_id, "force": request.force}
    )
    
    async def run_classify():
        classifier = await get_classifier(db)
        result = await classifier.classify_media(
            file_id=request.file_id,
            device_id=request.device_id,
            force=request.force
        )
        await db.update_task_status(task_id, "success", progress=100)
        return result
    
    background_tasks.add_task(run_classify)
    
    return {
        "task_id": task_id,
        "status": "started",
        "message": "AI classification started"
    }


@router.post("/classify/sync")
async def sync_classify(
    request: ClassifyRequest,
    db: Database = Depends(get_db)
):
    """Synchronous AI classification (blocking)"""
    classifier = await get_classifier(db)
    result = await classifier.classify_media(
        file_id=request.file_id,
        device_id=request.device_id,
        force=request.force
    )
    
    return {
        "status": "completed",
        "result": result
    }


@router.post("/classify/face")
async def detect_faces(
    file_id: int,
    db: Database = Depends(get_db)
):
    """Run face detection on a file"""
    classifier = await get_classifier(db)
    result = await classifier.face_detection(file_id)
    
    return result


# ============ Deduplication Routes ============

@router.post("/dedup")
async def start_dedup(
    request: DedupRequest,
    background_tasks: BackgroundTasks,
    db: Database = Depends(get_db)
):
    """Start deduplication task"""
    import uuid
    
    task_id = str(uuid.uuid4())
    await db.create_task(
        task_id=task_id,
        task_type="dedup",
        device_id="local",
        params={"scope": request.scope_path, "threshold": request.threshold}
    )
    
    async def run_dedup():
        deduplicator = await get_deduplicator(db)
        result = await deduplicator.find_duplicates(
            scope_path=request.scope_path,
            threshold=request.threshold,
            method=request.method
        )
        await db.update_task_status(task_id, "success", progress=100)
        return result
    
    background_tasks.add_task(run_dedup)
    
    return {
        "task_id": task_id,
        "status": "started",
        "message": "Deduplication started"
    }


@router.post("/dedup/sync")
async def sync_dedup(
    request: DedupRequest,
    db: Database = Depends(get_db)
):
    """Synchronous deduplication"""
    deduplicator = await get_deduplicator(db)
    result = await deduplicator.find_duplicates(
        scope_path=request.scope_path,
        threshold=request.threshold,
        method=request.method
    )
    
    return {
        "status": "completed",
        "result": result
    }


@router.get("/dedup/stats")
async def get_dedup_stats(db: Database = Depends(get_db)):
    """Get deduplication statistics"""
    deduplicator = await get_deduplicator(db)
    return await deduplicator.get_duplicate_stats()


# ============ Batch Operations ============

@router.post("/batch/classify-all")
async def batch_classify_all(
    device_id: Optional[str] = None,
    background_tasks: BackgroundTasks = None,
    db: Database = Depends(get_db)
):
    """Classify all unprocessed media"""
    import uuid
    
    task_id = str(uuid.uuid4())
    await db.create_task(
        task_id=task_id,
        task_type="ai_classify",
        device_id=device_id or "local",
        params={"batch": True}
    )
    
    async def run():
        classifier = await get_classifier(db)
        result = await classifier.classify_media(device_id=device_id)
        await db.update_task_status(task_id, "success", progress=100)
        return result
    
    background_tasks.add_task(run)
    
    return {
        "task_id": task_id,
        "status": "started"
    }


@router.post("/batch/create-albums")
async def batch_create_albums(
    db: Database = Depends(get_db)
):
    """Create albums based on existing tags"""
    # This would iterate through all tagged files and create albums
    return {
        "status": "not_implemented",
        "message": "Batch album creation coming soon"
    }


# ============ 批量操作路由 ============

@router.post("/batch/delete")
async def batch_delete(
    request: BatchDeleteRequest,
    db: Database = Depends(get_db)
):
    """批量软删除媒体文件"""
    deleted = 0
    not_found = 0
    for fid in request.file_ids:
        file = await db.fetchone("SELECT id FROM media_files WHERE id = ? AND is_deleted = FALSE", (fid,))
        if file:
            await db.execute(
                "UPDATE media_files SET is_deleted = TRUE, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (fid,)
            )
            deleted += 1
        else:
            not_found += 1
    return {"status": "completed", "deleted": deleted, "not_found": not_found}


@router.post("/batch/add-tags")
async def batch_add_tags(
    request: BatchAddTagsRequest,
    db: Database = Depends(get_db)
):
    """批量添加标签到多个文件"""
    import json as _json
    updated = 0
    for fid in request.file_ids:
        file = await db.fetchone("SELECT tags FROM media_files WHERE id = ? AND is_deleted = FALSE", (fid,))
        if not file:
            continue
        existing = []
        if file.get('tags'):
            try:
                existing = _json.loads(file['tags'])
            except (_json.JSONDecodeError, TypeError):
                existing = []
        for tag in request.tags:
            if tag not in existing:
                existing.append(tag)
        await db.execute(
            "UPDATE media_files SET tags = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (_json.dumps(existing), fid)
        )
        updated += 1
    return {"status": "completed", "updated": updated, "tags_added": request.tags}


@router.post("/batch/remove-tags")
async def batch_remove_tags(
    request: BatchRemoveTagsRequest,
    db: Database = Depends(get_db)
):
    """批量从多个文件移除标签"""
    import json as _json
    updated = 0
    for fid in request.file_ids:
        file = await db.fetchone("SELECT tags FROM media_files WHERE id = ? AND is_deleted = FALSE", (fid,))
        if not file:
            continue
        existing = []
        if file.get('tags'):
            try:
                existing = _json.loads(file['tags'])
            except (_json.JSONDecodeError, TypeError):
                existing = []
        existing = [t for t in existing if t not in request.tags]
        await db.execute(
            "UPDATE media_files SET tags = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (_json.dumps(existing), fid)
        )
        updated += 1
    return {"status": "completed", "updated": updated, "tags_removed": request.tags}


@router.post("/batch/add-to-album")
async def batch_add_to_album(
    request: BatchAddToAlbumRequest,
    db: Database = Depends(get_db)
):
    """批量添加文件到相册"""
    album = await db.fetchone("SELECT * FROM albums WHERE id = ?", (request.album_id,))
    if not album:
        raise HTTPException(status_code=404, detail="Album not found")
    
    added = 0
    for fid in request.file_ids:
        try:
            await db.execute(
                "INSERT OR IGNORE INTO album_files (album_id, file_id) VALUES (?, ?)",
                (request.album_id, fid)
            )
            added += 1
        except Exception:
            pass
    
    # 更新相册文件计数
    await db.execute(
        "UPDATE albums SET file_count = (SELECT COUNT(*) FROM album_files WHERE album_id = ?) WHERE id = ?",
        (request.album_id, request.album_id)
    )
    
    return {"status": "completed", "added": added, "album_id": request.album_id}
