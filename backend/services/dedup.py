"""
Deduplication Service
Finds and marks duplicate media files
"""

import os
import numpy as np
from typing import Dict, List, Optional, Callable
from pathlib import Path
import json

from database.db import Database


class Deduplicator:
    """
    Media file deduplication service
    Uses file hash and feature similarity to find duplicates
    """
    
    def __init__(self, db: Database):
        self.db = db
        self._running = False
        self._progress_callback: Optional[Callable] = None
    
    def set_progress_callback(self, callback: Callable):
        """Set callback for progress updates"""
        self._progress_callback = callback
    
    async def find_duplicates(
        self,
        scope_path: str = None,
        threshold: float = 0.85,
        method: str = 'hash'
    ) -> Dict:
        """
        Find duplicate files
        
        Args:
            scope_path: Limit scope to specific path
            threshold: Similarity threshold (0-1)
            method: 'hash' (exact) or 'similar' (fuzzy)
        
        Returns:
            Dict with duplicate groups
        """
        self._running = True
        
        try:
            # Get all files
            if scope_path:
                sql = "SELECT * FROM media_files WHERE file_path LIKE ? AND is_deleted = 0"
                files = await self.db.fetchall(sql, (f"{scope_path}%",))
            else:
                sql = "SELECT * FROM media_files WHERE is_deleted = 0"
                files = await self.db.fetchall(sql)
            
            if not files:
                return {'groups': [], 'total': 0}
            
            if method == 'hash':
                groups = await self._find_by_hash(files)
            else:
                groups = await self._find_by_similarity(files, threshold)
            
            return {
                'groups': groups,
                'total': len(files),
                'duplicates_found': sum(len(g) - 1 for g in groups),
                'groups_count': len(groups)
            }
        
        finally:
            self._running = False
    
    async def _find_by_hash(self, files: List[Dict]) -> List[List[Dict]]:
        """Find exact duplicates by file hash"""
        # Group files by their quick hash (already calculated during scan)
        hash_groups = {}
        
        for i, file_info in enumerate(files):
            if not self._running:
                break
            
            # Calculate hash if not available
            filepath = file_info['file_path']
            
            if os.path.exists(filepath):
                quick_hash = self._calculate_quick_hash(filepath)
                
                if quick_hash not in hash_groups:
                    hash_groups[quick_hash] = []
                hash_groups[quick_hash].append(file_info)
            
            # Progress
            if self._progress_callback:
                self._progress_callback({
                    'current': i + 1,
                    'total': len(files),
                    'status': 'scanning'
                })
        
        # Return only groups with duplicates
        duplicates = [group for group in hash_groups.values() if len(group) > 1]
        
        # Mark duplicates in database
        for group in duplicates:
            for file_info in group[1:]:  # Keep first, mark rest as duplicate
                await self._mark_as_duplicate(file_info['id'], group[0]['id'])
        
        return duplicates
    
    async def _find_by_similarity(self, files: List[Dict], threshold: float) -> List[List[Dict]]:
        """Find similar files by feature vector"""
        # Get files with feature vectors
        files_with_features = []
        
        for file_info in files:
            if file_info.get('feature_vector') and os.path.exists(file_info['file_path']):
                files_with_features.append(file_info)
        
        if len(files_with_features) < 2:
            return []
        
        # Build feature matrix
        features = []
        for file_info in files_with_features:
            feat = np.frombuffer(file_info['feature_vector'], dtype=np.float32)
            features.append(feat)
        
        features_matrix = np.array(features)
        
        # Calculate similarity matrix
        # Using cosine similarity
        norms = np.linalg.norm(features_matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1
        normalized = features_matrix / norms
        similarity_matrix = np.dot(normalized, normalized.T)
        
        # Find groups
        visited = set()
        groups = []
        
        for i, file_a in enumerate(files_with_features):
            if i in visited:
                continue
            
            if not self._running:
                break
            
            group = [file_a]
            
            for j, file_b in enumerate(files_with_features):
                if i != j and j not in visited:
                    if similarity_matrix[i][j] >= threshold:
                        group.append(file_b)
                        visited.add(j)
            
            if len(group) > 1:
                groups.append(group)
                visited.add(i)
        
        # Mark duplicates
        for group in groups:
            for file_info in group[1:]:
                await self._mark_as_duplicate(file_info['id'], group[0]['id'])
        
        return groups
    
    async def _mark_as_duplicate(self, file_id: int, original_id: int):
        """Mark a file as duplicate of another"""
        await self.db.execute(
            """UPDATE media_files SET 
               updated_at = CURRENT_TIMESTAMP
               WHERE id = ?""",
            (file_id,)
        )
        
        # Store duplicate relationship (could add a separate table for this)
        await self.db.execute(
            """INSERT OR IGNORE INTO tasks (task_id, task_type, params, status)
               VALUES (?, 'duplicate', ?, 'completed')""",
            (f"dup_{file_id}", json.dumps({'original_id': original_id, 'duplicate_id': file_id}))
        )
    
    def _calculate_quick_hash(self, filepath: str, sample_size: int = 8192) -> str:
        """Calculate quick hash from file beginning and end"""
        try:
            import hashlib
            
            with open(filepath, 'rb') as f:
                start = f.read(sample_size)
                f.seek(-sample_size, 2)
                end = f.read(sample_size)
                f.seek(0, 2)
                size = f.tell()
            
            hash_input = start + end + str(size).encode()
            return hashlib.md5(hash_input).hexdigest()
        except (IOError, OSError, PermissionError):
            return ''  # 文件无法读取时返回空哈希
    
    async def get_duplicate_stats(self) -> Dict:
        """Get statistics about duplicates"""
        # Count files marked as duplicates
        result = await self.db.fetchone(
            """SELECT COUNT(*) as count FROM tasks 
               WHERE task_type = 'duplicate' AND status = 'completed'"""
        )
        
        duplicate_count = result['count'] if result else 0
        
        # Get space that could be saved
        result = await self.db.fetchall(
            """SELECT SUM(file_size) as total_size FROM tasks t
               JOIN media_files m ON t.task_id = 'dup_' || m.id
               WHERE t.task_type = 'duplicate' AND t.status = 'completed'"""
        )
        
        wasted_space = result[0]['total_size'] if result and result[0]['total_size'] else 0
        
        return {
            'duplicate_count': duplicate_count,
            'wasted_space_bytes': wasted_space,
            'wasted_space_formatted': self._format_bytes(wasted_space)
        }
    
    def _format_bytes(self, size: int) -> str:
        """Format bytes to human readable"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024:
                return f"{size:.2f} {unit}"
            size /= 1024
        return f"{size:.2f} PB"
    
    def stop(self):
        """Stop deduplication"""
        self._running = False


# Global deduplicator
deduplicator: Optional[Deduplicator] = None


async def get_deduplicator(db: Database) -> Deduplicator:
    """Get or create deduplicator instance"""
    global deduplicator
    if deduplicator is None:
        deduplicator = Deduplicator(db)
    return deduplicator
