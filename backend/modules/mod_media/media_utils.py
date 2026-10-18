"""
Media Format Utilities
Handles HEIC, RAW formats and EXIF orientation
"""

import io
import numpy as np
from typing import Optional, Tuple, Dict
from PIL import Image, ImageOps


class MediaFormatHandler:
    """
    Handles special media formats:
    - HEIC/HEIF
    - RAW formats (CR2, NEF, ARW, DNG)
    - EXIF orientation correction
    """
    
    def __init__(self):
        self._heif_available = False
        self._rawpy_available = False
        self._check_dependencies()
    
    def _check_dependencies(self):
        """Check available format libraries"""
        try:
            import pyheif
            self._heif_available = True
        except ImportError:
            pass
        
        try:
            import rawpy
            self._rawpy_available = True
        except ImportError:
            pass
    
    def open_image(self, filepath: str) -> Optional[Image.Image]:
        """
        Open image with automatic format detection
        
        Supports:
        - Standard formats (JPEG, PNG, WebP, etc.)
        - HEIC/HEIF (if pyheif installed)
        - RAW formats (if rawpy installed)
        """
        ext = filepath.lower().split('.')[-1]
        
        # HEIC formats
        if ext in ('heic', 'heif'):
            return self._open_heif(filepath)
        
        # RAW formats
        if ext in ('cr2', 'nef', 'arw', 'dng', 'raw', 'orf', 'rw2'):
            return self._open_raw(filepath)
        
        # Standard formats
        try:
            img = Image.open(filepath)
            return self._fix_exif_orientation(img)
        except Exception as e:
            logger.info(f"Open image error: {e}")
            return None
    
    def _open_heif(self, filepath: str) -> Optional[Image.Image]:
        """Open HEIC/HEIF image"""
        if not self._heif_available:
            try:
                import pyheif
                self._heif_available = True
            except ImportError:
                logger.info("pyheif not installed, cannot open HEIC files")
                return None
        
        try:
            import pyheif
            heif_file = pyheif.read(filepath)
            image = Image.frombytes(
                heif_file.mode,
                heif_file.size,
                heif_file.data,
                "raw",
                heif_file.mode,
                heif_file.stride,
                heif_file.planar_config
            )
            # Fix orientation
            if heif_file.has_exif:
                image = self._apply_exif_orientation(image, heif_file.exif)
            return image
        except Exception as e:
            logger.info(f"Open HEIC error: {e}")
            return None
    
    def _open_raw(self, filepath: str) -> Optional[Image.Image]:
        """
        Open RAW format image
        
        Uses embedded JPEG preview for speed,
        or demosaic full RAW if needed.
        """
        if not self._rawpy_available:
            # Try to use embedded preview
            try:
                img = Image.open(filepath)
                return self._fix_exif_orientation(img)
            except (IOError, OSError, ValueError):  # 文件损坏或格式不支持
                logger.info("rawpy not installed, cannot open RAW files")
                return None
        
        try:
            import rawpy
            raw = rawpy.imread(filepath)
            
            # Use postprocessed image (faster, good quality)
            rgb = raw.postprocess(
                output_color=rawpy.ColorSpace.sRGB,
                output_bps=8,
                demosaic_algorithm=rawpy.DemosaicAlgorithm.LINEAR
            )
            
            img = Image.fromarray(rgb)
            return self._fix_exif_orientation(img)
        
        except Exception as e:
            logger.info(f"Open RAW error: {e}")
            return None
    
    def _fix_exif_orientation(self, img: Image.Image) -> Image.Image:
        """Fix image orientation based on EXIF data"""
        try:
            return ImageOps.exif_transpose(img)
        except Exception:
            return img
    
    def _apply_exif_orientation(self, img: Image.Image, exif: bytes) -> Image.Image:
        """Apply orientation from EXIF data"""
        try:
            from PIL import ImageOps
            img = ImageOps.exif_transpose(img)
        except Exception:
            pass
        return img
    
    def get_thumbnail(
        self,
        filepath: str,
        size: Tuple[int, int] = (200, 200),
        quality: int = 85
    ) -> Optional[bytes]:
        """
        Generate thumbnail from any supported format
        
        Args:
            filepath: Image file path
            size: Thumbnail size (width, height)
            quality: JPEG quality
        
        Returns:
            JPEG thumbnail bytes or None
        """
        img = self.open_image(filepath)
        if not img:
            return None
        
        try:
            # Resize with high quality
            img.thumbnail(size, Image.Resampling.LANCZOS)
            
            # Convert to RGB
            if img.mode in ('RGBA', 'P', 'LA'):
                img = img.convert('RGB')
            
            # Save to bytes
            buffer = io.BytesIO()
            img.save(buffer, format='JPEG', quality=quality)
            return buffer.getvalue()
        
        except Exception as e:
            logger.info(f"Thumbnail error: {e}")
            return None
    
    def get_image_info(self, filepath: str) -> Dict:
        """
        Get image information
        
        Returns:
            Dict with width, height, format, mode, etc.
        """
        info = {
            'format': None,
            'width': 0,
            'height': 0,
            'mode': None,
            'file_size': 0,
            'exif': {}
        }
        
        try:
            img = self.open_image(filepath)
            if img:
                info['format'] = img.format
                info['width'] = img.width
                info['height'] = img.height
                info['mode'] = img.mode
                
                # Get EXIF
                from loguru import logger
                if hasattr(img, '_getexif') and img._getexif():
                    from PIL.ExifTags import TAGS
                    for tag_id, value in img._getexif().items():
                        tag = TAGS.get(tag_id, tag_id)
                        info['exif'][tag] = str(value)
        
        except Exception as e:
            info['error'] = str(e)
        
        return info
    
    def convert_to_jpeg(
        self,
        filepath: str,
        output_path: str = None,
        quality: int = 95
    ) -> Optional[str]:
        """
        Convert image to JPEG format
        
        Args:
            filepath: Source image path
            output_path: Output path (optional, auto-generate if None)
            quality: JPEG quality
        
        Returns:
            Output file path or None
        """
        img = self.open_image(filepath)
        if not img:
            return None
        
        try:
            # Generate output path
            if not output_path:
                output_path = filepath.rsplit('.', 1)[0] + '.jpg'
            
            # Convert and save
            if img.mode in ('RGBA', 'P', 'LA'):
                img = img.convert('RGB')
            
            img.save(output_path, format='JPEG', quality=quality)
            return output_path
        
        except Exception as e:
            logger.info(f"Convert to JPEG error: {e}")
            return None


# Global handler instance
_media_handler: Optional[MediaFormatHandler] = None


def get_media_handler() -> MediaFormatHandler:
    """Get or create media format handler"""
    global _media_handler
    if _media_handler is None:
        _media_handler = MediaFormatHandler()
    return _media_handler
