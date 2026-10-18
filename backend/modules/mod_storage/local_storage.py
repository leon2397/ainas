from loguru import logger
"""
Local Storage Plugin
V2.0 Phase 1: 架构修复 - 正确继承 FileStorage

继承链: BasePlugin → StoragePlugin → FileStorage → LocalStoragePlugin
"""

import os
import shutil
import platform
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import logging
import mimetypes

# 导入 FileStorage 基类（已继承 StoragePlugin）
from modules.mod_storage.base import FileStorage
from modules.mod_storage.base import PluginManifest, PluginType, PluginState

logger = logger.bind(name="ai_nas.plugins.storage.local")


class LocalStoragePlugin(FileStorage):
    """
    本地文件存储插件
    
    功能：
    - 本地文件系统操作
    - EXIF 读取（通过 Pillow）
    - 缩略图生成
    - 软链接创建（Linux/Windows开发者模式）
    - 文件移动/复制
    """
    
    @staticmethod
    def get_manifest() -> PluginManifest:
        """获取插件清单"""
        return PluginManifest(
            id="local-storage",
            name="本地存储",
            version="2.0.0",
            description="使用本地文件系统存储媒体文件（支持EXIF/缩略图/软链接）",
            author="AI-NAS Team",
            plugin_type=PluginType.STORAGE,
            tags=["storage", "local", "builtin", "exif", "thumbnail"],
            icon="folder",
            requirements=["Pillow>=9.0.0"],
            config_schema={
                "type": "object",
                "properties": {
                    "base_path": {
                        "type": "string",
                        "title": "存储路径",
                        "description": "媒体文件的本地存储路径"
                    },
                    "max_size_gb": {
                        "type": "number",
                        "title": "最大存储大小(GB)",
                        "default": 100
                    },
                    "thumbnail_cache": {
                        "type": "string",
                        "title": "缩略图缓存路径",
                        "default": "data/thumbnails"
                    }
                },
                "required": ["base_path"]
            }
        )
    
    def __init__(self, manifest: PluginManifest, config: Dict):
        super().__init__(manifest, config)
        self.base_path = config.get("base_path", "data/media")
        self.max_size_gb = config.get("max_size_gb", 100)
        self.thumbnail_cache = config.get("thumbnail_cache", "data/thumbnails")
        self._connected = False
    
    # ========== StoragePlugin 基础方法 ==========
    
    def initialize(self) -> bool:
        """初始化插件"""
        try:
            # 创建主存储目录
            Path(self.base_path).mkdir(parents=True, exist_ok=True)
            
            # 创建缩略图缓存目录
            Path(self.thumbnail_cache).mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Local storage initialized at {self.base_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize local storage: {e}")
            return False
    
    def enable(self) -> bool:
        """启用插件"""
        if self.initialize():
            self.state = PluginState.ENABLED
            logger.info("Local storage plugin enabled")
            return True
        return False
    
    def disable(self) -> bool:
        """禁用插件"""
        self.state = PluginState.DISABLED
        self._connected = False
        logger.info("Local storage plugin disabled")
        return True
    
    def cleanup(self) -> bool:
        """清理资源"""
        self._connected = False
        logger.info("Local storage cleanup completed")
        return True
    
    def connect(self) -> bool:
        """连接存储"""
        if not Path(self.base_path).exists():
            Path(self.base_path).mkdir(parents=True, exist_ok=True)
        self._connected = True
        logger.info(f"Connected to local storage: {self.base_path}")
        return True
    
    def disconnect(self) -> bool:
        """断开连接"""
        self._connected = False
        logger.info("Disconnected from local storage")
        return True
    
    def list_files(self, path: str = "/") -> List[Dict]:
        """列出文件"""
        full_path = self.resolve_path(path)
        if not full_path.exists():
            return []
        
        files = []
        for item in full_path.iterdir():
            try:
                stat = item.stat()
                files.append({
                    "name": item.name,
                    "path": str(item.relative_to(self.base_path)),
                    "type": "directory" if item.is_dir() else "file",
                    "size": stat.st_size if item.is_file() else 0,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "created": datetime.fromtimestamp(stat.st_ctime).isoformat()
                })
            except Exception as e:
                logger.warning(f"Failed to stat {item}: {e}")
        
        return files
    
    def upload_file(self, local_path: str, remote_path: str) -> bool:
        """上传文件（复制到存储目录）"""
        try:
            source = Path(local_path)
            dest = self.resolve_path(remote_path)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, dest)
            logger.info(f"Uploaded {local_path} to {remote_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to upload file: {e}")
            return False
    
    def download_file(self, remote_path: str, local_path: str) -> bool:
        """下载文件（从存储目录复制）"""
        try:
            source = self.resolve_path(remote_path)
            dest = Path(local_path)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, dest)
            logger.info(f"Downloaded {remote_path} to {local_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to download file: {e}")
            return False
    
    def delete_file(self, remote_path: str) -> bool:
        """删除文件"""
        try:
            path = self.resolve_path(remote_path)
            if path.exists():
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    path.unlink()
                logger.info(f"Deleted {remote_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete file: {e}")
            return False
    
    # ========== FileStorage 扩展方法 ==========
    
    def resolve_path(self, filepath: str) -> Path:
        """解析文件路径为绝对路径"""
        # 处理 Windows 路径分隔符
        filepath = filepath.replace("\\", "/")
        return Path(self.base_path) / filepath.lstrip("/")
    
    def get_exif(self, filepath: str) -> Dict:
        """读取文件 EXIF 信息"""
        try:
            from PIL import Image
            from PIL.ExifTags import TAGS, GPSTAGS
            
            full_path = self.resolve_path(filepath)
            if not full_path.exists():
                return {}
            
            exif_data = {}
            
            with Image.open(full_path) as img:
                # 基本信息
                exif_data["width"] = img.width
                exif_data["height"] = img.height
                exif_data["format"] = img.format
                exif_data["mode"] = img.mode
                
                # EXIF 数据
                if hasattr(img, "_getexif") and img._getexif():
                    raw_exif = img._getexif()
                    
                    for tag_id, value in raw_exif.items():
                        tag = TAGS.get(tag_id, tag_id)
                        
                        # 拍摄时间
                        if tag == "DateTimeOriginal":
                            exif_data["datetime"] = str(value)
                        elif tag == "DateTime":
                            exif_data["datetime"] = str(value) if "datetime" not in exif_data else exif_data["datetime"]
                        
                        # 设备信息
                        elif tag == "Make":
                            exif_data["make"] = str(value)
                        elif tag == "Model":
                            exif_data["model"] = str(value)
                        
                        # 方向
                        elif tag == "Orientation":
                            exif_data["orientation"] = int(value)
                        
                        # GPS 信息
                        elif tag == "GPSInfo":
                            gps_data = {}
                            for gps_tag_id, gps_value in value.items():
                                gps_tag = GPSTAGS.get(gps_tag_id, gps_tag_id)
                                gps_data[gps_tag] = gps_value
                            
                            # 解析 GPS 坐标
                            if "GPSLatitude" in gps_data and "GPSLongitude" in gps_data:
                                lat = self._convert_gps_coord(gps_data["GPSLatitude"], gps_data.get("GPSLatitudeRef", "N"))
                                lon = self._convert_gps_coord(gps_data["GPSLongitude"], gps_data.get("GPSLongitudeRef", "E"))
                                exif_data["gps"] = {"lat": lat, "lon": lon}
                
            return exif_data
            
        except Exception as e:
            logger.warning(f"Failed to read EXIF from {filepath}: {e}")
            return {}
    
    def _convert_gps_coord(self, coord: Tuple, ref: str) -> float:
        """转换 GPS 坐标（度分秒 → 十进制度）"""
        try:
            degrees = float(coord[0])
            minutes = float(coord[1])
            seconds = float(coord[2])
            
            decimal = degrees + minutes / 60 + seconds / 3600
            
            if ref in ["S", "W"]:
                decimal = -decimal
            
            return decimal
        except Exception:
            return 0.0
    
    def create_symlink(self, target_path: str, link_path: str) -> bool:
        """创建软链接"""
        try:
            target = self.resolve_path(target_path)
            link = self.resolve_path(link_path)
            
            if not target.exists():
                logger.error(f"Target does not exist: {target_path}")
                return False
            
            # 确保链接目录存在
            link.parent.mkdir(parents=True, exist_ok=True)
            
            # 删除已存在的链接
            if link.exists() or link.is_symlink():
                link.unlink()
            
            # 创建软链接
            if platform.system() == "Windows":
                # Windows: 需要管理员权限或开发者模式
                # 使用 junction（目录）或 symlink（文件）
                if target.is_dir():
                    # 目录使用 junction（不需要管理员权限）
                    import subprocess
                    subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)], check=True)
                else:
                    # 文件使用 symlink（需要管理员权限）
                    os.symlink(str(target), str(link))
            else:
                # Linux: 直接创建软链接
                os.symlink(str(target), str(link))
            
            logger.info(f"Created symlink: {link_path} → {target_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create symlink: {e}")
            return False
    
    def move_file(self, src_path: str, dst_path: str) -> bool:
        """移动文件（不复制）"""
        try:
            src = self.resolve_path(src_path)
            dst = self.resolve_path(dst_path)
            
            if not src.exists():
                logger.error(f"Source does not exist: {src_path}")
                return False
            
            # 确保目标目录存在
            dst.parent.mkdir(parents=True, exist_ok=True)
            
            # 移动文件
            shutil.move(str(src), str(dst))
            
            logger.info(f"Moved file: {src_path} → {dst_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to move file: {e}")
            return False
    
    def is_support_symlink(self) -> bool:
        """判断是否支持软链接"""
        system = platform.system()
        
        if system == "Linux":
            return True
        
        if system == "Windows":
            # Windows 10 开发者模式支持软链接
            # 检查是否有创建软链接的权限
            try:
                # 尝试创建测试链接
                test_file = Path(self.base_path) / ".symlink_test"
                test_link = Path(self.base_path) / ".symlink_test_link"
                
                test_file.touch()
                try:
                    os.symlink(str(test_file), str(test_link))
                    test_link.unlink()
                    test_file.unlink()
                    return True
                except Exception:
                    test_file.unlink()
                    return False
            except Exception:
                return False
        
        if system == "Darwin":  # macOS
            return True
        
        return False
    
    def get_thumbnail(self, filepath: str, size: Tuple[int, int] = (200, 200)) -> bytes:
        """生成缩略图"""
        try:
            from PIL import Image
            import io
            
            full_path = self.resolve_path(filepath)
            if not full_path.exists():
                return b""
            
            # 检查缓存
            cache_key = f"{filepath}_{size[0]}x{size[1]}"
            cache_path = Path(self.thumbnail_cache) / f"{hash(cache_key)}.jpg"
            
            if cache_path.exists():
                return cache_path.read_bytes()
            
            # 生成缩略图
            with Image.open(full_path) as img:
                # 处理方向
                if hasattr(img, "_getexif") and img._getexif():
                    orientation = img._getexif().get(274, 1)  # Orientation tag
                    img = self._apply_orientation(img, orientation)
                
                # 转换为 RGB（JPEG 不支持 RGBA）
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                
                # 生成缩略图
                img.thumbnail(size, Image.Resampling.LANCZOS)
                
                # 保存到缓存
                buffer = io.BytesIO()
                img.save(buffer, format="JPEG", quality=85)
                thumbnail_data = buffer.getvalue()
                
                # 写入缓存
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                cache_path.write_bytes(thumbnail_data)
                
                return thumbnail_data
                
        except Exception as e:
            logger.error(f"Failed to generate thumbnail for {filepath}: {e}")
            return b""
    
    def _apply_orientation(self, img, orientation: int):
        """应用 EXIF 方向"""
        from PIL import Image as PILImage
        
        if orientation == 2:
            img = img.transpose(PILImage.Transpose.FLIP_LEFT_RIGHT)
        elif orientation == 3:
            img = img.rotate(180, expand=True)
        elif orientation == 4:
            img = img.transpose(PILImage.Transpose.FLIP_TOP_BOTTOM)
        elif orientation == 5:
            img = img.rotate(-90, expand=True).transpose(PILImage.Transpose.FLIP_LEFT_RIGHT)
        elif orientation == 6:
            img = img.rotate(-90, expand=True)
        elif orientation == 7:
            img = img.rotate(90, expand=True).transpose(PILImage.Transpose.FLIP_LEFT_RIGHT)
        elif orientation == 8:
            img = img.rotate(90, expand=True)
        
        return img
    
    def get_file_info(self, filepath: str) -> Dict:
        """获取文件详细信息"""
        try:
            full_path = self.resolve_path(filepath)
            if not full_path.exists():
                return {}
            
            stat = full_path.stat()
            
            # MIME 类型
            mime_type, _ = mimetypes.guess_type(str(full_path))
            
            # 文件类型
            if full_path.is_dir():
                file_type = "directory"
            elif mime_type and mime_type.startswith("image/"):
                file_type = "image"
            elif mime_type and mime_type.startswith("video/"):
                file_type = "video"
            else:
                file_type = "file"
            
            return {
                "name": full_path.name,
                "path": str(full_path),
                "relative_path": filepath,
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "type": file_type,
                "mime": mime_type or "application/octet-stream",
                "extension": full_path.suffix.lower(),
                "is_symlink": full_path.is_symlink(),
                "is_dir": full_path.is_dir()
            }
            
        except Exception as e:
            logger.error(f"Failed to get file info for {filepath}: {e}")
            return {}
    
    def get_storage_info(self) -> Dict:
        """获取存储信息"""
        try:
            total, used, free = shutil.disk_usage(self.base_path)
            return {
                "total": total,
                "used": used,
                "free": free,
                "used_percent": (used / total * 100) if total > 0 else 0,
                "max_size_gb": self.max_size_gb,
                "base_path": self.base_path
            }
        except Exception as e:
            logger.error(f"Failed to get storage info: {e}")
            return {}


# 兼容性别名
LocalStorage = LocalStoragePlugin