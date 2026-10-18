"""
mod_media — AI-NAS 媒体管理模块

提供：
- 媒体文件扫描器（目录扫描 + EXIF + GPS）
- 媒体格式处理器（缩略图、格式转换）

使用方式：
    from modules.mod_media import MediaScanner, MediaFormatHandler
"""

from modules.mod_media.scanner import MediaScanner
from modules.mod_media.media_utils import MediaFormatHandler, get_media_handler

__all__ = [
    "MediaScanner",
    "MediaFormatHandler",
    "get_media_handler",
]
