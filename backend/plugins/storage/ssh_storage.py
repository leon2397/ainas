from loguru import logger
"""
SSH Storage Plugin
V2.0 Phase 1: 架构修复 - 正确继承 FileStorage

继承链: BasePlugin → StoragePlugin → FileStorage → SSHStoragePlugin
"""

import os
import io
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import logging
import mimetypes

try:
    import paramiko
    PARAMIKO_AVAILABLE = True
except ImportError:
    PARAMIKO_AVAILABLE = False

# 导入 FileStorage 基类
from core.storage import FileStorage
from plugins.base import PluginManifest, PluginType, PluginState

logger = logger.bind(name="ai_nas.plugins.storage.ssh")


class SSHStoragePlugin(FileStorage):
    """
    SSH/SFTP 远程存储插件
    
    功能：
    - SSH/SFTP 协议连接远程服务器
    - 远程文件操作（上传/下载/删除）
    - 缩略图生成（下载后本地生成）
    - 注意：远程存储不支持软链接
    """
    
    @staticmethod
    def get_manifest() -> PluginManifest:
        return PluginManifest(
            id="ssh-storage",
            name="SSH/SFTP 存储",
            version="2.0.0",
            description="通过 SSH/SFTP 协议连接远程服务器存储文件",
            author="AI-NAS Team",
            plugin_type=PluginType.STORAGE,
            tags=["storage", "remote", "ssh", "sftp", "exif", "thumbnail"],
            icon="cloud-upload",
            requirements=["paramiko"],
            config_schema={
                "type": "object",
                "properties": {
                    "host": {
                        "type": "string",
                        "title": "服务器地址"
                    },
                    "port": {
                        "type": "number",
                        "title": "端口",
                        "default": 22
                    },
                    "username": {
                        "type": "string",
                        "title": "用户名"
                    },
                    "password": {
                        "type": "string",
                        "title": "密码",
                        "format": "password"
                    },
                    "remote_path": {
                        "type": "string",
                        "title": "远程路径",
                        "default": "/data/media"
                    },
                    "thumbnail_cache": {
                        "type": "string",
                        "title": "缩略图缓存路径",
                        "default": "data/thumbnails"
                    }
                },
                "required": ["host", "username", "password", "remote_path"]
            }
        )
    
    def __init__(self, manifest: PluginManifest, config: Dict):
        super().__init__(manifest, config)
        self.host = config.get("host")
        self.port = config.get("port", 22)
        self.username = config.get("username")
        self.password = config.get("password")
        self.remote_path = config.get("remote_path", "/data/media")
        self.thumbnail_cache = config.get("thumbnail_cache", "data/thumbnails")
        self._client = None
        self._sftp = None
    
    # ========== StoragePlugin 基础方法 ==========
    
    def initialize(self) -> bool:
        """初始化"""
        if not PARAMIKO_AVAILABLE:
            logger.error("paramiko library not available")
            return False
        
        # 创建缩略图缓存目录
        from pathlib import Path
        Path(self.thumbnail_cache).mkdir(parents=True, exist_ok=True)
        
        return True
    
    def enable(self) -> bool:
        """启用"""
        if self.initialize():
            self.state = PluginState.ENABLED
            return True
        return False
    
    def disable(self) -> bool:
        """禁用"""
        self.disconnect()
        self.state = PluginState.DISABLED
        return True
    
    def cleanup(self) -> bool:
        """清理"""
        self.disconnect()
        return True
    
    def connect(self) -> bool:
        """连接服务器"""
        if not PARAMIKO_AVAILABLE:
            logger.error("paramiko library not available")
            return False
        
        try:
            self._client = paramiko.SSHClient()
            self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            self._client.connect(
                hostname=self.host,
                port=self.port,
                username=self.username,
                password=self.password
            )
            
            self._sftp = self._client.open_sftp()
            logger.info(f"Connected to {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect via SSH: {e}")
            return False
    
    def disconnect(self) -> bool:
        """断开连接"""
        try:
            if self._sftp:
                self._sftp.close()
                self._sftp = None
            if self._client:
                self._client.close()
                self._client = None
            logger.info("Disconnected from SSH server")
            return True
        except Exception as e:
            logger.error(f"Failed to disconnect: {e}")
            return False
    
    def list_files(self, path: str = "/") -> List[Dict]:
        """列出文件"""
        if not self._sftp:
            if not self.connect():
                return []
        
        full_path = self.remote_path.rstrip("/") + "/" + path.lstrip("/")
        
        try:
            files = self._sftp.listdir_attr(full_path)
            result = []
            for f in files:
                is_dir = f.st_mode & 0o170000 == 0o40000
                result.append({
                    "name": f.filename,
                    "path": path.rstrip("/") + "/" + f.filename,
                    "type": "directory" if is_dir else "file",
                    "size": f.st_size,
                    "modified": datetime.fromtimestamp(f.st_mtime).isoformat()
                })
            return result
        except Exception as e:
            logger.error(f"Failed to list files: {e}")
            return []
    
    def upload_file(self, local_path: str, remote_path: str) -> bool:
        """上传文件"""
        if not self._sftp:
            if not self.connect():
                return False
        
        full_remote = self.remote_path.rstrip("/") + "/" + remote_path.lstrip("/")
        
        try:
            # 确保目录存在
            dirs = "/".join(full_remote.split("/")[:-1])
            try:
                self._sftp.stat(dirs)
            except FileNotFoundError:
                self._mkdir_p(dirs)
            
            self._sftp.put(local_path, full_remote)
            logger.info(f"Uploaded to {full_remote}")
            return True
        except Exception as e:
            logger.error(f"Failed to upload: {e}")
            return False
    
    def _mkdir_p(self, path: str):
        """递归创建目录"""
        if not self._sftp:
            return
        
        dirs = path.split("/")
        current = ""
        for d in dirs:
            if not d:
                continue
            current += "/" + d
            try:
                self._sftp.stat(current)
            except FileNotFoundError:
                self._sftp.mkdir(current)
    
    def download_file(self, remote_path: str, local_path: str) -> bool:
        """下载文件"""
        if not self._sftp:
            if not self.connect():
                return False
        
        full_remote = self.remote_path.rstrip("/") + "/" + remote_path.lstrip("/")
        
        try:
            # 确保本地目录存在
            from pathlib import Path
            Path(local_path).parent.mkdir(parents=True, exist_ok=True)
            
            self._sftp.get(full_remote, local_path)
            logger.info(f"Downloaded from {full_remote}")
            return True
        except Exception as e:
            logger.error(f"Failed to download: {e}")
            return False
    
    def delete_file(self, remote_path: str) -> bool:
        """删除文件"""
        if not self._sftp:
            if not self.connect():
                return False
        
        full_remote = self.remote_path.rstrip("/") + "/" + remote_path.lstrip("/")
        
        try:
            # 检查是否是目录
            stat = self._sftp.stat(full_remote)
            if stat.st_mode & 0o170000 == 0o40000:
                # 是目录，递归删除
                self._rmdir_recursive(full_remote)
            else:
                self._sftp.remove(full_remote)
            
            logger.info(f"Deleted {full_remote}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete: {e}")
            return False
    
    def _rmdir_recursive(self, path: str):
        """递归删除目录"""
        if not self._sftp:
            return
        
        files = self._sftp.listdir_attr(path)
        for f in files:
            full_path = path + "/" + f.filename
            if f.st_mode & 0o170000 == 0o40000:
                self._rmdir_recursive(full_path)
            else:
                self._sftp.remove(full_path)
        
        self._sftp.rmdir(path)
    
    # ========== FileStorage 扩展方法 ==========
    
    def resolve_path(self, filepath: str) -> str:
        """解析远程文件路径"""
        return self.remote_path.rstrip("/") + "/" + filepath.lstrip("/")
    
    def get_exif(self, filepath: str) -> Dict:
        """
        读取文件 EXIF 信息
        
        对于远程文件，需要先下载到内存中
        """
        try:
            from PIL import Image
            
            if not self._sftp:
                if not self.connect():
                    return {}
            
            full_path = self.resolve_path(filepath)
            
            # 读取文件到内存
            with io.BytesIO() as buf:
                self._sftp.getfo(full_path, buf)
                buf.seek(0)
                
                with Image.open(buf) as img:
                    exif_data = {
                        "width": img.width,
                        "height": img.height,
                        "format": img.format,
                        "mode": img.mode
                    }
                    
                    # 尝试读取 EXIF
                    if hasattr(img, "_getexif") and img._getexif():
                        from PIL.ExifTags import TAGS
                        raw_exif = img._getexif()
                        
                        for tag_id, value in raw_exif.items():
                            tag = TAGS.get(tag_id, tag_id)
                            if tag == "DateTimeOriginal":
                                exif_data["datetime"] = str(value)
                            elif tag == "Make":
                                exif_data["make"] = str(value)
                            elif tag == "Model":
                                exif_data["model"] = str(value)
                            elif tag == "Orientation":
                                exif_data["orientation"] = int(value)
                    
                    return exif_data
                    
        except Exception as e:
            logger.warning(f"Failed to read EXIF from {filepath}: {e}")
            return {}
    
    def create_symlink(self, target_path: str, link_path: str) -> bool:
        """
        创建软链接
        
        SSH 远程存储支持软链接，使用 SFTP symlink 方法
        """
        if not self._sftp:
            if not self.connect():
                return False
        
        try:
            target_full = self.resolve_path(target_path)
            link_full = self.resolve_path(link_path)
            
            # 确保目标存在
            try:
                self._sftp.stat(target_full)
            except FileNotFoundError:
                logger.error(f"Target does not exist: {target_path}")
                return False
            
            # 删除已存在的链接
            try:
                self._sftp.remove(link_full)
            except FileNotFoundError:
                pass
            
            # 创建软链接
            self._sftp.symlink(target_full, link_full)
            
            logger.info(f"Created symlink: {link_path} → {target_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create symlink: {e}")
            return False
    
    def move_file(self, src_path: str, dst_path: str) -> bool:
        """移动文件"""
        if not self._sftp:
            if not self.connect():
                return False
        
        try:
            src_full = self.resolve_path(src_path)
            dst_full = self.resolve_path(dst_path)
            
            # 确保源文件存在
            try:
                self._sftp.stat(src_full)
            except FileNotFoundError:
                logger.error(f"Source does not exist: {src_path}")
                return False
            
            # 确保目标目录存在
            dst_dir = "/".join(dst_full.split("/")[:-1])
            try:
                self._sftp.stat(dst_dir)
            except FileNotFoundError:
                self._mkdir_p(dst_dir)
            
            # 重命名/移动
            self._sftp.rename(src_full, dst_full)
            
            logger.info(f"Moved file: {src_path} → {dst_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to move file: {e}")
            return False
    
    def is_support_symlink(self) -> bool:
        """
        判断是否支持软链接
        
        SSH/SFTP 支持软链接，返回 True
        """
        return True
    
    def get_thumbnail(self, filepath: str, size: Tuple[int, int] = (200, 200)) -> bytes:
        """
        生成缩略图
        
        下载远程文件到内存，生成缩略图
        """
        try:
            from PIL import Image
            from pathlib import Path
            
            if not self._sftp:
                if not self.connect():
                    return b""
            
            full_path = self.resolve_path(filepath)
            
            # 检查缓存
            cache_key = f"ssh_{self.host}_{filepath}_{size[0]}x{size[1]}"
            cache_path = Path(self.thumbnail_cache) / f"{hash(cache_key)}.jpg"
            
            if cache_path.exists():
                return cache_path.read_bytes()
            
            # 读取文件到内存
            with io.BytesIO() as buf:
                self._sftp.getfo(full_path, buf)
                buf.seek(0)
                
                with Image.open(buf) as img:
                    # 处理方向
                    if hasattr(img, "_getexif") and img._getexif():
                        orientation = img._getexif().get(274, 1)
                        img = self._apply_orientation(img, orientation)
                    
                    # 转换为 RGB
                    if img.mode in ("RGBA", "P"):
                        img = img.convert("RGB")
                    
                    # 生成缩略图
                    img.thumbnail(size, Image.Resampling.LANCZOS)
                    
                    # 保存
                    out_buf = io.BytesIO()
                    img.save(out_buf, format="JPEG", quality=85)
                    thumbnail_data = out_buf.getvalue()
                    
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
        if not self._sftp:
            if not self.connect():
                return {}
        
        try:
            full_path = self.resolve_path(filepath)
            
            stat = self._sftp.stat(full_path)
            
            # MIME 类型
            mime_type, _ = mimetypes.guess_type(filepath)
            
            # 文件类型
            is_dir = stat.st_mode & 0o170000 == 0o40000
            if is_dir:
                file_type = "directory"
            elif mime_type and mime_type.startswith("image/"):
                file_type = "image"
            elif mime_type and mime_type.startswith("video/"):
                file_type = "video"
            else:
                file_type = "file"
            
            return {
                "name": filepath.split("/")[-1],
                "path": full_path,
                "relative_path": filepath,
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "type": file_type,
                "mime": mime_type or "application/octet-stream",
                "is_symlink": stat.st_mode & 0o170000 == 0o120000,  # S_IFLNK
                "is_dir": is_dir,
                "permissions": oct(stat.st_mode)[-3:]
            }
            
        except Exception as e:
            logger.error(f"Failed to get file info for {filepath}: {e}")
            return {}


# 兼容性别名
SSHStorage = SSHStoragePlugin