from loguru import logger
"""
SMB/CIFS Storage Plugin
V2.0 Phase 1: 架构修复 - 正确继承 FileStorage

继承链: BasePlugin → StoragePlugin → FileStorage → SMBStoragePlugin
"""

import os
import io
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import logging
import mimetypes
from pathlib import Path

# 导入 FileStorage 基类
from modules.mod_storage.base import FileStorage
from modules.mod_storage.base import PluginManifest, PluginType, PluginState

logger = logger.bind(name="ai_nas.plugins.storage.smb")

# 尝试导入 SMB 库
try:
    from smb.SMBConnection import SMBConnection
    from smb.smb_structs import OperationFailure
    SMB_AVAILABLE = True
except ImportError:
    SMB_AVAILABLE = False


class SMBStoragePlugin(FileStorage):
    """
    SMB/CIFS 网络存储插件
    
    功能：
    - SMB/CIFS 协议连接网络存储
    - 网络文件操作
    - 注意：SMB 存储的软链接支持取决于服务器配置
    """
    
    @staticmethod
    def get_manifest() -> PluginManifest:
        return PluginManifest(
            id="smb-storage",
            name="SMB/CIFS 存储",
            version="2.0.0",
            description="通过 SMB/CIFS 协议连接网络存储设备",
            author="AI-NAS Team",
            plugin_type=PluginType.STORAGE,
            tags=["storage", "network", "smb", "cifs", "nas"],
            icon="hard-drive",
            requirements=["pysmb"],
            config_schema={
                "type": "object",
                "properties": {
                    "server": {
                        "type": "string",
                        "title": "服务器地址"
                    },
                    "share": {
                        "type": "string",
                        "title": "共享名称"
                    },
                    "username": {
                        "type": "string",
                        "title": "用户名",
                        "default": "guest"
                    },
                    "password": {
                        "type": "string",
                        "title": "密码"
                    },
                    "domain": {
                        "type": "string",
                        "title": "域（可选）"
                    },
                    "remote_path": {
                        "type": "string",
                        "title": "远程路径",
                        "default": "/"
                    },
                    "thumbnail_cache": {
                        "type": "string",
                        "title": "缩略图缓存路径",
                        "default": "data/thumbnails"
                    }
                },
                "required": ["server", "share"]
            }
        )
    
    def __init__(self, manifest: PluginManifest, config: Dict):
        super().__init__(manifest, config)
        self.server = config.get("server")
        self.share = config.get("share")
        self.username = config.get("username", "guest")
        self.password = config.get("password", "")
        self.domain = config.get("domain", "")
        self.remote_path = config.get("remote_path", "/")
        self.thumbnail_cache = config.get("thumbnail_cache", "data/thumbnails")
        self._connection = None
    
    # ========== StoragePlugin 基础方法 ==========
    
    def initialize(self) -> bool:
        """初始化"""
        if not SMB_AVAILABLE:
            logger.warning("pysmb library not available, using fallback mode")
        
        # 创建缩略图缓存目录
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
        """连接 SMB 共享"""
        try:
            if SMB_AVAILABLE:
                # 使用 pysmb 库连接
                self._connection = SMBConnection(
                    self.username,
                    self.password,
                    "ai-nas-client",
                    self.server,
                    domain=self.domain,
                    use_ntlm_v2=True
                )
                self._connection.connect(self.server, 445)
                logger.info(f"Connected to SMB share: //{self.server}/{self.share}")
            else:
                # 使用 UNC 路径模式
                self._connection = f"\\\\{self.server}\\{self.share}"
                logger.info(f"Using UNC path mode: {self._connection}")
            
            return True
        except Exception as e:
            logger.error(f"Failed to connect SMB: {e}")
            return False
    
    def disconnect(self) -> bool:
        """断开连接"""
        try:
            if self._connection and SMB_AVAILABLE:
                self._connection.close()
            self._connection = None
            return True
        except Exception as e:
            logger.error(f"Failed to disconnect: {e}")
            return False
    
    def list_files(self, path: str = "/") -> List[Dict]:
        """列出文件"""
        if not self._connection:
            if not self.connect():
                return []
        
        try:
            if SMB_AVAILABLE:
                # 使用 pysmb 列出文件
                full_path = self.remote_path.rstrip("/") + "/" + path.lstrip("/")
                files = self._connection.listPath(
                    self.share,
                    full_path.rstrip("/") + "/*"
                )
                
                result = []
                for f in files:
                    if f.filename in [".", ".."]:
                        continue
                    
                    result.append({
                        "name": f.filename,
                        "path": path.rstrip("/") + "/" + f.filename,
                        "type": "directory" if f.isDirectory else "file",
                        "size": f.file_size,
                        "modified": datetime.fromtimestamp(f.last_write_time).isoformat()
                    })
                
                return result
            else:
                # UNC 路径模式 - 尝试使用本地文件系统
                unc_path = f"\\\\{self.server}\\{self.share}" + path.replace("/", "\\")
                try:
                    items = os.listdir(unc_path)
                    result = []
                    for item in items:
                        item_path = os.path.join(unc_path, item)
                        stat = os.stat(item_path)
                        result.append({
                            "name": item,
                            "path": path.rstrip("/") + "/" + item,
                            "type": "directory" if os.path.isdir(item_path) else "file",
                            "size": stat.st_size,
                            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                        })
                    return result
                except Exception as e:
                    logger.error(f"Failed to list UNC path: {e}")
                    return []
                    
        except Exception as e:
            logger.error(f"Failed to list files: {e}")
            return []
    
    def upload_file(self, local_path: str, remote_path: str) -> bool:
        """上传文件"""
        if not self._connection:
            if not self.connect():
                return False
        
        try:
            if SMB_AVAILABLE:
                full_remote = self.remote_path.rstrip("/") + "/" + remote_path.lstrip("/")
                
                with open(local_path, "rb") as f:
                    self._connection.storeFile(
                        self.share,
                        full_remote,
                        f
                    )
                
                logger.info(f"Uploaded to {remote_path}")
                return True
            else:
                # UNC 路径模式
                unc_path = f"\\\\{self.server}\\{self.share}" + remote_path.replace("/", "\\")
                Path(unc_path).parent.mkdir(parents=True, exist_ok=True)
                
                import shutil
                shutil.copy2(local_path, unc_path)
                
                logger.info(f"Uploaded to {remote_path}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to upload: {e}")
            return False
    
    def download_file(self, remote_path: str, local_path: str) -> bool:
        """下载文件"""
        if not self._connection:
            if not self.connect():
                return False
        
        try:
            if SMB_AVAILABLE:
                full_remote = self.remote_path.rstrip("/") + "/" + remote_path.lstrip("/")
                
                Path(local_path).parent.mkdir(parents=True, exist_ok=True)
                
                with open(local_path, "wb") as f:
                    self._connection.retrieveFile(
                        self.share,
                        full_remote,
                        f
                    )
                
                logger.info(f"Downloaded from {remote_path}")
                return True
            else:
                # UNC 路径模式
                unc_path = f"\\\\{self.server}\\{self.share}" + remote_path.replace("/", "\\")
                Path(local_path).parent.mkdir(parents=True, exist_ok=True)
                
                import shutil
                shutil.copy2(unc_path, local_path)
                
                logger.info(f"Downloaded from {remote_path}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to download: {e}")
            return False
    
    def delete_file(self, remote_path: str) -> bool:
        """删除文件"""
        if not self._connection:
            if not self.connect():
                return False
        
        try:
            if SMB_AVAILABLE:
                full_remote = self.remote_path.rstrip("/") + "/" + remote_path.lstrip("/")
                self._connection.deleteFiles(self.share, full_remote)
                logger.info(f"Deleted {remote_path}")
                return True
            else:
                # UNC 路径模式
                unc_path = f"\\\\{self.server}\\{self.share}" + remote_path.replace("/", "\\")
                if os.path.isdir(unc_path):
                    import shutil
                    shutil.rmtree(unc_path)
                else:
                    os.unlink(unc_path)
                
                logger.info(f"Deleted {remote_path}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to delete: {e}")
            return False
    
    # ========== FileStorage 扩展方法 ==========
    
    def resolve_path(self, filepath: str) -> str:
        """解析远程文件路径"""
        return self.remote_path.rstrip("/") + "/" + filepath.lstrip("/")
    
    def get_exif(self, filepath: str) -> Dict:
        """读取文件 EXIF 信息"""
        try:
            from PIL import Image
            
            if not self._connection:
                if not self.connect():
                    return {}
            
            if SMB_AVAILABLE:
                full_path = self.resolve_path(filepath)
                
                # 读取文件到内存
                with io.BytesIO() as buf:
                    self._connection.retrieveFile(self.share, full_path, buf)
                    buf.seek(0)
                    
                    with Image.open(buf) as img:
                        exif_data = {
                            "width": img.width,
                            "height": img.height,
                            "format": img.format
                        }
                        
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
                        
                        return exif_data
            else:
                # UNC 路径模式
                unc_path = f"\\\\{self.server}\\{self.share}" + filepath.replace("/", "\\")
                
                with Image.open(unc_path) as img:
                    exif_data = {
                        "width": img.width,
                        "height": img.height,
                        "format": img.format
                    }
                    return exif_data
                    
        except Exception as e:
            logger.warning(f"Failed to read EXIF from {filepath}: {e}")
            return {}
    
    def create_symlink(self, target_path: str, link_path: str) -> bool:
        """
        创建软链接
        
        SMB 存储的软链接支持取决于服务器配置，默认不支持
        """
        logger.warning("SMB storage does not support symlinks")
        return False
    
    def move_file(self, src_path: str, dst_path: str) -> bool:
        """移动文件"""
        if not self._connection:
            if not self.connect():
                return False
        
        try:
            if SMB_AVAILABLE:
                src_full = self.resolve_path(src_path)
                dst_full = self.resolve_path(dst_path)
                
                self._connection.rename(self.share, src_full, dst_full)
                
                logger.info(f"Moved file: {src_path} → {dst_path}")
                return True
            else:
                # UNC 路径模式 - 使用本地移动
                src_unc = f"\\\\{self.server}\\{self.share}" + src_path.replace("/", "\\")
                dst_unc = f"\\\\{self.server}\\{self.share}" + dst_path.replace("/", "\\")
                
                import shutil
                shutil.move(src_unc, dst_unc)
                
                logger.info(f"Moved file: {src_path} → {dst_path}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to move file: {e}")
            return False
    
    def is_support_symlink(self) -> bool:
        """SMB 默认不支持软链接"""
        return False
    
    def get_thumbnail(self, filepath: str, size: Tuple[int, int] = (200, 200)) -> bytes:
        """生成缩略图"""
        try:
            from PIL import Image
            
            # 检查缓存
            cache_key = f"smb_{self.server}_{filepath}_{size[0]}x{size[1]}"
            cache_path = Path(self.thumbnail_cache) / f"{hash(cache_key)}.jpg"
            
            if cache_path.exists():
                return cache_path.read_bytes()
            
            # 获取文件内容
            if SMB_AVAILABLE:
                if not self._connection:
                    if not self.connect():
                        return b""
                
                full_path = self.resolve_path(filepath)
                
                with io.BytesIO() as buf:
                    self._connection.retrieveFile(self.share, full_path, buf)
                    buf.seek(0)
                    
                    with Image.open(buf) as img:
                        if img.mode in ("RGBA", "P"):
                            img = img.convert("RGB")
                        
                        img.thumbnail(size, Image.Resampling.LANCZOS)
                        
                        out_buf = io.BytesIO()
                        img.save(out_buf, format="JPEG", quality=85)
                        thumbnail_data = out_buf.getvalue()
                        
                        cache_path.parent.mkdir(parents=True, exist_ok=True)
                        cache_path.write_bytes(thumbnail_data)
                        
                        return thumbnail_data
            
            return b""
            
        except Exception as e:
            logger.error(f"Failed to generate thumbnail for {filepath}: {e}")
            return b""
    
    def get_file_info(self, filepath: str) -> Dict:
        """获取文件详细信息"""
        if not self._connection:
            if not self.connect():
                return {}
        
        try:
            if SMB_AVAILABLE:
                full_path = self.resolve_path(filepath)
                
                files = self._connection.listPath(self.share, full_path)
                if not files:
                    return {}
                
                f = files[0]
                mime_type, _ = mimetypes.guess_type(filepath)
                
                return {
                    "name": f.filename,
                    "path": full_path,
                    "relative_path": filepath,
                    "size": f.file_size,
                    "modified": datetime.fromtimestamp(f.last_write_time).isoformat(),
                    "type": "directory" if f.isDirectory else "file",
                    "mime": mime_type or "application/octet-stream",
                    "is_dir": f.isDirectory
                }
            else:
                unc_path = f"\\\\{self.server}\\{self.share}" + filepath.replace("/", "\\")
                stat = os.stat(unc_path)
                mime_type, _ = mimetypes.guess_type(filepath)
                
                return {
                    "name": os.path.basename(unc_path),
                    "path": unc_path,
                    "relative_path": filepath,
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "type": "directory" if os.path.isdir(unc_path) else "file",
                    "mime": mime_type or "application/octet-stream",
                    "is_dir": os.path.isdir(unc_path)
                }
                
        except Exception as e:
            logger.error(f"Failed to get file info for {filepath}: {e}")
            return {}


