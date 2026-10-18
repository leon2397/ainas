"""
内存优化模块
限制大文件处理时的内存使用
"""

import os
import psutil
from typing import Optional
from PIL import Image
from loguru import logger


# 内存限制配置
MAX_MEMORY_PERCENT = 70  # 最大使用70%内存
MAX_IMAGE_SIZE = (4096, 4096)  # 最大图片尺寸
CHUNK_SIZE = 1024 * 1024  # 1MB 分块大小


class MemoryGuard:
    """内存保护器"""
    
    def __init__(self, max_percent: float = MAX_MEMORY_PERCENT):
        self.max_percent = max_percent
        self.process = psutil.Process()
    
    def check_memory(self) -> bool:
        """检查内存使用是否在限制内"""
        memory = psutil.virtual_memory()
        return memory.percent < self.max_percent
    
    def get_memory_info(self) -> dict:
        """获取内存信息"""
        memory = psutil.virtual_memory()
        process_memory = self.process.memory_info()
        
        return {
            "system_percent": memory.percent,
            "system_available": memory.available / (1024**3),  # GB
            "system_total": memory.total / (1024**3),  # GB
            "process_rss": process_memory.rss / (1024**2),  # MB
            "process_vms": process_memory.vms / (1024**2),  # MB
        }
    
    def wait_if_needed(self, timeout: int = 30) -> bool:
        """如果内存不足，等待释放"""
        import time
        start = time.time()
        
        while self.check_memory():
            if time.time() - start > timeout:
                return False
            time.sleep(1)
        
        return True


def safe_load_image(file_path: str, max_size: tuple = MAX_IMAGE_SIZE) -> Optional[Image.Image]:
    """
    安全加载图片（限制内存使用）
    
    Args:
        file_path: 图片路径
        max_size: 最大尺寸
    
    Returns:
        PIL Image 对象或 None
    """
    try:
        # 检查文件大小
        file_size = os.path.getsize(file_path)
        
        # 大文件（>50MB）直接返回None
        if file_size > 50 * 1024 * 1024:
            logger.info(f"[WARN] File too large: {file_path} ({file_size / (1024**2):.1f}MB)")
            return None
        
        # 打开图片
        with Image.open(file_path) as img:
            # 检查尺寸
            if img.size[0] > max_size[0] or img.size[1] > max_size[1]:
                img.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # 转换模式
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')
            
            # EXIF方向纠正
            try:
                img = _exif_transpose(img)
            except Exception:  # EXIF 解析失败时忽略，使用原图
                pass
            
            return img.copy()
    
    except Exception as e:
        logger.info(f"[WARN] Failed to load image {file_path}: {e}")
        return None


def _exif_transpose(img: Image.Image) -> Image.Image:
    """EXIF方向纠正"""
    from loguru import logger
    try:
        from PIL import ImageOps
        return ImageOps.exif_transpose(img)
    except ImportError:
        return img


def get_optimal_batch_size() -> int:
    """根据可用内存计算最佳批量大小"""
    memory = psutil.virtual_memory()
    available_mb = memory.available / (1024**2)
    
    # 每张图片预估50MB内存
    # 使用可用内存的50%
    optimal = int(available_mb * 0.5 / 50)
    
    # 限制范围
    return max(1, min(optimal, 20))


# 全局内存保护器
memory_guard = MemoryGuard()
