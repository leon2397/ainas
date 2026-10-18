"""
缩略图缓存模块
避免重复生成缩略图，提升加载速度
"""

import os
import hashlib
from pathlib import Path
from typing import Optional, Tuple
from PIL import Image
import asyncio

# 缓存配置
CACHE_DIR = "./data/thumbnails"
CACHE_SIZE = (300, 300)  # 默认缩略图大小
MAX_CACHE_SIZE = 10000  # 最大缓存文件数


class ThumbnailCache:
    """缩略图缓存管理器"""
    
    def __init__(self, cache_dir: str = CACHE_DIR):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._cache_lock = asyncio.Lock()
    
    def _get_cache_key(self, file_path: str, size: Tuple[int, int] = CACHE_SIZE) -> str:
        """生成缓存键"""
        content = f"{file_path}:{size[0]}x{size[1]}"
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def _get_cache_path(self, file_path: str, size: Tuple[int, int] = CACHE_SIZE) -> Path:
        """获取缩略图缓存路径"""
        cache_key = self._get_cache_key(file_path, size)
        return self.cache_dir / f"{cache_key}.jpg"
    
    def exists(self, file_path: str, size: Tuple[int, int] = CACHE_SIZE) -> bool:
        """检查缓存是否存在"""
        return self._get_cache_path(file_path, size).exists()
    
    def get(self, file_path: str, size: Tuple[int, int] = CACHE_SIZE) -> Optional[Path]:
        """获取缩略图路径（如果存在）"""
        cache_path = self._get_cache_path(file_path, size)
        if cache_path.exists():
            # 更新访问时间（os.utime 同时支持 Windows/POSIX；Path 无 utime 方法）
            os.utime(cache_path, None)
            return cache_path
        return None
    
    async def generate(self, file_path: str, size: Tuple[int, int] = CACHE_SIZE) -> Optional[Path]:
        """生成缩略图（带缓存）"""
        cache_path = self._get_cache_path(file_path, size)
        
        # 检查缓存
        if cache_path.exists():
            return cache_path
        
        # 生成新缩略图
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._generate_sync,
                file_path,
                cache_path,
                size
            )
            return result
        except Exception as e:
            logger.info(f"[WARN] Thumbnail generation failed: {e}")
            return None
    
    def _generate_sync(self, file_path: str, cache_path: Path, size: Tuple[int, int]) -> Optional[Path]:
        """同步生成缩略图"""
        try:
            with Image.open(file_path) as img:
                # 转换为RGB（去除透明通道）
                if img.mode in ('RGBA', 'P', 'LA'):
                    img = img.convert('RGB')
                
                # EXIF方向纠正
                try:
                    img = ImageOps.exif_transpose(img)
                except Exception:  # EXIF 解析失败时忽略
                    pass
                
                # 生成缩略图
                img.thumbnail(size, Image.Resampling.LANCZOS)
                
                # 保存到缓存
                img.save(cache_path, "JPEG", quality=85, optimize=True)
                
                return cache_path
        except Exception as e:
            logger.info(f"[WARN] Failed to generate thumbnail for {file_path}: {e}")
            return None
    
    def clear(self, max_age_days: int = 30) -> int:
        """清理旧缓存"""
        import time
        cleared = 0
        max_age = max_age_days * 24 * 3600
        now = time.time()
        
        for cache_file in self.cache_dir.glob("*.jpg"):
            try:
                # 检查文件年龄
                file_age = now - os.path.getmtime(cache_file)
                if file_age > max_age:
                    cache_file.unlink()
                    cleared += 1
            except Exception as e:
                logger.info(f"[WARN] Failed to clear cache {cache_file}: {e}")
        
        return cleared
    
    def get_cache_size(self) -> int:
        """获取缓存大小（MB）"""
        total = 0
        for cache_file in self.cache_dir.glob("*.jpg"):
            try:
                total += cache_file.stat().st_size
            except OSError:  # 文件被删除或无法访问时忽略
                pass
        return total / (1024 * 1024)
    
    def get_cache_count(self) -> int:
        """获取缓存文件数"""
        return len(list(self.cache_dir.glob("*.jpg")))


# 导入修复
from loguru import logger
try:
    from PIL import ImageOps
except ImportError:
    ImageOps = None

# 全局缓存实例
thumbnail_cache = ThumbnailCache()
