from loguru import logger
"""
云存储插件
支持阿里云 OSS 和腾讯云 COS
SDK 为可选依赖，缺少时降级提示
"""

import os
import hashlib
from typing import List, Optional, Dict, Any
from pathlib import Path

from core.storage import FileStorage


class CloudStorage(FileStorage):
    """云存储基类，统一 OSS/COS 接口"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.provider = config.get("provider", "aliyun")  # aliyun / tencent
        self.bucket = config.get("bucket", "")
        self.prefix = config.get("prefix", "ai-nas/")
        self.client = None
        self._init_client()

    def _init_client(self):
        """初始化云 SDK 客户端（可选依赖）"""
        try:
            if self.provider == "aliyun":
                import oss2
                auth = oss2.Auth(self.config.get("access_key", ""), self.config.get("secret_key", ""))
                endpoint = self.config.get("endpoint", "https://oss-cn-hangzhou.aliyuncs.com")
                self.client = oss2.Bucket(auth, endpoint, self.bucket)
            elif self.provider == "tencent":
                from qcloud_cos import CosConfig, CosS3Client
                cfg = CosConfig(Region=self.config.get("region", "ap-guangzhou"),
                                SecretId=self.config.get("access_key", ""),
                                SecretKey=self.config.get("secret_key", ""))
                self.client = CosS3Client(cfg)
        except ImportError:
            self.client = None

    def is_available(self) -> bool:
        """检查 SDK 是否可用"""
        return self.client is not None

    def upload_file(self, local_path: str, remote_path: str = None) -> bool:
        """上传文件到云端"""
        if not self.is_available():
            return False
        key = self.prefix + (remote_path or Path(local_path).name)
        try:
            if self.provider == "aliyun":
                self.client.put_object_from_file(key, local_path)
            elif self.provider == "tencent":
                self.client.upload_file(
                    Bucket=self.bucket,
                    Key=key,
                    LocalFilePath=local_path
                )
            return True
        except Exception as e:
            logger.info(f"[CloudStorage] Upload failed: {e}")
            return False

    def download_file(self, remote_path: str, local_path: str) -> bool:
        """从云端下载文件"""
        if not self.is_available():
            return False
        key = self.prefix + remote_path
        try:
            if self.provider == "aliyun":
                self.client.get_object_to_file(key, local_path)
            elif self.provider == "tencent":
                response = self.client.get_object(Bucket=self.bucket, Key=key)
                with open(local_path, 'wb') as f:
                    for chunk in response['Body'].iter_chunks():
                        f.write(chunk)
            return True
        except Exception as e:
            logger.info(f"[CloudStorage] Download failed: {e}")
            return False

    def delete_file(self, remote_path: str) -> bool:
        """删除云端文件"""
        if not self.is_available():
            return False
        key = self.prefix + remote_path
        try:
            if self.provider == "aliyun":
                self.client.delete_object(key)
            elif self.provider == "tencent":
                self.client.delete_object(Bucket=self.bucket, Key=key)
            return True
        except Exception as e:
            logger.info(f"[CloudStorage] Delete failed: {e}")
            return False

    def list_files(self, prefix: str = "") -> List[Dict[str, Any]]:
        """列出云端文件"""
        if not self.is_available():
            return []
        try:
            files = []
            if self.provider == "aliyun":
                for obj in oss2.ObjectIterator(self.client, prefix=self.prefix + prefix):
                    files.append({"name": obj.key.replace(self.prefix, ""), "size": obj.size, "last_modified": str(obj.last_modified)})
            elif self.provider == "tencent":
                resp = self.client.list_objects(Bucket=self.bucket, Prefix=self.prefix + prefix)
                if 'Contents' in resp:
                    for obj in resp['Contents']:
                        files.append({"name": obj['Key'].replace(self.prefix, ""), "size": obj['Size'], "last_modified": obj['LastModified']})
            return files
        except Exception as e:
            logger.info(f"[CloudStorage] List failed: {e}")
            return []

    def file_exists(self, remote_path: str) -> bool:
        """检查文件是否存在"""
        key = self.prefix + remote_path
        try:
            if self.provider == "aliyun":
                return self.client.object_exists(key)
            elif self.provider == "tencent":
                self.client.head_object(Bucket=self.bucket, Key=key)
                return True
        except Exception:
            return False
        return False