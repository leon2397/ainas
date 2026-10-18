"""
Archive and Album API Routes
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel
from typing import List, Optional

from database.db import Database, get_db
from services.archiver import get_archiver

router = APIRouter(prefix="/api/archive", tags=["Archive"])


# ============ Request Models ============

class ArchiveRequest(BaseModel):
    file_id: Optional[int] = None
    source_path: Optional[str] = None
    recursive: bool = True

class AlbumRequest(BaseModel):
    album_name: str
    album_type: str  # person, scene, date, custom
    file_ids: List[int]

class CreateSymlinkRequest(BaseModel):
    target_path: str
    link_path: str

class RollbackRequest(BaseModel):
    rollback_file: Optional[str] = None


# ============ Archive Routes ============

@router.post("/file")
async def archive_file(
    file_id: int = Query(...),
    db: Database = Depends(get_db)
):
    """Archive a single file by date"""
    archiver = await get_archiver(db)
    success, archive_path = await archiver.archive_file(file_id)
    
    if not success:
        raise HTTPException(status_code=500, detail=archive_path)
    
    return {
        "status": "archived",
        "file_id": file_id,
        "archive_path": archive_path
    }


@router.post("/directory")
async def archive_directory(
    source_path: str = Query(...),
    recursive: bool = Query(True),
    background_tasks: BackgroundTasks = None,
    db: Database = Depends(get_db)
):
    """Archive all files in a directory"""
    archiver = await get_archiver(db)
    stats = await archiver.archive_directory(source_path, recursive)
    
    return {
        "status": "completed",
        "stats": stats
    }


@router.post("/create-auto-albums")
async def create_auto_albums(
    db: Database = Depends(get_db)
):
    """Create automatic albums based on tags and metadata"""
    archiver = await get_archiver(db)
    stats = await archiver.create_auto_albums()
    
    return {
        "status": "completed",
        "albums_created": stats.get('albums_created', 0),
        "files_processed": stats.get('files_processed', 0)
    }


# ============ Album Routes ============

@router.post("/albums/symlink")
async def create_symlink_album(
    request: AlbumRequest,
    db: Database = Depends(get_db)
):
    """Create a symlink-based album"""
    archiver = await get_archiver(db)
    success, album_path = await archiver.create_symlink_album(
        album_name=request.album_name,
        file_ids=request.file_ids,
        album_type=request.album_type
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to create album")
    
    return {
        "status": "created",
        "album_name": request.album_name,
        "album_path": album_path,
        "files_count": len(request.file_ids)
    }


@router.post("/albums/symlink/create")
async def create_single_symlink(
    request: CreateSymlinkRequest,
    db: Database = Depends(get_db)
):
    """Create a single symbolic link"""
    import os
    
    try:
        os.symlink(request.target_path, request.link_path)
        return {
            "status": "created",
            "target": request.target_path,
            "link": request.link_path
        }
    except OSError as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Symlink Routes ============

@router.get("/symlink/check")
async def check_symlink_support(
    db: Database = Depends(get_db)
):
    """Check if current storage supports symlinks"""
    from plugins.storage.local_storage import LocalStorage
    
    storage = LocalStorage({'base_path': './data'})
    supported = storage.is_support_symlink()
    
    return {
        "supported": supported,
        "mode": "symlink" if supported else "virtual"
    }
