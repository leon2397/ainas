"""
媒体编辑服务
支持旋转、裁剪、调整等基础图片编辑
"""

from PIL import Image, ImageOps
import os
import io
import tempfile
from typing import Optional, Tuple
from datetime import datetime
import shutil


class MediaEditor:
    """媒体编辑器"""
    
    SUPPORTED_FORMATS = {
        'image': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff'],
        'video': ['.mp4', '.mov', '.avi', '.mkv']
    }
    
    def __init__(self, storage_path: str = "./data/media_edits"):
        self.storage_path = storage_path
        os.makedirs(storage_path, exist_ok=True)
    
    def _is_supported_image(self, file_path: str) -> bool:
        """检查是否为支持的图片格式"""
        ext = os.path.splitext(file_path)[1].lower()
        return ext in self.SUPPORTED_FORMATS['image']
    
    def _is_supported_video(self, file_path: str) -> bool:
        """检查是否为支持的视频格式"""
        ext = os.path.splitext(file_path)[1].lower()
        return ext in self.SUPPORTED_FORMATS['video']
    
    def rotate(
        self,
        file_path: str,
        angle: float,
        expand: bool = True,
        save_original: bool = True
    ) -> dict:
        """
        旋转图片
        
        Args:
            file_path: 源文件路径
            angle: 旋转角度（顺时针）
            expand: 是否扩展画布以容纳旋转后的图片
            save_original: 是否保存原始文件备份
            
        Returns:
            编辑结果信息
        """
        if not self._is_supported_image(file_path):
            raise ValueError(f"不支持的图片格式: {file_path}")
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        # 保存原始文件备份
        backup_path = None
        if save_original:
            backup_dir = os.path.join(self.storage_path, "backups")
            os.makedirs(backup_dir, exist_ok=True)
            backup_name = f"{os.path.basename(file_path)}.bak.{datetime.now().strftime('%Y%m%d%H%M%S')}"
            backup_path = os.path.join(backup_dir, backup_name)
            shutil.copy2(file_path, backup_path)
        
        # 打开并旋转图片
        with Image.open(file_path) as img:
            # 处理EXIF方向
            img = ImageOps.exif_transpose(img)
            
            # 旋转
            rotated = img.rotate(-angle, expand=expand, resample=Image.Resampling.BICUBIC)
            
            # 保存（保持原格式）
            ext = os.path.splitext(file_path)[1].lower()
            format_map = {
                '.jpg': 'JPEG',
                '.jpeg': 'JPEG',
                '.png': 'PNG',
                '.gif': 'GIF',
                '.bmp': 'BMP',
                '.webp': 'WEBP',
                '.tiff': 'TIFF'
            }
            
            save_format = format_map.get(ext, 'JPEG')
            
            # RGBA -> RGB for JPEG
            if save_format == 'JPEG' and rotated.mode in ('RGBA', 'P'):
                rotated = rotated.convert('RGB')
            
            rotated.save(file_path, format=save_format, quality=95)
            
            return {
                "status": "success",
                "file_path": file_path,
                "angle": angle,
                "backup_path": backup_path,
                "new_size": rotated.size,
                "message": f"图片已旋转 {angle}°"
            }
    
    def crop(
        self,
        file_path: str,
        x: int,
        y: int,
        width: int,
        height: int,
        save_original: bool = True
    ) -> dict:
        """
        裁剪图片
        
        Args:
            file_path: 源文件路径
            x, y: 裁剪区域左上角坐标
            width, height: 裁剪区域宽高
            save_original: 是否保存原始文件备份
            
        Returns:
            编辑结果信息
        """
        if not self._is_supported_image(file_path):
            raise ValueError(f"不支持的图片格式: {file_path}")
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        # 保存原始文件备份
        backup_path = None
        if save_original:
            backup_dir = os.path.join(self.storage_path, "backups")
            os.makedirs(backup_dir, exist_ok=True)
            backup_name = f"{os.path.basename(file_path)}.bak.{datetime.now().strftime('%Y%m%d%H%M%S')}"
            backup_path = os.path.join(backup_dir, backup_name)
            shutil.copy2(file_path, backup_path)
        
        with Image.open(file_path) as img:
            # 处理EXIF方向
            img = ImageOps.exif_transpose(img)
            
            original_size = img.size
            
            # 边界检查
            x = max(0, x)
            y = max(0, y)
            width = min(width, original_size[0] - x)
            height = min(height, original_size[1] - y)
            
            # 裁剪 (left, upper, right, lower)
            box = (x, y, x + width, y + height)
            cropped = img.crop(box)
            
            # 保存
            ext = os.path.splitext(file_path)[1].lower()
            format_map = {
                '.jpg': 'JPEG',
                '.jpeg': 'JPEG',
                '.png': 'PNG',
                '.gif': 'GIF',
                '.bmp': 'BMP',
                '.webp': 'WEBP',
                '.tiff': 'TIFF'
            }
            
            save_format = format_map.get(ext, 'JPEG')
            
            if save_format == 'JPEG' and cropped.mode in ('RGBA', 'P'):
                cropped = cropped.convert('RGB')
            
            cropped.save(file_path, format=save_format, quality=95)
            
            return {
                "status": "success",
                "file_path": file_path,
                "crop_region": {"x": x, "y": y, "width": width, "height": height},
                "original_size": original_size,
                "new_size": cropped.size,
                "backup_path": backup_path,
                "message": f"图片已裁剪，新尺寸: {cropped.size[0]}x{cropped.size[1]}"
            }
    
    def flip(
        self,
        file_path: str,
        direction: str = "horizontal",
        save_original: bool = True
    ) -> dict:
        """
        翻转图片
        
        Args:
            file_path: 源文件路径
            direction: 翻转方向 horizontal/vertical
            save_original: 是否保存原始文件备份
            
        Returns:
            编辑结果信息
        """
        if not self._is_supported_image(file_path):
            raise ValueError(f"不支持的图片格式: {file_path}")
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        # 保存原始文件备份
        backup_path = None
        if save_original:
            backup_dir = os.path.join(self.storage_path, "backups")
            os.makedirs(backup_dir, exist_ok=True)
            backup_name = f"{os.path.basename(file_path)}.bak.{datetime.now().strftime('%Y%m%d%H%M%S')}"
            backup_path = os.path.join(backup_dir, backup_name)
            shutil.copy2(file_path, backup_path)
        
        with Image.open(file_path) as img:
            img = ImageOps.exif_transpose(img)
            
            if direction == "horizontal":
                flipped = ImageOps.mirror(img)
            else:  # vertical
                flipped = ImageOps.flip(img)
            
            # 保存
            ext = os.path.splitext(file_path)[1].lower()
            format_map = {
                '.jpg': 'JPEG',
                '.jpeg': 'JPEG',
                '.png': 'PNG',
                '.gif': 'GIF',
                '.bmp': 'BMP',
                '.webp': 'WEBP',
                '.tiff': 'TIFF'
            }
            
            save_format = format_map.get(ext, 'JPEG')
            
            if save_format == 'JPEG' and flipped.mode in ('RGBA', 'P'):
                flipped = flipped.convert('RGB')
            
            flipped.save(file_path, format=save_format, quality=95)
            
            return {
                "status": "success",
                "file_path": file_path,
                "direction": direction,
                "backup_path": backup_path,
                "message": f"图片已{'水平' if direction == 'horizontal' else '垂直'}翻转"
            }
    
    def resize(
        self,
        file_path: str,
        width: Optional[int] = None,
        height: Optional[int] = None,
        keep_aspect: bool = True,
        save_original: bool = True
    ) -> dict:
        """
        调整图片尺寸
        
        Args:
            file_path: 源文件路径
            width: 目标宽度
            height: 目标高度
            keep_aspect: 是否保持宽高比
            save_original: 是否保存原始文件备份
            
        Returns:
            编辑结果信息
        """
        if not self._is_supported_image(file_path):
            raise ValueError(f"不支持的图片格式: {file_path}")
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        if width is None and height is None:
            raise ValueError("必须指定 width 或 height")
        
        # 保存原始文件备份
        backup_path = None
        if save_original:
            backup_dir = os.path.join(self.storage_path, "backups")
            os.makedirs(backup_dir, exist_ok=True)
            backup_name = f"{os.path.basename(file_path)}.bak.{datetime.now().strftime('%Y%m%d%H%M%S')}"
            backup_path = os.path.join(backup_dir, backup_name)
            shutil.copy2(file_path, backup_path)
        
        with Image.open(file_path) as img:
            img = ImageOps.exif_transpose(img)
            original_size = img.size
            
            # 计算新尺寸
            if keep_aspect:
                if width and height:
                    # 按比例缩放到能包含在指定范围内
                    ratio = min(width / original_size[0], height / original_size[1])
                    new_width = int(original_size[0] * ratio)
                    new_height = int(original_size[1] * ratio)
                elif width:
                    ratio = width / original_size[0]
                    new_width = width
                    new_height = int(original_size[1] * ratio)
                else:
                    ratio = height / original_size[1]
                    new_width = int(original_size[0] * ratio)
                    new_height = height
            else:
                new_width = width or original_size[0]
                new_height = height or original_size[1]
            
            resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # 保存
            ext = os.path.splitext(file_path)[1].lower()
            format_map = {
                '.jpg': 'JPEG',
                '.jpeg': 'JPEG',
                '.png': 'PNG',
                '.gif': 'GIF',
                '.bmp': 'BMP',
                '.webp': 'WEBP',
                '.tiff': 'TIFF'
            }
            
            save_format = format_map.get(ext, 'JPEG')
            
            if save_format == 'JPEG' and resized.mode in ('RGBA', 'P'):
                resized = resized.convert('RGB')
            
            resized.save(file_path, format=save_format, quality=95)
            
            return {
                "status": "success",
                "file_path": file_path,
                "original_size": original_size,
                "new_size": (new_width, new_height),
                "backup_path": backup_path,
                "message": f"图片尺寸已调整: {original_size[0]}x{original_size[1]} -> {new_width}x{new_height}"
            }
    
    def auto_orient(self, file_path: str, save_original: bool = True) -> dict:
        """
        自动根据EXIF方向调整图片
        
        Args:
            file_path: 源文件路径
            save_original: 是否保存原始文件备份
            
        Returns:
            编辑结果信息
        """
        if not self._is_supported_image(file_path):
            raise ValueError(f"不支持的图片格式: {file_path}")
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        with Image.open(file_path) as img:
            # 检查是否需要旋转
            oriented = ImageOps.exif_transpose(img)
            
            if oriented.size == img.size and oriented.mode == img.mode:
                # 无需调整
                return {
                    "status": "no_change",
                    "file_path": file_path,
                    "message": "图片方向正确，无需调整"
                }
            
            # 保存原始文件备份
            backup_path = None
            if save_original:
                backup_dir = os.path.join(self.storage_path, "backups")
                os.makedirs(backup_dir, exist_ok=True)
                backup_name = f"{os.path.basename(file_path)}.bak.{datetime.now().strftime('%Y%m%d%H%M%S')}"
                backup_path = os.path.join(backup_dir, backup_name)
                shutil.copy2(file_path, backup_path)
            
            # 保存调整后的图片
            ext = os.path.splitext(file_path)[1].lower()
            format_map = {
                '.jpg': 'JPEG',
                '.jpeg': 'JPEG',
                '.png': 'PNG',
                '.gif': 'GIF',
                '.bmp': 'BMP',
                '.webp': 'WEBP',
                '.tiff': 'TIFF'
            }
            
            save_format = format_map.get(ext, 'JPEG')
            
            if save_format == 'JPEG' and oriented.mode in ('RGBA', 'P'):
                oriented = oriented.convert('RGB')
            
            oriented.save(file_path, format=save_format, quality=95)
            
            return {
                "status": "success",
                "file_path": file_path,
                "backup_path": backup_path,
                "message": "图片已根据EXIF方向自动调整"
            }
    
    def restore_backup(self, backup_path: str, original_path: str) -> dict:
        """
        从备份恢复原始文件
        
        Args:
            backup_path: 备份文件路径
            original_path: 原始文件路径
            
        Returns:
            恢复结果
        """
        if not os.path.exists(backup_path):
            raise FileNotFoundError(f"备份文件不存在: {backup_path}")
        
        shutil.copy2(backup_path, original_path)
        
        return {
            "status": "success",
            "original_path": original_path,
            "backup_path": backup_path,
            "message": "已从备份恢复原始文件"
        }


# 单例实例
_media_editor = None

def get_media_editor() -> MediaEditor:
    """获取媒体编辑器单例"""
    global _media_editor
    if _media_editor is None:
        _media_editor = MediaEditor()
    return _media_editor
