"""
Media Scanner Service
Scans directories for media files and indexes them.

计数准确性设计（2026-10-18 加固，详见 docs/TROUBLESHOOTING.md「素材计数失真」）：
1. 单次 os.walk 全树遍历（替代按扩展名多次 rglob），后缀统一小写比较，
   Linux 大小写敏感文件系统下不漏扫 `.Jpg` 这类混合大小写文件。
2. 重扫时对「扫描范围内、磁盘上已消失」的记录自动软删除
   （is_deleted=TRUE，可恢复），保证计数只反映真实存在的文件，只增不删的
   幽灵记录问题就此消除。
3. 统计口径：total = images + videos + errors；new/updated/unchanged/removed
   各自独立，unchanged 要求 file_size 一致且未被软删除。
4. reconcile() 提供 dry-run 对账预览（不写库），供 /api/media/count/reconcile
   使用，让「数据库与磁盘是否一致」随时可验证。
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Callable, Tuple

from modules.mod_database.db import Database
from core.logger import logger

# Supported media formats
# 注意：.ts 刻意不收（与 TypeScript 源码歧义，扫到代码目录会误索引为视频）；
# 如确有 .ts 视频需求，可通过 scan_directory(extensions={...}) 显式指定。
IMAGE_EXTENSIONS = {
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.heic', '.heif',
    '.tiff', '.tif', '.raw', '.cr2', '.nef', '.arw', '.dng',
    '.avif', '.jfif', '.pjpeg',
}
VIDEO_EXTENSIONS = {
    '.mp4', '.mov', '.avi', '.mkv', '.flv', '.wmv', '.m4v', '.mpg', '.mpeg',
    '.3gp', '.3g2', '.m2ts', '.mts', '.rmvb', '.ogv', '.vob',
}
ALL_MEDIA_EXTENSIONS = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS


def _normalize_path(p) -> str:
    """规范化路径用于集合比较：绝对化 + normcase（Windows 下大小写不敏感）。"""
    return os.path.normcase(os.path.normpath(str(p)))


def _is_under(child_norm: str, parent_norm: str) -> bool:
    """child 是否位于 parent 目录之内（含自身）。"""
    if child_norm == parent_norm:
        return True
    return child_norm.startswith(parent_norm + os.sep)


class MediaScanner:
    """Media file scanner with incremental scanning support."""

    def __init__(self, db: Database):
        self.db = db
        self._running = False
        self._progress_callback: Optional[Callable] = None

    def set_progress_callback(self, callback: Callable) -> None:
        """Set callback for progress updates."""
        self._progress_callback = callback

    # ── 扫描主流程 ───────────────────────────────────────────────────────

    async def scan_directory(
        self,
        root_path: str,
        recursive: bool = True,
        extensions: Optional[set] = None,
        file_type: Optional[str] = None,
    ) -> Dict:
        """
        Scan a directory for media files.

        Args:
            root_path: 扫描根目录
            recursive: 是否递归子目录
            extensions: 自定义扩展名集合（默认全部媒体格式）
            file_type: 'image' / 'video' / None(全部)，在 extensions 基础上再过滤

        Returns:
            Dict with scan statistics:
              total/images/videos 本次遍历到的文件数
              new/updated/unchanged 入库结果
              removed 自动软删除的失效记录数
              errors 处理失败数（error_files 为明细，最多 50 条）
              walk_errors 目录不可读等遍历错误数
        """
        if extensions is None:
            extensions = ALL_MEDIA_EXTENSIONS
        allowed = self._filter_extensions(extensions, file_type)

        self._running = True
        stats = {
            'total': 0, 'images': 0, 'videos': 0,
            'new': 0, 'updated': 0, 'unchanged': 0, 'removed': 0,
            'errors': 0, 'walk_errors': 0,
            'error_files': [],
        }

        try:
            root = Path(root_path)
            if not root.exists():
                return {'error': f'Path does not exist: {root_path}'}

            # 1) 单次全树遍历收集媒体文件（大小写归一）
            files, walk_errors = self._collect_files(root, recursive, allowed)
            stats['total'] = len(files)
            stats['walk_errors'] = len(walk_errors)
            for err in walk_errors[:50]:
                logger.warning(f"[Scanner] Walk error: {err}")
            logger.info(f"[Scanner] Start scanning: {root_path}, found {len(files)} files")

            # 2) 逐文件入库/更新
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
                    else:
                        stats['unchanged'] += 1

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
                    if len(stats['error_files']) < 50:
                        stats['error_files'].append(str(filepath))
                    logger.error(f"[Scanner] Error processing {filepath}: {e}")

            # 3) 对账清理：软删除扫描范围内磁盘已消失的记录。
            # 仅递归扫描执行——非递归扫描只看到根目录一层，
            # 子目录里的现存文件不在 files 中，会被误判为消失。
            # 仅清理后缀落在本次 allowed 范围内的记录——自定义扩展名/
            # file_type 过滤扫描不得波及其他类型的历史记录。
            if recursive:
                stats['removed'] = await self._remove_missing(root, files, allowed)

            logger.info(f"[Scanner] Scan complete: {stats}")
            return stats

        finally:
            self._running = False

    async def reconcile(self, root_path: str, recursive: bool = True,
                        extensions: Optional[set] = None,
                        file_type: Optional[str] = None) -> Dict:
        """
        对账预览（dry-run，不写库）：比较数据库记录与磁盘实际文件。

        consistent 的含义：/api/media/count/by-type 的计数与磁盘实际一致。
        四类差异：
          phantom       库里有(未删除)、磁盘没了 → 下次重扫自动软删除
          missing       磁盘有、库里完全没有     → 下次重扫自动索引
          revivable     磁盘有、库里记录被软删除 → 下次重扫自动复活
          type_mismatch 同路径但 file_type 与扩展名不符
        """
        if extensions is None:
            extensions = ALL_MEDIA_EXTENSIONS
        allowed = self._filter_extensions(extensions, file_type)

        root = Path(root_path)
        if not root.exists():
            return {'error': f'Path does not exist: {root_path}'}

        files, walk_errors = self._collect_files(root, recursive, allowed)
        root_norm = _normalize_path(root)

        # norm_path -> (原始路径串, 后缀小写)
        disk_map: Dict[str, Tuple[str, str]] = {}
        for f in files:
            disk_map[_normalize_path(f)] = (str(f), f.suffix.lower())

        disk_images = sum(1 for _, s in disk_map.values() if s in IMAGE_EXTENSIONS)
        disk_videos = len(disk_map) - disk_images

        rows = await self.db.fetchall(
            "SELECT id, file_path, file_type, is_deleted FROM media_files")
        row_by_norm = {_normalize_path(r['file_path']): r for r in rows}

        db_total = db_images = db_videos = db_deleted = 0
        phantom: List[str] = []
        type_mismatch: List[str] = []

        for row in rows:
            p_norm = _normalize_path(row['file_path'])
            if not _is_under(p_norm, root_norm):
                continue  # 其他根目录（上传目录/其他盘）不在对账范围
            if Path(row['file_path']).suffix.lower() not in allowed:
                continue  # 超出本次扫描类型范围
            if row['is_deleted']:
                db_deleted += 1
                continue
            db_total += 1
            if row['file_type'] == 'image':
                db_images += 1
            else:
                db_videos += 1
            if p_norm not in disk_map:
                phantom.append(row['file_path'])
            elif ((row['file_type'] == 'image') !=
                  (disk_map[p_norm][1] in IMAGE_EXTENSIONS)):
                type_mismatch.append(row['file_path'])

        missing: List[str] = []
        revivable: List[str] = []
        for p_norm, (orig, _suffix) in disk_map.items():
            row = row_by_norm.get(p_norm)
            if row is None:
                missing.append(orig)
            elif row['is_deleted']:
                revivable.append(orig)

        consistent = not (phantom or missing or revivable or type_mismatch)
        return {
            'root': str(root),
            'disk': {'total': len(disk_map), 'images': disk_images,
                     'videos': disk_videos},
            'db': {'total': db_total, 'images': db_images,
                   'videos': db_videos, 'soft_deleted': db_deleted},
            'diff': {
                'phantom': len(phantom),
                'missing': len(missing),
                'revivable': len(revivable),
                'type_mismatch': len(type_mismatch),
            },
            'consistent': consistent,
            'samples': {
                'phantom': phantom[:10],
                'missing': missing[:10],
                'revivable': revivable[:10],
                'type_mismatch': type_mismatch[:10],
            },
            'walk_errors': len(walk_errors),
        }

    def stop(self) -> None:
        """Stop the running scan."""
        self._running = False
        logger.info("[Scanner] Stop signal sent")

    # ── 内部实现 ─────────────────────────────────────────────────────────

    @staticmethod
    def _filter_extensions(extensions: set,
                           file_type: Optional[str]) -> set:
        """按 file_type 过滤扩展名集合。"""
        if file_type == 'image':
            return {e for e in extensions if e in IMAGE_EXTENSIONS}
        if file_type == 'video':
            return {e for e in extensions if e in VIDEO_EXTENSIONS}
        return set(extensions)

    def _collect_files(self, root: Path, recursive: bool,
                       allowed: set) -> Tuple[List[Path], List[str]]:
        """
        单次遍历收集媒体文件。后缀统一转小写后比较，
        `.JPG` / `.Jpg` / `.jpg` 一视同仁（Linux 安全）。
        返回 (文件列表, 遍历错误列表)。
        """
        files: List[Path] = []
        errors: List[str] = []

        def _on_error(err: OSError):
            errors.append(str(err))

        if recursive:
            # followlinks=False（默认）：不跟随符号链接目录，
            # 防止链接环与同一份文件被重复计数。
            for dirpath, _dirnames, filenames in os.walk(root, onerror=_on_error):
                for fn in filenames:
                    if Path(fn).suffix.lower() in allowed:
                        files.append(Path(dirpath) / fn)
        else:
            try:
                with os.scandir(root) as it:
                    for entry in it:
                        try:
                            if entry.is_file() and \
                                    Path(entry.name).suffix.lower() in allowed:
                                files.append(Path(entry.path))
                        except OSError as e:
                            errors.append(str(e))
            except OSError as e:
                errors.append(str(e))

        return files, errors

    async def _remove_missing(self, root: Path, disk_files: List[Path],
                              allowed: set) -> int:
        """
        软删除「扫描范围内、磁盘上已消失」的记录。
        只动 is_deleted=TRUE（可恢复），绝不物理删除。
        范围外的记录（其他盘/上传目录/其他后缀类型）一律不碰。
        """
        root_norm = _normalize_path(root)
        disk_norm = {_normalize_path(f) for f in disk_files}

        rows = await self.db.fetchall(
            "SELECT id, file_path FROM media_files WHERE is_deleted = FALSE")

        removed = 0
        for row in rows:
            p_norm = _normalize_path(row['file_path'])
            if not _is_under(p_norm, root_norm):
                continue
            if Path(row['file_path']).suffix.lower() not in allowed:
                continue
            if p_norm not in disk_norm:
                await self.db.execute(
                    """UPDATE media_files SET is_deleted = TRUE,
                       updated_at = CURRENT_TIMESTAMP WHERE id = ?""",
                    (row['id'],)
                )
                removed += 1

        if removed:
            logger.info(
                f"[Scanner] Soft-deleted {removed} vanished record(s) "
                f"under {root}")
        return removed

    async def _process_file(self, filepath: str) -> str:
        """
        Process a single media file and add to database.
        Returns: 'new' | 'updated' | 'unchanged'
          updated 含：体积变化、曾被软删除后重新出现（复活）
        """
        path = Path(filepath)

        existing = await self.db.fetchone(
            "SELECT id, file_size, is_deleted FROM media_files WHERE file_path = ?",
            (filepath,)
        )

        stat = path.stat()
        file_size = stat.st_size

        ext = path.suffix.lower()
        file_type = 'image' if ext in IMAGE_EXTENSIONS else 'video'

        if existing:
            # 体积一致且未被软删除 →  genuinely 没变，不碰 updated_at
            if existing.get('file_size') == file_size and not existing.get('is_deleted'):
                return 'unchanged'
            # 体积变化，或软删除记录重新出现（复活）
            await self.db.execute(
                """UPDATE media_files SET
                   file_size = ?, file_type = ?, is_deleted = FALSE,
                   updated_at = CURRENT_TIMESTAMP
                   WHERE file_path = ?""",
                (file_size, file_type, filepath)
            )
            logger.debug(f"[Scanner] Updated: {filepath}")
            return 'updated'
        else:
            # Insert new record
            import datetime
            modified_time = datetime.datetime.fromtimestamp(stat.st_mtime)
            exif = self._extract_exif(filepath) if file_type == 'image' else {}
            file_data = {
                'file_path': filepath,
                'file_name': path.name,
                'file_type': file_type,
                'file_size': file_size,
                'mime_type': self._get_mime_type(ext),
                'device_id': 'local',
                'taken_at': exif.get('datetime') or modified_time.isoformat(),
                'camera_make': exif.get('make'),
                'camera_model': exif.get('model'),
                'gps_lat': exif.get('gps_lat'),
                'gps_lon': exif.get('gps_lon'),
            }
            await self.db.add_media_file(file_data)
            logger.debug(f"[Scanner] New file indexed: {filepath}")
            return 'new'

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
            '.avif': 'image/avif',
            '.mp4': 'video/mp4',
            '.mov': 'video/quicktime',
            '.avi': 'video/x-msvideo',
            '.mkv': 'video/x-matroska',
            '.m2ts': 'video/mp2t',
            '.rmvb': 'application/vnd.rn-realmedia-vbr',
        }
        return mime_types.get(ext.lower(), 'application/octet-stream')


# Global scanner instance
scanner: Optional[MediaScanner] = None


async def get_scanner(db: Database) -> MediaScanner:
    """Get or create scanner instance."""
    global scanner
    if scanner is None:
        scanner = MediaScanner(db)
    return scanner
