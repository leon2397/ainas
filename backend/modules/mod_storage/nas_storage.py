from loguru import logger
"""
NAS Direct Mount Storage Plugin
For NAS storage mounted as local filesystem (NFS/CIFS mount points)
Provides NAS-specific optimizations: quota check, network health, concurrent-safe operations
"""

import os
import shutil
import time
import subprocess
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from PIL import Image
import io
import threading

from modules.mod_storage.base import FileStorage


class NasStorage(FileStorage):
    """NAS direct-mount storage (NFS/CIFS mount point)"""

    def __init__(self, config: Dict):
        super().__init__(config)
        self.base_path = config.get("base_path", "/nas")
        self.mount_point = config.get("mount_point", "/nas")
        self.thumbnail_path = os.path.join(self.base_path, ".thumbnails")
        self.max_concurrent_ops = config.get("max_concurrent_ops", 4)
        self._op_semaphore = threading.Semaphore(self.max_concurrent_ops)
        self._mount_check_interval = config.get("mount_check_interval", 300)
        self._last_mount_check = 0
        self._is_mounted = True
        self._lock = threading.Lock()
        os.makedirs(self.thumbnail_path, exist_ok=True)
        self._check_mount()

    def _check_mount(self) -> bool:
        """Check if NAS mount point is available"""
        if time.time() - self._last_mount_check < self._mount_check_interval:
            return self._is_mounted

        with self._lock:
            self._last_mount_check = time.time()
            try:
                if os.name == "nt":
                    self._is_mounted = os.path.exists(self.base_path)
                else:
                    result = subprocess.run(
                        ["mountpoint", "-q", self.mount_point],
                        capture_output=True, timeout=5
                    )
                    self._is_mounted = (result.returncode == 0)
                    if not self._is_mounted:
                        self._is_mounted = os.path.ismount(self.mount_point)

                if not self._is_mounted:
                    logger.info(f"[WARN] NAS mount point not available: {self.mount_point}")

                return self._is_mounted
            except Exception as e:
                logger.info(f"[WARN] Mount check failed: {e}")
                self._is_mounted = os.path.exists(self.base_path)
                return self._is_mounted

    def _full_path(self, path: str) -> str:
        """Resolve full path within NAS"""
        if os.path.isabs(path):
            return path
        return os.path.join(self.base_path, path)

    def list_files(self, path: str) -> List[str]:
        """List files under path, with mount check"""
        if not self._check_mount():
            return []

        full_path = self._full_path(path)
        if not os.path.exists(full_path):
            return []

        files = []
        try:
            with self._op_semaphore:
                for item in os.listdir(full_path):
                    item_path = os.path.join(full_path, item)
                    if os.path.isfile(item_path):
                        files.append(item_path)
                    elif os.path.isdir(item_path):
                        for sub in os.listdir(item_path):
                            sub_path = os.path.join(item_path, sub)
                            if os.path.isfile(sub_path):
                                files.append(sub_path)
        except PermissionError:
            logger.info(f"[WARN] Permission denied: {full_path}")
        except Exception as e:
            logger.info(f"[ERROR] list_files failed: {e}")

        return files

    def get_exif(self, filepath: str) -> Dict:
        """Read EXIF data"""
        if not self._check_mount():
            return {"error": "NAS not mounted"}

        try:
            from PIL.ExifTags import TAGS
            img = Image.open(filepath)
            exif_data = img._getexif()

            if not exif_data:
                return {}

            result = {}
            for tag_id, value in exif_data.items():
                tag = TAGS.get(tag_id, tag_id)
                result[tag] = value
            return result
        except Exception as e:
            return {"error": str(e)}

    def create_symlink(self, target_path: str, link_path: str) -> bool:
        """Create symbolic link on NAS"""
        if not self._check_mount():
            return False

        try:
            with self._op_semaphore:
                os.makedirs(os.path.dirname(link_path), exist_ok=True)

                if os.name != "nt":
                    if os.path.exists(link_path) or os.path.islink(link_path):
                        os.remove(link_path)
                    os.symlink(target_path, link_path)
                else:
                    try:
                        if os.path.exists(link_path):
                            os.remove(link_path)
                        os.symlink(target_path, link_path)
                    except OSError:
                        subprocess.run(
                            ["cmd", "/c", "mklink", "/J", link_path, target_path],
                            capture_output=True, timeout=10
                        )

                return True
        except Exception as e:
            logger.info(f"[ERROR] symlink failed: {e}")
            return False

    def move_file(self, src_path: str, dst_path: str) -> bool:
        """Move file (copy + verify + delete, NAS-safe)"""
        if not self._check_mount():
            return False

        try:
            with self._op_semaphore:
                os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                shutil.copy2(src_path, dst_path)

                src_size = os.path.getsize(src_path)
                dst_size = os.path.getsize(dst_path)
                if src_size == dst_size:
                    os.remove(src_path)
                    return True
                else:
                    logger.info(f"[WARN] Move verify failed: src={src_size}, dst={dst_size}")
                    os.remove(dst_path)
                    return False
        except Exception as e:
            logger.info(f"[ERROR] move_file failed: {e}")
            return False

    def copy_file(self, src_path: str, dst_path: str) -> bool:
        """Copy file with NAS-safe concurrency"""
        if not self._check_mount():
            return False

        try:
            with self._op_semaphore:
                os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                shutil.copy2(src_path, dst_path)
                return True
        except Exception as e:
            logger.info(f"[ERROR] copy failed: {e}")
            return False

    def is_support_symlink(self) -> bool:
        """Check symlink support"""
        if os.name != "nt":
            return True
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\AppModelUnlock"
            )
            value, _ = winreg.QueryValueEx(key, "AllowDevelopmentWithoutDevLicense")
            return value == 1
        except Exception:
            return False

    def get_thumbnail(self, filepath: str, size: Tuple[int, int] = (200, 200)) -> bytes:
        """Generate thumbnail with NAS-safe caching"""
        if not self._check_mount():
            return b""

        try:
            cache_file = os.path.join(
                self.thumbnail_path,
                f"{os.path.basename(filepath)}_{size[0]}x{size[1]}.jpg"
            )

            if os.path.exists(cache_file):
                with self._op_semaphore:
                    with open(cache_file, "rb") as f:
                        return f.read()

            with self._op_semaphore:
                img = Image.open(filepath)
                img.thumbnail(size, Image.Resampling.LANCZOS)
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")

                buffer = io.BytesIO()
                img.save(buffer, format="JPEG", quality=85)
                data = buffer.getvalue()

                with open(cache_file, "wb") as f:
                    f.write(data)

                return data
        except Exception as e:
            logger.info(f"[ERROR] thumbnail failed: {e}")
            return b""

    def get_file_info(self, filepath: str) -> Dict:
        """Get file info with NAS health check"""
        if not self._check_mount():
            return {"error": "NAS not mounted"}

        try:
            stat = os.stat(filepath)
            info = {
                "size": stat.st_size,
                "created": stat.st_ctime,
                "modified": stat.st_mtime,
            }
            try:
                img = Image.open(filepath)
                info.update({
                    "type": img.format,
                    "width": img.width,
                    "height": img.height,
                    "mode": img.mode,
                })
            except Exception:
                pass
            return info
        except Exception as e:
            return {"error": str(e)}

    def ensure_directory(self, path: str) -> bool:
        if not self._check_mount():
            return False
        try:
            full_path = self._full_path(path)
            os.makedirs(full_path, exist_ok=True)
            return True
        except Exception:
            return False

    def file_exists(self, path: str) -> bool:
        if not self._check_mount():
            return False
        return os.path.exists(self._full_path(path))

    def delete_file(self, path: str) -> bool:
        if not self._check_mount():
            return False
        try:
            os.remove(self._full_path(path))
            return True
        except Exception:
            return False

    def get_storage_info(self) -> Dict:
        """Get NAS storage usage"""
        if not self._check_mount():
            return {"mounted": False}

        try:
            stat = shutil.disk_usage(self.base_path)
            return {
                "mounted": True,
                "total_gb": round(stat.total / (1024**3), 2),
                "used_gb": round(stat.used / (1024**3), 2),
                "free_gb": round(stat.free / (1024**3), 2),
                "usage_percent": round(stat.used / stat.total * 100, 1),
                "mount_point": self.mount_point,
            }
        except Exception as e:
            return {"mounted": True, "error": str(e)}

    def check_health(self) -> Dict:
        """NAS health check (mount + disk + write test + latency)"""
        start = time.time()
        mounted = self._check_mount()
        latency = round((time.time() - start) * 1000, 1)

        info = {"mounted": mounted, "latency_ms": latency}

        if mounted:
            storage = self.get_storage_info()
            info.update(storage)

        if mounted:
            try:
                test_file = os.path.join(self.base_path, ".nas_health_check")
                with self._op_semaphore:
                    with open(test_file, "w") as f:
                        f.write("health")
                    os.remove(test_file)
                info["writable"] = True
            except Exception:
                info["writable"] = False

        return info


def create_storage(config: Dict) -> NasStorage:
    """Create NasStorage instance"""
    return NasStorage(config)
