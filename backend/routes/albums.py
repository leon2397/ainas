"""
Albums API Routes
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel

from database.db import Database, get_db

router = APIRouter(prefix="/api/albums", tags=["Albums"])


# ============ Models ============

class AlbumResponse(BaseModel):
    id: int
    album_name: str
    album_type: str
    parent_id: Optional[int] = None
    cover_file_id: Optional[int] = None
    file_count: int = 0
    
    class Config:
        from_attributes = True


class CreateAlbumRequest(BaseModel):
    name: str
    album_type: str  # person, scene, date, custom
    parent_id: Optional[int] = None


class AddToAlbumRequest(BaseModel):
    album_id: int
    file_ids: List[int]


class UpdateAlbumRequest(BaseModel):
    """更新相册信息（名称、封面、排序）"""
    album_name: Optional[str] = None
    cover_file_id: Optional[int] = None
    sort_order: Optional[str] = None  # name_asc, name_desc, date_asc, date_desc, count_asc, count_desc


# ============ Routes ============

@router.get("/", response_model=List[AlbumResponse])
async def list_albums(
    album_type: Optional[str] = Query(None, description="Filter by type: person, scene, date, custom"),
    sort: str = Query("name_asc", description="Sort: name_asc, name_desc, date_asc, date_desc, count_asc, count_desc"),
    db: Database = Depends(get_db)
):
    """List all albums"""
    order_map = {
        "name_asc": "album_name ASC",
        "name_desc": "album_name DESC",
        "date_asc": "created_at ASC",
        "date_desc": "created_at DESC",
        "count_asc": "file_count ASC",
        "count_desc": "file_count DESC",
    }
    order_clause = order_map.get(sort, "album_name ASC")
    
    if album_type:
        sql = f"SELECT * FROM albums WHERE album_type = ? ORDER BY {order_clause}"
        return await db.fetchall(sql, (album_type,))
    else:
        sql = f"SELECT * FROM albums ORDER BY {order_clause}"
        return await db.fetchall(sql)


@router.get("/{album_id}", response_model=AlbumResponse)
async def get_album(album_id: int, db: Database = Depends(get_db)):
    """Get album details"""
    album = await db.fetchone("SELECT * FROM albums WHERE id = ?", (album_id,))
    if not album:
        raise HTTPException(status_code=404, detail="Album not found")
    return album


@router.get("/{album_id}/files")
async def get_album_files(
    album_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    db: Database = Depends(get_db)
):
    """Get files in an album"""
    album = await db.fetchone("SELECT * FROM albums WHERE id = ?", (album_id,))
    if not album:
        raise HTTPException(status_code=404, detail="Album not found")
    
    # Check if this is a symlink album or DB album
    if album['album_type'] == 'custom':
        # Custom albums use DB-based file tracking
        sql = """
            SELECT m.* FROM media_files m
            JOIN album_files af ON m.id = af.file_id
            WHERE af.album_id = ?
            ORDER BY af.added_at DESC
            LIMIT ? OFFSET ?
        """
        files = await db.fetchall(sql, (album_id, limit, skip))
    else:
        # Person/Scene/Date albums use symlinks, list from filesystem
        # For now, return empty list - will be implemented with storage plugin
        files = []
    
    return {
        "album": album,
        "files": files,
        "total": album['file_count']
    }


@router.post("/", response_model=AlbumResponse)
async def create_album(
    request: CreateAlbumRequest,
    db: Database = Depends(get_db)
):
    """Create a new album"""
    album_id = await db.create_album(request.name, request.album_type, request.parent_id)
    return await db.fetchone("SELECT * FROM albums WHERE id = ?", (album_id,))


@router.post("/add-files")
async def add_files_to_album(
    request: AddToAlbumRequest,
    db: Database = Depends(get_db)
):
    """Add files to a custom album"""
    album = await db.fetchone("SELECT * FROM albums WHERE id = ?", (request.album_id,))
    if not album:
        raise HTTPException(status_code=404, detail="Album not found")
    
    added_count = 0
    for file_id in request.file_ids:
        try:
            await db.execute(
                "INSERT INTO album_files (album_id, file_id) VALUES (?, ?)",
                (request.album_id, file_id)
            )
            added_count += 1
        except Exception:
            pass  # Skip if already exists
    
    # Update file count
    await db.execute(
        "UPDATE albums SET file_count = (SELECT COUNT(*) FROM album_files WHERE album_id = ?) WHERE id = ?",
        (request.album_id, request.album_id)
    )
    
    return {"added": added_count, "album_id": request.album_id}


@router.patch("/{album_id}")
async def update_album(
    album_id: int,
    request: UpdateAlbumRequest,
    db: Database = Depends(get_db)
):
    """更新相册名称、封面等"""
    album = await db.fetchone("SELECT * FROM albums WHERE id = ?", (album_id,))
    if not album:
        raise HTTPException(status_code=404, detail="Album not found")
    
    if request.album_name is not None:
        await db.execute("UPDATE albums SET album_name = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (request.album_name, album_id))
    if request.cover_file_id is not None:
        # 验证文件存在
        f = await db.fetchone("SELECT id FROM media_files WHERE id = ? AND is_deleted = FALSE", (request.cover_file_id,))
        if not f:
            raise HTTPException(status_code=404, detail="Cover file not found")
        await db.execute("UPDATE albums SET cover_file_id = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (request.cover_file_id, album_id))
    
    updated = await db.fetchone("SELECT * FROM albums WHERE id = ?", (album_id,))
    return updated


@router.put("/{album_id}/reorder")
async def reorder_album_files(
    album_id: int,
    file_ids: List[int],
    db: Database = Depends(get_db)
):
    """重新排序相册内文件顺序（按给定 ID 列表的顺序）"""
    album = await db.fetchone("SELECT * FROM albums WHERE id = ?", (album_id,))
    if not album:
        raise HTTPException(status_code=404, detail="Album not found")
    
    # 先删除旧关联，再按新顺序插入
    await db.execute("DELETE FROM album_files WHERE album_id = ?", (album_id,))
    for idx, fid in enumerate(file_ids):
        await db.execute(
            "INSERT INTO album_files (album_id, file_id, added_at) VALUES (?, ?, datetime('now', ? || ' seconds'))",
            (album_id, fid, -idx)  # 用负偏移实现自定义排序
        )
    
    await db.execute(
        "UPDATE albums SET file_count = (SELECT COUNT(*) FROM album_files WHERE album_id = ?) WHERE id = ?",
        (album_id, album_id)
    )
    return {"status": "reordered", "album_id": album_id, "file_count": len(file_ids)}


@router.delete("/{album_id}")
async def delete_album(album_id: int, db: Database = Depends(get_db)):
    """Delete an album"""
    album = await db.fetchone("SELECT * FROM albums WHERE id = ?", (album_id,))
    if not album:
        raise HTTPException(status_code=404, detail="Album not found")
    
    # Remove file associations
    await db.execute("DELETE FROM album_files WHERE album_id = ?", (album_id,))
    # Remove album
    await db.execute("DELETE FROM albums WHERE id = ?", (album_id,))
    
    return {"status": "deleted", "album_id": album_id}
