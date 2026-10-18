"""
日志管理模块
日志轮转和清理
"""

import os
import time
import gzip
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional


class LogManager:
    """日志管理器"""
    
    def __init__(
        self,
        log_dir: str = "./logs",
        max_age_days: int = 30,
        max_size_mb: int = 100,
        compress_after_days: int = 7
    ):
        self.log_dir = Path(log_dir)
        self.max_age_days = max_age_days
        self.max_size_mb = max_size_mb
        self.compress_after_days = compress_after_days
    
    def get_log_files(self) -> list:
        """获取所有日志文件"""
        if not self.log_dir.exists():
            return []
        return list(self.log_dir.glob("*.log"))
    
    def get_total_size(self) -> float:
        """获取日志总大小（MB）"""
        total = 0
        for log_file in self.get_log_files():
            total += log_file.stat().st_size
        return total / (1024 * 1024)
    
    def cleanup_old_logs(self, days: Optional[int] = None) -> dict:
        """
        清理旧日志
        
        Returns:
            dict: 清理结果
        """
        if days is None:
            days = self.max_age_days
        
        cutoff = time.time() - (days * 24 * 3600)
        deleted = 0
        freed_mb = 0
        
        for log_file in self.get_log_files():
            if log_file.stat().st_mtime < cutoff:
                size = log_file.stat().st_size
                log_file.unlink()
                deleted += 1
                freed_mb += size / (1024 * 1024)
        
        return {
            "deleted": deleted,
            "freed_mb": round(freed_mb, 2)
        }
    
    def compress_old_logs(self, days: Optional[int] = None) -> dict:
        """
        压缩旧日志
        
        Returns:
            dict: 压缩结果
        """
        if days is None:
            days = self.compress_after_days
        
        cutoff = time.time() - (days * 24 * 3600)
        compressed = 0
        saved_mb = 0
        
        for log_file in self.get_log_files():
            # 只压缩未压缩的大文件
            if log_file.stat().st_mtime < cutoff and log_file.suffix != ".gz":
                original_size = log_file.stat().st_size
                
                # 压缩
                with open(log_file, 'rb') as f_in:
                    with gzip.open(str(log_file) + '.gz', 'wb') as f_out:
                        f_out.writelines(f_in)
                
                compressed_size = Path(str(log_file) + '.gz').stat().st_size
                
                # 删除原文件
                log_file.unlink()
                
                compressed += 1
                saved_mb += (original_size - compressed_size) / (1024 * 1024)
        
        return {
            "compressed": compressed,
            "saved_mb": round(saved_mb, 2)
        }
    
    def rotate_log(self, log_file: Path) -> bool:
        """
        轮转日志
        
        Args:
            log_file: 日志文件路径
        
        Returns:
            bool: 是否成功
        """
        if not log_file.exists():
            return False
        
        # 检查大小
        size_mb = log_file.stat().st_size / (1024 * 1024)
        if size_mb < self.max_size_mb:
            return False
        
        # 轮转
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        rotated_name = f"{log_file.stem}_{timestamp}.log"
        rotated_path = log_file.parent / rotated_name
        
        log_file.rename(rotated_path)
        
        return True
    
    def get_log_summary(self) -> dict:
        """获取日志摘要"""
        files = self.get_log_files()
        
        if not files:
            return {
                "total_files": 0,
                "total_size_mb": 0,
                "oldest_file": None,
                "newest_file": None,
            }
        
        oldest = min(files, key=lambda f: f.stat().st_mtime)
        newest = max(files, key=lambda f: f.stat().st_mtime)
        
        return {
            "total_files": len(files),
            "total_size_mb": round(self.get_total_size(), 2),
            "oldest_file": oldest.name,
            "newest_file": newest.name,
        }


# 全局日志管理器
log_manager = LogManager()
