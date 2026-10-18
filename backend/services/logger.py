"""
Logging Service
Comprehensive logging with rotation and rollback support
"""

import os
import json
from loguru import logger
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from logging.handlers import RotatingFileHandler
import asyncio


class OperationLogger:
    """
    Comprehensive operation logging service
    
    Features:
    - Structured logging (JSON)
    - File rotation
    - Operation rollback support
    - Search and query
    """
    
    def __init__(self, log_dir: str = "./logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create loggers for different operations
        self.loggers = {
            'file': self._create_logger('file_ops', 'file_operations.log'),
            'task': self._create_logger('task', 'task_operations.log'),
            'ai': self._create_logger('ai', 'ai_operations.log'),
            'system': self._create_logger('system', 'system.log'),
            'error': self._create_logger('error', 'error.log'),
        }
        
        # In-memory log cache for quick access
        self._cache = []
        self._cache_max = 1000
    
    def _create_logger(self, name: str, filename: str) -> logging.Logger:
        """Create a logger with file rotation"""
        logger = logger.bind(name=name)
        logger.setLevel(logging.DEBUG)
        
        # File handler with rotation
        handler = RotatingFileHandler(
            self.log_dir / filename,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        
        # JSON formatter
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        ))
        
        logger.addHandler(handler)
        
        return logger
    
    def log_operation(
        self,
        category: str,
        operation: str,
        details: Dict,
        rollback_action: Optional[Dict] = None
    ):
        """
        Log an operation with structured data
        
        Args:
            category: file/task/ai/system
            operation: operation name
            details: operation details
            rollback_action: action to take for rollback
        """
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'category': category,
            'operation': operation,
            'details': details,
            'rollback_available': rollback_action is not None
        }
        
        # Log to file
        logger = self.loggers.get(category, self.loggers['system'])
        logger.info(json.dumps(details, ensure_ascii=False))
        
        # Store rollback info if available
        if rollback_action:
            rollback_file = self.log_dir / 'rollback' / f"{category}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            rollback_file.parent.mkdir(exist_ok=True)
            with open(rollback_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'log_entry': log_entry,
                    'rollback_action': rollback_action
                }, f, ensure_ascii=False, indent=2)
        
        # Update cache
        self._cache.append(log_entry)
        if len(self._cache) > self._cache_max:
            self._cache = self._cache[-self._cache_max:]
        
        return log_entry
    
    def log_file_operation(
        self,
        operation: str,
        src_path: str,
        dst_path: str = None,
        success: bool = True,
        error: str = None
    ):
        """Log a file operation"""
        details = {
            'operation': operation,
            'src_path': src_path,
            'dst_path': dst_path,
            'success': success
        }
        
        if error:
            details['error'] = error
        
        # Create rollback action
        rollback = None
        if success and dst_path and operation == 'move':
            rollback = {
                'action': 'move',
                'src_path': dst_path,
                'dst_path': src_path
            }
        
        return self.log_operation('file', operation, details, rollback)
    
    def log_task_operation(
        self,
        task_id: str,
        operation: str,
        details: Dict
    ):
        """Log a task operation"""
        details['task_id'] = task_id
        return self.log_operation('task', operation, details)
    
    def log_ai_operation(
        self,
        file_id: int,
        operation: str,
        tags: List[str] = None,
        confidence: float = None
    ):
        """Log an AI operation"""
        details = {
            'file_id': file_id,
            'operation': operation
        }
        
        if tags:
            details['tags'] = tags
        if confidence is not None:
            details['confidence'] = confidence
        
        return self.log_operation('ai', operation, details)
    
    def get_recent_logs(
        self,
        category: str = None,
        limit: int = 100
    ) -> List[Dict]:
        """Get recent log entries"""
        if category:
            return [l for l in self._cache if l.get('category') == category][-limit:]
        return self._cache[-limit:]
    
    def search_logs(
        self,
        keyword: str,
        category: str = None,
        start_date: datetime = None,
        end_date: datetime = None
    ) -> List[Dict]:
        """Search logs by keyword and filters"""
        results = []
        
        # Read from log files
        log_files = list(self.log_dir.glob('**/*.log'))
        
        for log_file in log_files:
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        try:
                            entry = json.loads(line)
                            
                            # Filter by category
                            if category and entry.get('category') != category:
                                continue
                            
                            # Filter by date
                            timestamp = entry.get('timestamp')
                            if timestamp:
                                dt = datetime.fromisoformat(timestamp)
                                if start_date and dt < start_date:
                                    continue
                                if end_date and dt > end_date:
                                    continue
                            
                            # Filter by keyword
                            entry_str = json.dumps(entry, ensure_ascii=False)
                            if keyword.lower() in entry_str.lower():
                                results.append(entry)
                        except json.JSONDecodeError:
                            continue
            except Exception as e:
                logger.info(f"Error reading log file {log_file}: {e}")
        
        return results[-limit:]
    
    def get_rollback_actions(
        self,
        start_date: datetime = None
    ) -> List[Dict]:
        """Get available rollback actions"""
        rollback_dir = self.log_dir / 'rollback'
        if not rollback_dir.exists():
            return []
        
        actions = []
        for rollback_file in rollback_dir.glob('*.json'):
            try:
                with open(rollback_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    timestamp = rollback_file.stem.split('_')[1:]
                    if timestamp:
                        dt = datetime.strptime('_'.join(timestamp), '%Y%m%d_%H%M%S')
                        if start_date and dt < start_date:
                            continue
                    
                    actions.append(data)
            except Exception as e:
                logger.info(f"Error reading rollback file {rollback_file}: {e}")
        
        return sorted(actions, key=lambda x: x['log_entry']['timestamp'], reverse=True)
    
    async def rollback_operation(self, rollback_file: str = None) -> Dict:
        """
        Rollback an operation
        
        Args:
            rollback_file: Specific rollback file to execute
        
        Returns:
            Result of rollback operation
        """
        if rollback_file:
            rollback_actions = [rollback_file]
        else:
            # Get most recent rollback
            rollbacks = self.get_rollback_actions()
            if not rollbacks:
                return {'success': False, 'message': 'No rollback actions available'}
            rollback_actions = rollbacks
        
        results = []
        for rollback in rollback_actions[:1]:  # Rollback one at a time
            action = rollback.get('rollback_action', {})
            op_type = action.get('action')
            
            try:
                if op_type == 'move':
                    import shutil
                    shutil.move(action['src_path'], action['dst_path'])
                    results.append({
                        'success': True,
                        'operation': 'move',
                        'from': action['src_path'],
                        'to': action['dst_path']
                    })
                    
                    self.log_operation('system', 'rollback', {
                        'rolled_back': rollback['log_entry']
                    })
            
            except Exception as e:
                results.append({
                    'success': False,
                    'error': str(e)
                })
        
        return {'results': results}
    
    def cleanup_old_logs(self, days: int = 30):
        """Clean up logs older than specified days"""
        cutoff = datetime.now() - timedelta(days=days)
        removed = 0
        
        for log_file in self.log_dir.glob('**/*.log*'):
            try:
                mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                if mtime < cutoff:
                    log_file.unlink()
                    removed += 1
            except Exception as e:
                logger.info(f"Error removing {log_file}: {e}")
        
        # Clean rollback files
        rollback_dir = self.log_dir / 'rollback'
        if rollback_dir.exists():
            for rollback_file in rollback_dir.glob('*.json'):
                try:
                    mtime = datetime.fromtimestamp(rollback_file.stat().st_mtime)
                    if mtime < cutoff:
                        rollback_file.unlink()
                        removed += 1
                except OSError:  # 文件无法删除（权限或文件不存在）
                    pass
        
        return {'removed': removed}


# Global logger instance
operation_logger = OperationLogger()


def get_logger() -> OperationLogger:
    """Get logger instance"""
    return operation_logger
