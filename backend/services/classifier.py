"""
AI Classification Service
Analyzes media files and generates tags, features, etc.
"""

import os
import asyncio
import numpy as np
from typing import Dict, List, Optional, Callable
from pathlib import Path
import json

from database.db import Database
from modules.mod_plugins import get_plugin_manager
from core.config_manager import get_config
from loguru import logger


class AIClassifier:
    """
    AI-powered media classification service
    """

    def __init__(self, db: Database):
        self.db = db
        self.plugin_manager = get_plugin_manager()
        self.config = get_config()       # ConfigManager for general config
        self.ai_cfg  = get_config()['ai_config']  # AI engine config from YAML
        self._running = False
        self._progress_callback: Optional[Callable] = None
    
    def set_progress_callback(self, callback: Callable):
        """Set callback for progress updates"""
        self._progress_callback = callback
    
    async def classify_media(
        self,
        file_id: int = None,
        device_id: str = None,
        force: bool = False
    ) -> Dict:
        """
        Classify media files using AI
        
        Args:
            file_id: Specific file to classify
            device_id: Device to use for inference
            force: Re-classify even if already processed
        """
        self._running = True
        
        try:
            # Get files to process
            if file_id:
                sql = "SELECT * FROM media_files WHERE id = ?"
                params = (file_id,)
            elif device_id:
                sql = "SELECT * FROM media_files WHERE device_id = ?"
                params = (device_id,)
            else:
                sql = "SELECT * FROM media_files WHERE ai_processed = 0"
                params = ()
            
            if not force:
                sql += " AND ai_processed = 0"
            
            files = await self.db.fetchall(sql, params)
            
            if not files:
                return {'message': 'No files to classify', 'count': 0}
            
            # Get AI engine config (from YAML dict via config_manager)
            engine = self.plugin_manager.get_ai_engine('cpu', {
                'model_path': self.ai_cfg['image_classification']['model_path'],
                'input_size': self.ai_cfg['image_classification']['input_size'],
                'threshold': self.ai_cfg['image_classification']['threshold']
            })
            
            results = []
            
            for i, file_info in enumerate(files):
                if not self._running:
                    break
                
                try:
                    result = await self._classify_file(file_info, engine)
                    results.append(result)
                    
                    if self._progress_callback:
                        self._progress_callback({
                            'current': i + 1,
                            'total': len(files),
                            'file_id': file_info['id'],
                            'status': result.get('status')
                        })
                
                except Exception as e:
                    logger.info(f"Classification error for {file_info['file_path']}: {e}")
                    results.append({
                        'file_id': file_info['id'],
                        'status': 'error',
                        'error': str(e)
                    })
            
            return {
                'total': len(files),
                'processed': len(results),
                'results': results
            }
        
        finally:
            self._running = False
    
    async def _classify_file(self, file_info: Dict, engine) -> Dict:
        """Classify a single file"""
        filepath = file_info['file_path']
        
        if not os.path.exists(filepath):
            return {
                'file_id': file_info['id'],
                'status': 'error',
                'error': 'File not found'
            }
        
        # Run AI inference based on file type
        if file_info['file_type'] == 'video':
            result = engine.video_predict(filepath)
        else:
            result = engine.image_predict(filepath)
        
        tags = result.get('tags', [])
        confidence = result.get('confidence', 0)
        feature = result.get('feature', [])
        
        # Convert feature to bytes for storage
        feature_bytes = self._feature_to_bytes(feature) if feature else None
        
        # Update database
        await self.db.update_ai_analysis(
            file_id=file_info['id'],
            tags=tags,
            feature_vector=feature_bytes,
            confidence=confidence
        )
        
        # Auto-create albums based on tags
        await self._create_auto_albums(file_info['id'], tags)
        
        return {
            'file_id': file_info['id'],
            'status': 'success',
            'tags': tags,
            'confidence': confidence
        }
    
    def _feature_to_bytes(self, feature: List[float]) -> bytes:
        """Convert feature list to bytes for storage"""
        arr = np.array(feature, dtype=np.float32)
        return arr.tobytes()
    
    async def _create_auto_albums(self, file_id: int, tags: List[str]):
        """Create automatic albums based on tags"""
        if not tags:
            return
        
        # Group tags by type
        scene_tags = ['indoor', 'outdoor', 'nature', 'beach', 'mountain', 'city', 'sunset', 'sunrise', 'night']
        person_tags = ['portrait', 'face', 'person']
        event_tags = ['wedding', 'birthday', 'party', 'travel', 'holiday']
        
        created_albums = []
        
        for tag in tags:
            tag_lower = tag.lower()
            
            # Scene albums
            if tag_lower in scene_tags:
                album_name = f"场景/{tag}"
                album_id = await self._ensure_album(album_name, 'scene')
                await self._add_to_album(album_id, file_id)
                created_albums.append(album_name)
            
            # Date-based albums
            file_info = await self.db.fetchone(
                "SELECT taken_at FROM media_files WHERE id = ?",
                (file_id,)
            )
            if file_info and file_info.get('taken_at'):
                # Extract date info for date albums
                date_str = file_info['taken_at'][:10]  # YYYY-MM-DD
                year = date_str[:4]
                month = date_str[5:7]
                
                # Create year album
                year_album = f"日期/{year}"
                year_id = await self._ensure_album(year_album, 'date')
                await self._add_to_album(year_id, file_id)
                
                # Create month album
                month_album = f"日期/{year}/{month}"
                month_id = await self._ensure_album(month_album, 'date')
                await self._add_to_album(month_id, file_id)
        
        return created_albums
    
    async def _ensure_album(self, album_name: str, album_type: str) -> int:
        """Ensure album exists, create if not"""
        # Check if exists
        existing = await self.db.fetchone(
            "SELECT id FROM albums WHERE album_name = ?",
            (album_name,)
        )
        
        if existing:
            return existing['id']
        
        # Create new album
        return await self.db.create_album(album_name, album_type)
    
    async def _add_to_album(self, album_id: int, file_id: int):
        """Add file to album (for custom albums)"""
        try:
            await self.db.execute(
                "INSERT OR IGNORE INTO album_files (album_id, file_id) VALUES (?, ?)",
                (album_id, file_id)
            )
            
            # Update file count
            await self.db.execute(
                "UPDATE albums SET file_count = (SELECT COUNT(*) FROM album_files WHERE album_id = ?) WHERE id = ?",
                (album_id, album_id)
            )
        except Exception as e:
            logger.info(f"Error adding to album: {e}")
    
    async def face_detection(self, file_id: int) -> Dict:
        """Run face detection on a file"""
        file_info = await self.db.fetchone(
            "SELECT * FROM media_files WHERE id = ?",
            (file_id,)
        )
        
        if not file_info:
            return {'error': 'File not found'}
        
        if not os.path.exists(file_info['file_path']):
            return {'error': 'File not found on disk'}
        
        # Get engine
        engine = self.plugin_manager.get_ai_engine('cpu', {})
        
        # Run face detection
        result = engine.face_detect(file_info['file_path'])
        
        # Create person albums
        faces = result.get('faces', [])
        for i, face in enumerate(faces):
            album_name = f"人物/未识别-{i+1}"
            album_id = await self._ensure_album(album_name, 'person')
            await self._add_to_album(album_id, file_id)
        
        return {
            'file_id': file_id,
            'faces_detected': len(faces),
            'result': result
        }
    
    def stop(self):
        """Stop classification"""
        self._running = False


# Global classifier
classifier: Optional[AIClassifier] = None


async def get_classifier(db: Database) -> AIClassifier:
    """Get or create classifier instance"""
    global classifier
    if classifier is None:
        classifier = AIClassifier(db)
    return classifier
