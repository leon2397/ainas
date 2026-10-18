# Task Scheduler

import uuid
import asyncio
from datetime import datetime
from typing import Dict, Optional, Callable, Any
from enum import Enum

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"

class Task:
    def __init__(self, task_type: str, device_id: str, params: Dict[str, Any]):
        self.task_id = str(uuid.uuid4())
        self.task_type = task_type
        self.device_id = device_id
        self.params = params
        self.status = TaskStatus.PENDING
        self.progress = 0
        self.create_time = datetime.now()
        self.finish_time: Optional[datetime] = None
        self.error_msg = ""
        self.result: Optional[Any] = None

class TaskScheduler:
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.tasks: Dict[str, Task] = {}
        self._running = False
        self._queue = asyncio.Queue()
    
    def create_task(self, task_type: str, device_id: str, params: Dict) -> Task:
        """创建新任务"""
        task = Task(task_type, device_id, params)
        self.tasks[task.task_id] = task
        return task
    
    async def submit_task(self, task: Task) -> str:
        """提交任务到队列"""
        await self._queue.put(task)
        return task.task_id
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务状态"""
        return self.tasks.get(task_id)
    
    def update_progress(self, task_id: str, progress: int):
        """更新任务进度"""
        if task_id in self.tasks:
            self.tasks[task_id].progress = min(100, max(0, progress))
    
    async def start(self):
        """启动调度器"""
        self._running = True
        workers = [
            asyncio.create_task(self._worker())
            for _ in range(self.max_workers)
        ]
        await asyncio.gather(*workers)
    
    async def _worker(self):
        """工作线程"""
        while self._running:
            try:
                task = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                await self._execute_task(task)
            except asyncio.TimeoutError:
                continue
    
    async def _execute_task(self, task: Task):
        """执行任务（子类应重写此方法）"""
        task.status = TaskStatus.RUNNING
        # TODO: 实现具体的任务执行逻辑
        pass
    
    def stop(self):
        """停止调度器"""
        self._running = False

# 全局调度器实例
scheduler = TaskScheduler()
