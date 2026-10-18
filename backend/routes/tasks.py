"""
Tasks API Routes
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Any, List, Optional
from pydantic import BaseModel
import requests
import json

from database.db import Database, get_db
from core.scheduler import TaskScheduler, TaskStatus

router = APIRouter(prefix="/api/tasks", tags=["Tasks"])


# ============ Models ============

class TaskResponse(BaseModel):
    task_id: str
    task_type: str
    device_id: Optional[str] = None
    status: str
    progress: int = 0
    error_msg: Optional[str] = None
    # 注意：历史上 result 列可能存有非 dict 的 JSON（list/标量）或脏文本，
    # 用 Any 兜底，避免单行脏数据让整个列表接口 500
    result: Optional[Any] = None
    created_at: Optional[str] = None
    
    class Config:
        from_attributes = True


class CreateTaskRequest(BaseModel):
    task_type: str  # ai_classify, archive, dedup, sync
    device_id: str
    params: dict = {}


class TaskResultResponse(BaseModel):
    task_id: str
    status: str
    result: Optional[dict] = None
    error: Optional[str] = None


# ============ Routes ============

@router.get("/", response_model=List[TaskResponse])
async def list_tasks(
    status: Optional[str] = Query(None, description="Filter by status: pending, running, success, failed"),
    task_type: Optional[str] = Query(None, description="Filter by type"),
    limit: int = Query(50, ge=1, le=500),
    db: Database = Depends(get_db)
):
    """List all tasks"""
    if status:
        sql = "SELECT * FROM tasks WHERE status = ? ORDER BY created_at DESC LIMIT ?"
        tasks = await db.fetchall(sql, (status, limit))
    elif task_type:
        sql = "SELECT * FROM tasks WHERE task_type = ? ORDER BY created_at DESC LIMIT ?"
        tasks = await db.fetchall(sql, (task_type, limit))
    else:
        sql = "SELECT * FROM tasks ORDER BY created_at DESC LIMIT ?"
        tasks = await db.fetchall(sql, (limit,))
    
    # DB 中 params/result 为 JSON 字符串，需解析后再交给响应模型校验
    for task in tasks:
        for key in ('params', 'result'):
            value = task.get(key)
            if isinstance(value, str):
                try:
                    task[key] = json.loads(value)
                except (ValueError, TypeError):
                    pass  # 脏数据保留原样，由 Optional[Any] 兜底
    
    return tasks


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str, db: Database = Depends(get_db)):
    """Get task details"""
    task = await db.fetchone("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Parse JSON fields
    if task.get('params'):
        task['params'] = json.loads(task['params'])
    if task.get('result'):
        task['result'] = json.loads(task['result'])
    
    return task


@router.post("/{task_id}/result", response_model=TaskResultResponse)
async def submit_task_result(
    task_id: str,
    status: str,
    result: Optional[dict] = None,
    error: Optional[str] = None,
    db: Database = Depends(get_db)
):
    """Submit task result (called by ARM device)"""
    task = await db.fetchone("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Update task
    if status == "success":
        await db.execute(
            "UPDATE tasks SET status = 'success', result = ?, progress = 100, finished_at = CURRENT_TIMESTAMP WHERE task_id = ?",
            (json.dumps(result) if result else None, task_id)
        )
    else:
        await db.update_task_status(task_id, status, error_msg=error)
    
    return {"task_id": task_id, "status": status}


@router.post("/{task_id}/progress")
async def update_task_progress(
    task_id: str,
    progress: int = Query(..., ge=0, le=100),
    db: Database = Depends(get_db)
):
    """Update task progress (called by ARM device)"""
    task = await db.fetchone("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    await db.execute(
        "UPDATE tasks SET progress = ?, status = CASE WHEN status = 'pending' THEN 'running' ELSE status END WHERE task_id = ?",
        (progress, task_id)
    )
    
    return {"task_id": task_id, "progress": progress}


@router.post("/{task_id}/dispatch")
async def dispatch_task(
    task_id: str,
    db: Database = Depends(get_db)
):
    """Dispatch a task to ARM device"""
    task = await db.fetchone("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    device = await db.fetchone("SELECT * FROM devices WHERE device_id = ?", (task['device_id'],))
    if not device or device['status'] != 'online':
        raise HTTPException(status_code=400, detail="Device is not online")
    
    try:
        # Dispatch to ARM device
        response = requests.post(
            f"http://{device['ip_address']}:{device['port']}/task/start",
            json={
                "task_id": task_id,
                "task_type": task['task_type'],
                "params": json.loads(task['params']) if task['params'] else {}
            },
            timeout=10
        )
        
        # Update task status
        await db.update_task_status(task_id, "running")
        
        return {"status": "dispatched", "response": response.json()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to dispatch: {str(e)}")


@router.delete("/{task_id}")
async def cancel_task(task_id: str, db: Database = Depends(get_db)):
    """Cancel a task"""
    task = await db.fetchone("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task['status'] in ['success', 'failed']:
        raise HTTPException(status_code=400, detail="Cannot cancel completed task")
    
    await db.execute(
        "UPDATE tasks SET status = 'failed', error_msg = 'Cancelled by user', finished_at = CURRENT_TIMESTAMP WHERE task_id = ?",
        (task_id,)
    )
    
    return {"status": "cancelled", "task_id": task_id}


@router.post("/create-and-dispatch")
async def create_and_dispatch_task(
    request: CreateTaskRequest,
    db: Database = Depends(get_db)
):
    """Create a task and immediately dispatch to device"""
    import uuid
    
    # Check device
    device = await db.fetchone("SELECT * FROM devices WHERE device_id = ?", (request.device_id,))
    if not device:
        raise HTTPException(status_code=400, detail="Device not found")
    
    if device['status'] != 'online':
        raise HTTPException(status_code=400, detail="Device is not online")
    
    # Create task
    task_id = str(uuid.uuid4())
    await db.create_task(task_id, request.task_type, request.device_id, request.params)
    
    try:
        # Dispatch to ARM device
        response = requests.post(
            f"http://{device['ip_address']}:{device['port']}/task/start",
            json={
                "task_id": task_id,
                "task_type": request.task_type,
                "params": request.params
            },
            timeout=10
        )
        
        await db.update_task_status(task_id, "running")
        
        return {
            "task_id": task_id,
            "status": "dispatched",
            "device": request.device_id
        }
    except Exception as e:
        await db.update_task_status(task_id, "failed", error_msg=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to dispatch: {str(e)}")
