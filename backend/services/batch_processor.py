"""
批量处理模块
优化大量文件的并发处理
"""

import asyncio
from typing import List, Callable, Any, Optional
from functools import wraps
import time


class BatchProcessor:
    """批量处理器"""
    
    def __init__(
        self,
        batch_size: int = 50,
        max_concurrency: int = 10
    ):
        self.batch_size = batch_size
        self.max_concurrency = max_concurrency
        self.semaphore = asyncio.Semaphore(max_concurrency)
    
    async def process_batch(
        self,
        items: List[Any],
        process_func: Callable,
        *args,
        **kwargs
    ) -> List[Any]:
        """
        批量处理项目
        """
        results = []
        
        # 分批处理
        for i in range(0, len(items), self.batch_size):
            batch = items[i:i + self.batch_size]
            
            # 并发处理当前批次
            tasks = []
            for item in batch:
                task = self._process_with_semaphore(
                    process_func, item, *args, **kwargs
                )
                tasks.append(task)
            
            # 等待当前批次完成
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            results.extend(batch_results)
        
        return results
    
    async def _process_with_semaphore(
        self,
        func: Callable,
        item: Any,
        *args,
        **kwargs
    ) -> Any:
        """使用信号量限制并发"""
        async with self.semaphore:
            try:
                if asyncio.iscoroutinefunction(func):
                    return await func(item, *args, **kwargs)
                else:
                    loop = asyncio.get_event_loop()
                    return await loop.run_in_executor(
                        None,
                        lambda: func(item, *args, **kwargs)
                    )
            except Exception as e:
                return {"error": str(e), "item": item}


class ProgressTracker:
    """进度跟踪器"""
    
    def __init__(self, total: int, callback: Optional[Callable] = None):
        self.total = total
        self.current = 0
        self.callback = callback
        self.start_time = time.time()
    
    def update(self, count: int = 1):
        """更新进度"""
        self.current += count
        if self.callback:
            percent = (self.current / self.total) * 100
            elapsed = time.time() - self.start_time
            eta = (elapsed / self.current) * (self.total - self.current) if self.current > 0 else 0
            self.callback({
                "current": self.current,
                "total": self.total,
                "percent": percent,
                "elapsed": elapsed,
                "eta": eta
            })
    
    def get_progress(self) -> dict:
        """获取当前进度"""
        return {
            "current": self.current,
            "total": self.total,
            "percent": (self.current / self.total) * 100 if self.total > 0 else 0,
            "elapsed": time.time() - self.start_time,
            "eta": (time.time() - self.start_time) / self.current * (self.total - self.current) if self.current > 0 else 0
        }


# 全局批量处理器实例
batch_processor = BatchProcessor(batch_size=50, max_concurrency=10)
