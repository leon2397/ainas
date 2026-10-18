"""
Video Processing Service
Extract frames, thumbnails, and metadata from videos
"""

import os
import subprocess
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from PIL import Image
import cv2
import numpy as np


class VideoProcessor:
    """
    Video processing utilities for frame extraction and analysis
    """
    
    def __init__(self, ffmpeg_path: str = "ffmpeg"):
        self.ffmpeg_path = ffmpeg_path
    
    def get_video_info(self, filepath: str) -> Dict:
        """Get video metadata using ffprobe"""
        try:
            cmd = [
                self.ffmpeg_path, "-i", filepath,
                "-hide_banner"
            ]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Parse output for duration, resolution, etc.
            output = result.stderr
            
            info = {
                'duration': 0,
                'width': 0,
                'height': 0,
                'fps': 0,
                'codec': '',
                'bitrate': 0,
                'size_bytes': 0
            }
            
            # Parse duration
            if 'Duration:' in output:
                import re
                dur_match = re.search(r'Duration: (\d+):(\d+):(\d+)\.(\d+)', output)
                if dur_match:
                    h, m, s, ms = dur_match.groups()
                    info['duration'] = int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 100
            
            # Parse video stream info
            stream_match = re.search(
                r'Stream.*Video.* (\d+)x(\d+).* (\d+) fps',
                output
            )
            if stream_match:
                info['width'] = int(stream_match.group(1))
                info['height'] = int(stream_match.group(2))
                info['fps'] = int(stream_match.group(3))
            
            # Get file size
            if os.path.exists(filepath):
                info['size_bytes'] = os.path.getsize(filepath)
            
            return info
        
        except Exception as e:
            return {'error': str(e)}
    
    def extract_frames(
        self,
        filepath: str,
        output_dir: str,
        count: int = 5,
        method: str = 'uniform'
    ) -> List[str]:
        """
        Extract frames from video
        
        Args:
            filepath: Input video path
            output_dir: Output directory for frames
            count: Number of frames to extract
            method: 'uniform' (evenly spaced) or 'scene' (scene change detection)
        
        Returns:
            List of extracted frame paths
        """
        os.makedirs(output_dir, exist_ok=True)
        
        if method == 'scene':
            return self._extract_scene_frames(filepath, output_dir, count)
        else:
            return self._extract_uniform_frames(filepath, output_dir, count)
    
    def _extract_uniform_frames(
        self,
        filepath: str,
        output_dir: str,
        count: int
    ) -> List[str]:
        """Extract evenly spaced frames"""
        frames = []
        
        try:
            # Get video duration
            cap = cv2.VideoCapture(filepath)
            if not cap.isOpened():
                return []
            
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            duration = total_frames / fps if fps > 0 else 0
            
            cap.release()
            
            if duration == 0:
                return []
            
            # Calculate intervals
            interval = duration / count
            
            for i in range(count):
                timestamp = i * interval
                output_path = os.path.join(output_dir, f"frame_{i:04d}.jpg")
                
                # Extract frame using ffmpeg
                cmd = [
                    self.ffmpeg_path, "-ss", str(timestamp),
                    "-i", filepath,
                    "-vframes", "1",
                    "-q:v", "2",
                    "-y",
                    output_path
                ]
                
                subprocess.run(cmd, capture_output=True, timeout=10)
                
                if os.path.exists(output_path):
                    frames.append(output_path)
            
            return frames
        
        except Exception as e:
            logger.info(f"Extract frames error: {e}")
            return []
    
    def _extract_scene_frames(
        self,
        filepath: str,
        output_dir: str,
        count: int
    ) -> List[str]:
        """Extract frames at scene changes"""
        frames = []
        
        try:
            cap = cv2.VideoCapture(filepath)
            if not cap.isOpened():
                return []
            
            prev_frame = None
            frame_idx = 0
            scene_indices = []
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                if prev_frame is not None:
                    # Calculate difference
                    diff = np.sum(np.abs(frame.astype(float) - prev_frame.astype(float)))
                    diff_normalized = diff / (frame.shape[0] * frame.shape[1] * frame.shape[2])
                    
                    # Threshold for scene change
                    if diff_normalized > 0.3:
                        scene_indices.append(frame_idx)
                
                prev_frame = frame
                frame_idx += 1
            
            cap.release()
            
            # Select top scene changes
            if len(scene_indices) > count:
                # Take evenly spaced samples from scene indices
                step = len(scene_indices) // count
                scene_indices = scene_indices[::step][:count]
            
            # Extract frames at scene indices
            for i, idx in enumerate(scene_indices):
                output_path = os.path.join(output_dir, f"scene_{i:04d}.jpg")
                
                cmd = [
                    self.ffmpeg_path, "-i", filepath,
                    "-vf", f"select=eq(n\\,{idx})",
                    "-vframes", "1",
                    "-y",
                    output_path
                ]
                
                subprocess.run(cmd, capture_output=True, timeout=10)
                
                if os.path.exists(output_path):
                    frames.append(output_path)
            
            return frames
        
        except Exception as e:
            logger.info(f"Scene detection error: {e}")
            return []
    
    def extract_thumbnail(
        self,
        filepath: str,
        output_path: str,
        timestamp: float = 1.0,
        size: Tuple[int, int] = (320, 240)
    ) -> bool:
        """Extract a single thumbnail at specified timestamp"""
        try:
            cmd = [
                self.ffmpeg_path, "-ss", str(timestamp),
                "-i", filepath,
                "-vframes", "1",
                "-vf", f"scale={size[0]}:{size[1]}:force_original_aspect_ratio=decrease,pad={size[0]}:{size[1]}:(ow-iw)/2:(oh-ih)/2",
                "-q:v", "3",
                "-y",
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, timeout=30)
            return os.path.exists(output_path)
        
        except Exception as e:
            logger.info(f"Thumbnail extraction error: {e}")
            return False
    
    def get_video_thumbnail_base64(self, filepath: str, timestamp: float = 1.0) -> Optional[str]:
        """Get thumbnail as base64 string"""
        import base64
        import tempfile
        
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            success = self.extract_thumbnail(filepath, tmp_path, timestamp)
            if success:
                with open(tmp_path, 'rb') as f:
                    return base64.b64encode(f.read()).decode()
            return None
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
    
    def create_gif(
        self,
        filepath: str,
        output_path: str,
        start: float = None,
        duration: float = 5.0,
        fps: int = 10,
        width: int = 320
    ) -> bool:
        """Create animated GIF from video clip"""
        try:
            cmd = [
                self.ffmpeg_path, "-i", filepath
            ]
            
            if start is not None:
                cmd.extend(["-ss", str(start)])
            
            cmd.extend([
                "-t", str(duration),
                "-vf", f"fps={fps},scale={width}:-1:flags=lanczos",
                "-y",
                output_path
            ])
            
            subprocess.run(cmd, capture_output=True, timeout=60)
            return os.path.exists(output_path)
        
        except Exception as e:
            logger.info(f"GIF creation error: {e}")
            return False
    
    def get_audio_info(self, filepath: str) -> Dict:
        """Get audio track information"""
        try:
            cmd = [
                self.ffmpeg_path, "-i", filepath,
                "-hide_basket"
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            output = result.stderr
            
            audio_info = {
                'has_audio': False,
                'codec': '',
                'sample_rate': 0,
                'channels': 0,
                'bitrate': 0
            }
            
            if 'Audio:' in output:
                audio_info['has_audio'] = True
                
                import re
                from loguru import logger
                audio_match = re.search(
                    r'Audio:\s+\w+\s+\(?([\w/]+)\)?.*?(\d+)\s*Hz.*?(\d+)\s*ch',
                    output
                )
                
                if audio_match:
                    audio_info['codec'] = audio_match.group(1)
                    audio_info['sample_rate'] = int(audio_match.group(2))
                    audio_info['channels'] = int(audio_match.group(3))
            
            return audio_info
        
        except Exception as e:
            return {'error': str(e)}


# Global processor instance
video_processor = VideoProcessor()


def get_video_processor() -> VideoProcessor:
    """Get video processor instance"""
    return video_processor
