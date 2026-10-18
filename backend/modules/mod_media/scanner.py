"""
Media Scanner Service
Scans directories for media files and indexes them
"""

import asyncio
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Callable

from database.db import Database
from core.logger import logger

# Supported media formats
IMAGE_EXTENSIONS = {
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.heic', '.heif',
    '.tiff', '.tif', '.raw', '.cr2', '.nef', '.arw', '.dng'
}
VIDEO_EXTENSIONS = {
    '.mp4', '.mov', '.avi', '.mkv', '.flv', '.wmv', '.m4v', '.mpg', '.mpeg', '.3gp'
}


class MediaScanner:
    """Media file scanner with incremental scanning support."""

    def __init__(self, db: Database):
        self.db = db
        self._running = False
        self._progress_callback: Optional[Callable] = None

    def set_progress_callback(self, callback: Callable) -> None:
        """Set callback for progress updates."""
        self._progress_callback = callback

    async def scan_directory(
        self,
        root_path: str,
        recursive: bool = True,
        extensions: Optional[set] = None,
    ) -> Dict:
        """
        Scan a directory for media files.

        Returns:
            Dict with scan statistics
        """
        if extensions is None:
            extensions = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS

        self._running = True
        stats = {
            'total': 0, 'images': 0, 'videos': 0,
            'new': 0, 'updated': 0, 'errors': 0
        }

        try:
            root = Path(root_path)
            if not root.exists():
                return {'error': f'Path does not exist: {root_path}'}

            # Collect all media files
            files: List[Path] = []
            for ext in extensions:
                if recursive:
                    files.extend(root.rglob(f'*{ext}'))
                    files.extend(root.rglob(f'*{ext.upper()}'))
                else:
                    files.extend(root.glob(f'*{ext}'))
                    files.extend(root.glob(f'*{ext.upper()}'))

            # Deduplicate (rglob with upper-case can duplicate)
            seen: set = set()
            unique: List[Path] = []
            for f in files:
                if f not in seen:
                    seen.add(f)
                    unique.append(f)
            files = unique

            stats['total'] = len(files)
            logger.info(f"[Scanner] Start scanning: {root_path}, found {len(files)} files")

            for i, filepath in enumerate(files):
                if not self._running:
                    logger.info("[Scanner] Stopped by user")
                    break

                try:
                    result = await self._process_file(str(filepath))

                    if result == 'new':
                        stats['new'] += 1
                    elif result == 'updated':
                        stats['updated'] += 1

                    if filepath.suffix.lower() in IMAGE_EXTENSIONS:
                        stats['images'] += 1
                    else:
                        stats['videos'] += 1

                    if self._progress_callback:
                        self._progress_callback({
                            'current': i + 1,
                            'total': len(files),
                            'file': str(filepath),
                        })

                except Exception as e:
                    stats['errors'] += 1
                    logger.error(f"[Scanner] Error processing {filepath}: {e}")

            logger.info(f"[Scanner] Scan complete: {stats}")
            return stats

        finally:
            self._running = False

    async def _process_file(self, filepath: str) -> str:
        """Process a single media file and add to database."""
        path = Path(filepath)

        # Check if already exists
        existing = await self.db.fetchone(
            "SELECT id, updated_at FROM media_files WHERE file_path = ?",
            (filepath,)
        )

        # Get file stats
        stat = path.stat()
        file_size = stat.st_size

        # Determine file type
        ext = path.suffix.lower()
        file_type = 'image' if ext in IMAGE_EXTENSIONS else 'video'

        # Calculate quick hash (for dedup)
        file_hash = self._calculate_quick_hash(filepath)

        # Extract EXIF if image
        exif_data: Dict = {}
        if file_type == 'image':
            exif_data = self._extract_exif(filepath)

        if existing:
            # Update existing record
            await self.db.execute(
                """UPDATE media_files SET
                   file_size = ?, updated_at = CURRENT_TIMESTAMP
                   WHERE file_path = ?""",
                (file_size, filepath)
            )
            logger.debug(f"[Scanner] Updated: {filepath}")
            return 'updated'
        else:
            # Insert new record
            import datetime
            modified_time = datetime.datetime.fromtimestamp(stat.st_mtime)
            file_data = {
                'file_path': filepath,
                'file_name': path.name,
                'file_type': file_type,
                'file_size': file_size,
                'mime_type': self._get_mime_type(ext),
                'device_id': 'local',
                'taken_at': exif_data.get('datetime') or modified_time.isoformat(),
                'camera_make': exif_data.get('make'),
                'camera_model': exif_data.get('model'),
                'gps_lat': exif_data.get('gps_lat'),
                'gps_lon': exif_data.get('gps_lon'),
            }
            await self.db.add_media_file(file_data)
            logger.debug(f"[Scanner] New file indexed: {filepath}")
            return 'new'

    def _calculate_quick_hash(self, filepath: str, sample_size: int = 8192) -> str:
        """Calculate quick hash from file beginning and end (first+last 8KB)."""
        try:
            with open(filepath, 'rb') as f:
                start = f.read(sample_size)
                f.seek(-sample_size, 2)
                end = f.read(sample_size)
                f.seek(0, 2)
                size = f.tell()
            hash_input = start + end + str(size).encode()
            return hashlib.md5(hash_input).hexdigest()
        except OSError as e:
            logger.warning(f"[Scanner] Cannot read file for hash: {filepath} ({e})")
            return ''

    def _extract_exif(self, filepath: str) -> Dict:
        """Extract EXIF data from image."""
        try:
            from PIL import Image
            from PIL.ExifTags import TAGS
        except ImportError:
            logger.debug(f"[Scanner] PIL not installed, skipping EXIF: {filepath}")
            return {}

        try:
            img = Image.open(filepath)
            exif = img._getexif()
            if not exif:
                return {}

            result: Dict = {}
            tag_map = {
                271: 'make',
                272: 'model',
                306: 'datetime',
                36867: 'datetime_original',
                36868: 'datetime_digitized',
            }

            for tag_id, value in exif.items():
                if tag_id in tag_map:
                    result[tag_map[tag_id]] = str(value)
                if tag_id == 34853:  # GPSInfo
                    result.update(self._parse_gps(exif[tag_id]))

            return result

        except Exception as e:
            logger.debug(f"[Scanner] EXIF extraction failed for {filepath}: {e}")
            return {}

    def _parse_gps(self, gps_info: Dict) -> Dict:
        """Parse GPS coordinates from EXIF GPSInfo tag."""
        try:
            def convert_to_degrees(value: tuple) -> float:
                d, m, s = value
                return d + (m / 60.0) + (s / 3600.0)

            lat = gps_info.get(2)
            lat_ref = gps_info.get(1)
            lon = gps_info.get(4)
            lon_ref = gps_info.get(3)

            if lat is None or lon is None:
                return {}

            lat = convert_to_degrees(lat)
            lon = convert_to_degrees(lon)

            if lat_ref == 'S':
                lat = -lat
            if lon_ref == 'W':
                lon = -lon

            return {'gps_lat': lat, 'gps_lon': lon}

        except (ValueError, TypeError, KeyError) as e:
            logger.debug(f"[Scanner] GPS parse error: {e}")
            return {}

    def _get_mime_type(self, ext: str) -> str:
        """Get MIME type from extension."""
        mime_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.webp': 'image/webp',
            '.heic': 'image/heic',
            '.heif': 'image/heif',
            '.mp4': 'video/mp4',
            '.mov': 'video/quicktime',
            '.avi': 'video/x-msvideo',
            '.mkv': 'video/x-matroska',
        }
        return mime_types.get(ext.lower(), 'application/octet-stream')

    def stop(self) -> None:
        """Stop the running scan."""
        self._running = False
        logger.info("[Scanner] Stop signal sent")


# Global scanner instance
scanner: Optional[MediaScanner] = None


async def get_scanner(db: Database) -> MediaScanner:
    """Get or create scanner instance."""
    global scanner
    if scanner is None:
        scanner = MediaScanner(db)
    return scanner