# NAS Storage Plugin（继承 SMBStoragePlugin）
class NASStoragePlugin(SMBStoragePlugin):
    """
    通用 NAS 存储插件
    
    支持 Synology、QNAP 等品牌的 NAS 设备
    底层使用 SMB/CIFS 协议
    """
    
    @staticmethod
    def get_manifest() -> PluginManifest:
        return PluginManifest(
            id="nas-storage",
            name="通用 NAS 存储",
            version="2.0.0",
            description="支持 Synology、QNAP、群晖等 NAS 设备（SMB 协议）",
            author="AI-NAS Team",
            plugin_type=PluginType.STORAGE,
            tags=["storage", "nas", "synology", "qnap", "smb"],
            icon="server",
            requirements=["pysmb"],
            config_schema={
                "type": "object",
                "properties": {
                    "nas_type": {
                        "type": "string",
                        "title": "NAS 类型",
                        "enum": ["synology", "qnap", "generic"],
                        "default": "generic"
                    },
                    "host": {
                        "type": "string",
                        "title": "NAS 地址"
                    },
                    "share": {
                        "type": "string",
                        "title": "共享文件夹",
                        "default": "media"
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
                    "api_key": {
                        "type": "string",
                        "title": "API 密钥（可选）"
                    }
                },
                "required": ["host", "username", "password", "share"]
            }
        )
    
    def __init__(self, manifest: PluginManifest, config: Dict):
        # 复用 SMB 配置
        smb_config = {
            "server": config.get("host"),
            "share": config.get("share", "media"),
            "username": config.get("username"),
            "password": config.get("password"),
            "domain": "",
            "remote_path": config.get("remote_path", "/"),
            "thumbnail_cache": config.get("thumbnail_cache", "data/thumbnails")
        }
        
        # 使用 SMB manifest
        smb_manifest = SMBStoragePlugin.get_manifest()
        smb_manifest.id = manifest.id
        smb_manifest.name = manifest.name
        smb_manifest.version = manifest.version
        
        super().__init__(smb_manifest, smb_config)
        
        self.nas_type = config.get("nas_type", "generic")
        self.api_key = config.get("api_key")
    
    def connect(self) -> bool:
        """连接 NAS（支持特定品牌优化）"""
        if self.nas_type == "synology":
            logger.info(f"Connecting to Synology NAS at {self.server}")
            # Synology 特定优化（如 DSM API）
        
        elif self.nas_type == "qnap":
            logger.info(f"Connecting to QNAP NAS at {self.server}")
            # QNAP 特定优化
        
        # 使用父类 SMB 连接
        return super().connect()


# 兼容性别名
SMBStorage = SMBStoragePlugin
NASStorage = NASStoragePlugin