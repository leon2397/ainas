"""
File Archive Service
Archives media files by date with symlink album generation
"""

import os
import asyncio
from typing import Dict, List, Optional, Tuple, Callable
from pathlib import Path
from datetime import datetime

from database.db import Database
from plugins.storage.local_storage import LocalStoragePlugin


class Archiver:
    """
    File archiving service with symlink album generation
    
    Core principles:
    - Original files are READ-ONLY and never modified
    - Files are archived by date to photo_original directory
    - Albums are created as symlinks (Linux) or shortcuts (Windows)
    - Falls back to virtual albums (database) if symlinks not supported
    """
    
    def __init__(self, db: Database, storage: LocalStoragePlugin = None):
        self.db = db
        self.storage = storage or LocalStoragePlugin(
            LocalStoragePlugin.get_manifest(), 
            {'base_path': './data'}
        )
        self._running = False
        self._progress_callback: Optional[Callable] = None
    
    def set_progress_callback(self, callback: Callable):
        """Set callback for progress updates"""
        self._progress_callback = callback
    
    async def archive_file(self, file_id: int) -> Tuple[bool, str]:
        """
        Archive a single file by its taken date
        
        Args:
            file_id: Database file ID
        
        Returns:
            (success, archive_path)
        """
        # Get file info
        file_info = await self.db.fetchone(
            "SELECT * FROM media_files WHERE id = ?",
            (file_id,)
        )
        
        if not file_info:
            return False, "File not found"
        
        if file_info.get('is_archived'):
            return True, file_info.get('album_path', '')
        
        # Parse date
        taken_at = file_info.get('taken_at')
        if taken_at:
            try:
                dt = datetime.fromisoformat(taken_at.replace('Z', '+00:00'))
                year = dt.year
                month = dt.month
                day = dt.day
            except ValueError:  # 日期格式错误时使用当前日期
                now = datetime.now()
                year, month, day = now.year, now.month, now.day
        else:
            now = datetime.now()
            year, month, day = now.year, now.month, now.day
        
        # Build archive path
        original_path = self.storage.config.get('original_path', './data/original')
        archive_dir = os.path.join(
            original_path,
            str(year),
            f"{month:02d}",
            f"{day:02d}"
        )
        
        filename = file_info['file_name']
        archive_path = os.path.join(archive_dir, filename)
        
        # Ensure directory exists
        os.makedirs(archive_dir, exist_ok=True)
        
        # Move file (archive)
        src_path = file_info['file_path']
        if src_path != archive_path and os.path.exists(src_path):
            try:
                self.storage.move_file(src_path, archive_path)
            except Exception as e:
                logger.info(f"Archive move error: {e}")
                # If move fails, keep original path
                archive_path = src_path
        
        # Update database
        await self.db.execute(
            """UPDATE media_files SET
               album_path = ?,
               is_archived = TRUE,
               original_path = ?,
               updated_at = CURRENT_TIMESTAMP
               WHERE id = ?""",
            (archive_path, archive_path, file_id)
        )
        
        return True, archive_path
    
    async def archive_directory(
        self,
        source_path: str,
        recursive: bool = True
    ) -> Dict:
        """
        Archive all files in a directory
        
        Args:
            source_path: Directory to scan
            recursive: Scan subdirectories
        
        Returns:
            Archive statistics
        """
        self._running = True
        stats = {
            'total': 0,
            'archived': 0,
            'skipped': 0,
            'errors': 0
        }
        
        # Find all media files in directory
        files = self._find_media_files(source_path, recursive)
        stats['total'] = len(files)
        
        for i, filepath in enumerate(files):
            if not self._running:
                break
            
            # Find or create file record
            existing = await self.db.fetchone(
                "SELECT id, is_archived FROM media_files WHERE file_path = ?",
                (filepath,)
            )
            
            if existing and existing.get('is_archived'):
                stats['skipped'] += 1
                continue
            
            # Create record if not exists
            if not existing:
                file_info = await self._create_file_record(filepath)
                if not file_info:
                    stats['errors'] += 1
                    continue
            
            # Archive
            file_id = existing['id'] if existing else file_info['id']
            success, _ = await self.archive_file(file_id)
            
            if success:
                stats['archived'] += 1
            else:
                stats['errors'] += 1
            
            # Progress callback
            if self._progress_callback:
                self._progress_callback({
                    'current': i + 1,
                    'total': len(files),
                    'file': filepath
                })
        
        self._running = False
        return stats
    
    def _find_media_files(self, directory: str, recursive: bool) -> List[str]:
        """Find all media files in directory"""
        media_extensions = {
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp',
            '.heic', '.heif', '.tiff', '.tif',
            '.mp4', '.mov', '.avi', '.mkv', '.flv'
        }
        
        files = []
        for root, dirs, filenames in os.walk(directory):
            for filename in filenames:
                ext = os.path.splitext(filename)[1].lower()
                if ext in media_extensions:
                    files.append(os.path.join(root, filename))
            
            if not recursive:
                break
        
        return files
    
    async def _create_file_record(self, filepath: str) -> Optional[Dict]:
        """Create a database record for a file"""
        path = Path(filepath)
        
        file_type = 'image' if path.suffix.lower() in {
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'
        } else 'video'
        
        from PIL import Image
        
        width, height = 0, 0
        try:
            if file_type == 'image':
                img = Image.open(filepath)
                width, height = img.size
        except (IOError, OSError, ValueError):  # 文件无法读取时使用默认尺寸
            pass
        
        file_data = {
            'file_path': filepath,
            'file_name': path.name,
            'file_type': file_type,
            'file_size': path.stat().st_size,
            'device_id': 'local',
            'taken_at': datetime.now().isoformat()
        }
        
        try:
            file_id = await self.db.add_media_file(file_data)
            return {'id': file_id}
        except Exception:  # 数据库错误时返回 None
            return None
    
    async def create_symlink_album(
        self,
        album_name: str,
        file_ids: List[int],
        album_type: str = 'custom'
    ) -> Tuple[bool, str]:
        """
        Create a symlink-based album
        
        Args:
            album_name: Album name/path
            file_ids: List of file IDs to include
            album_type: Album type (person/scene/date/custom)
        
        Returns:
            (success, album_path)
        """
        # Create album record
        album_id = await self.db.create_album(album_name, album_type)
        
        # Build album directory
        album_path = self._build_album_path(album_name, album_type)
        
        # Check if storage supports symlinks
        if self.storage.is_support_symlink():
            return await self._create_symlink_album(
                album_id, album_path, file_ids
            )
        else:
            return await self._create_virtual_album(
                album_id, file_ids
            )
    
    def _build_album_path(self, album_name: str, album_type: str) -> str:
        """Build album directory path"""
        album_path = self.storage.config.get('album_path', './data/albums')
        
        # Type-specific subdirectory
        type_map = {
            'person': '人物',
            'scene': '场景',
            'date': '日期',
            'custom': '自定义'
        }
        
        subdir = type_map.get(album_type, '自定义')
        return os.path.join(album_path, subdir, album_name)
    
    async def _create_symlink_album(
        self,
        album_id: int,
        album_path: str,
        file_ids: List[int]
    ) -> Tuple[bool, str]:
        """Create actual symlink album"""
        try:
            os.makedirs(album_path, exist_ok=True)
            
            for file_id in file_ids:
                # Get file info
                file_info = await self.db.fetchone(
                    "SELECT * FROM media_files WHERE id = ?",
                    (file_id,)
                )
                
                if not file_info:
                    continue
                
                original_path = file_info.get('original_path') or file_info.get('file_path')
                
                if not os.path.exists(original_path):
                    continue
                
                # Create symlink
                link_name = f"{file_info['id']}_{file_info['file_name']}"
                link_path = os.path.join(album_path, link_name)
                
                try:
                    if os.path.exists(link_path):
                        os.remove(link_path)
                    os.symlink(original_path, link_path)
                    
                    # Add to database
                    await self.db.execute(
                        "INSERT OR IGNORE INTO album_files (album_id, file_id) VALUES (?, ?)",
                        (album_id, file_id)
                    )
                except Exception as e:
                    logger.info(f"Symlink error: {e}")
            
            # Update file count
            await self.db.execute(
                "UPDATE albums SET file_count = ? WHERE id = ?",
                (len(file_ids), album_id)
            )
            
            return True, album_path
        
        except Exception as e:
            logger.info(f"Create symlink album error: {e}")
            return False, ''
    
    async def _create_virtual_album(
        self,
        album_id: int,
        file_ids: List[int]
    ) -> Tuple[bool, str]:
        """Create virtual album (database only)"""
        try:
            for file_id in file_ids:
                await self.db.execute(
                    "INSERT OR IGNORE INTO album_files (album_id, file_id) VALUES (?, ?)",
                    (album_id, file_id)
                )
            
            # Update file count
            await self.db.execute(
                "UPDATE albums SET file_count = ? WHERE id = ?",
                (len(file_ids), album_id)
            )
            
            return True, f"virtual://album/{album_id}"
        
        except Exception as e:
            logger.info(f"Virtual album error: {e}")
            return False, ''
    
    async def create_auto_albums(self) -> Dict:
        """
        Create auto albums based on existing tags and metadata
        
        Creates albums for:
        - Each unique tag (as scene albums)
        - Each year/month (as date albums)
        - Face clusters (as person albums)
        """
        stats = {'albums_created': 0, 'files_processed': 0}
        
        # Get all files with tags
        files = await self.db.fetchall(
            "SELECT * FROM media_files WHERE ai_processed = TRUE AND is_deleted = FALSE"
        )
        
        # Group by tags
        import json
        from loguru import logger
        tag_groups = {}
        for file_info in files:
            tags_str = file_info.get('tags', '[]')
            try:
                tags = json.loads(tags_str) if isinstance(tags_str, str) else tags_str
            except (json.JSONDecodeError, TypeError):  # JSON 解析失败时使用空列表
                tags = []
            
            for tag in tags:
                if tag not in tag_groups:
                    tag_groups[tag] = []
                tag_groups[tag].append(file_info['id'])
        
        # Create tag albums
        for tag, file_ids in tag_groups.items():
            album_name = f"场景/{tag}"
            await self.create_symlink_album(album_name, file_ids, 'scene')
            stats['albums_created'] += 1
        
        # Get files grouped by year/month
        files_by_date = {}
        for file_info in files:
            taken_at = file_info.get('taken_at')
            if taken_at:
                try:
                    dt = datetime.fromisoformat(taken_at.replace('Z', '+00:00'))
                    key = (dt.year, dt.month)
                    if key not in files_by_date:
                        files_by_date[key] = []
                    files_by_date[key].append(file_info['id'])
                except (ValueError, TypeError):  # 日期解析失败时跳过
                    pass
        
        # Create date albums
        for (year, month), file_ids in files_by_date.items():
            album_name = f"日期/{year}/{month:02d}"
            await self.create_symlink_album(album_name, file_ids, 'date')
            stats['albums_created'] += 1
        
        stats['files_processed'] = len(files)
        return stats
    
    def stop(self):
        """Stop archiving"""
        self._running = False


# Global archiver instance
archiver: Optional[Archiver] = None


async def get_archiver(db: Database) -> Archiver:
    """Get or create archiver instance"""
    global archiver
    if archiver is None:
        archiver = Archiver(db)
    return archiver
