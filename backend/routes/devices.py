"""
Devices API Routes
"""

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel
import json
import os
from pathlib import Path
import requests

from database.db import Database, get_db

router = APIRouter(prefix="/api/devices", tags=["Devices"])

# 诊断报告存档目录（AINAS 补充分支新增）
_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEVICE_REPORTS_DIR = (
    Path(os.environ.get("AI_NAS_DATA_DIR", str(_REPO_ROOT / "data"))) / "device_reports"
)


# ============ Models ============

class DeviceResponse(BaseModel):
    id: int
    device_id: str
    device_name: Optional[str] = None
    ip_address: Optional[str] = None
    port: Optional[int] = None
    npu_type: Optional[str] = None
    status: str = "offline"
    cpu_usage: Optional[float] = None
    npu_usage: Optional[float] = None
    storage_usage: Optional[float] = None
    
    class Config:
        from_attributes = True


class DeviceConfig(BaseModel):
    device_id: str
    device_name: str
    ip: str
    port: int = 8000
    username: str = ""
    password: str = ""
    npu_type: str
    ai_plugin: str
    storage_plugin: str


class TaskRequest(BaseModel):
    task_type: str  # ai_classify, archive, dedup
    device_id: str
    params: dict = {}


# ============ Routes ============

@router.get("/", response_model=List[DeviceResponse])
async def list_devices(db: Database = Depends(get_db)):
    """List all devices"""
    devices = await db.fetchall("SELECT * FROM devices ORDER BY device_name")
    return devices


@router.get("/online", response_model=List[DeviceResponse])
async def list_online_devices(db: Database = Depends(get_db)):
    """List all online devices"""
    devices = await db.get_online_devices()
    return devices


@router.get("/{device_id}", response_model=DeviceResponse)
async def get_device(device_id: str, db: Database = Depends(get_db)):
    """Get device details"""
    device = await db.fetchone("SELECT * FROM devices WHERE device_id = ?", (device_id,))
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device


@router.get("/{device_id}/info")
async def get_device_info(device_id: str, db: Database = Depends(get_db)):
    """Get device info from ARM device"""
    device = await db.fetchone("SELECT * FROM devices WHERE device_id = ?", (device_id,))
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    if device['status'] != 'online':
        return {"status": "offline", "message": "Device is not online"}
    
    try:
        # Call ARM device API
        response = requests.get(
            f"http://{device['ip_address']}:{device['port']}/device/info",
            timeout=5
        )
        return response.json()
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/{device_id}/diagnosis")
async def save_device_diagnosis(
    device_id: str,
    report: dict = Body(...),
    db: Database = Depends(get_db),
):
    """存档设备端上报的诊断报告（AINAS 补充分支）"""
    device = await db.fetchone("SELECT * FROM devices WHERE device_id = ?", (device_id,))
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    safe_id = "".join(c for c in device_id if c.isalnum() or c in "-_.")[:128] or "unknown"
    _DEVICE_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    target = _DEVICE_REPORTS_DIR / f"{safe_id}.json"
    with open(target, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    return {"status": "stored", "device_id": device_id, "path": str(target)}


@router.get("/{device_id}/diagnosis")
async def get_device_diagnosis(device_id: str, db: Database = Depends(get_db)):
    """读取设备诊断报告（AINAS 补充分支）"""
    device = await db.fetchone("SELECT * FROM devices WHERE device_id = ?", (device_id,))
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    safe_id = "".join(c for c in device_id if c.isalnum() or c in "-_.")[:128] or "unknown"
    target = _DEVICE_REPORTS_DIR / f"{safe_id}.json"
    if not target.exists():
        raise HTTPException(status_code=404, detail="Diagnosis report not found")
    with open(target, "r", encoding="utf-8") as f:
        return json.load(f)


@router.post("/add")
async def add_device(
    config: DeviceConfig,
    db: Database = Depends(get_db)
):
    """Manually add a device"""
    # Check if already exists
    existing = await db.fetchone("SELECT * FROM devices WHERE device_id = ?", (config.device_id,))
    if existing:
        raise HTTPException(status_code=400, detail="Device already exists")
    
    sql = """
    INSERT INTO devices (device_id, device_name, ip_address, port, npu_type)
    VALUES (?, ?, ?, ?, ?)
    """
    await db.execute(sql, (
        config.device_id,
        config.device_name,
        config.ip,
        config.port,
        config.npu_type
    ))
    
    return {"status": "added", "device_id": config.device_id}


@router.post("/register")
async def register_device(
    device_id: str,
    device_name: str,
    ip_address: str,
    port: int = 8000,
    npu_type: str = "unknown",
    cpu_usage: float = 0,
    npu_usage: float = 0,
    storage_usage: float = 0,
    db: Database = Depends(get_db)
):
    """Register or update a device (called by ARM device itself)"""
    existing = await db.fetchone("SELECT * FROM devices WHERE device_id = ?", (device_id,))
    
    if existing:
        # Update existing device
        await db.update_device_status(device_id, "online", cpu_usage, npu_usage)
        await db.execute(
            """UPDATE devices SET ip_address = ?, port = ?, storage_usage = ?,
               last_seen = CURRENT_TIMESTAMP WHERE device_id = ?""",
            (ip_address, port, storage_usage, device_id)
        )
    else:
        # Insert new device
        await db.execute(
            """INSERT INTO devices (device_id, device_name, ip_address, port, npu_type, status)
               VALUES (?, ?, ?, ?, ?, 'online')""",
            (device_id, device_name, ip_address, port, npu_type)
        )
    
    return {"status": "registered", "device_id": device_id}


@router.post("/heartbeat")
async def device_heartbeat(
    device_id: str,
    cpu_usage: float = 0,
    npu_usage: float = 0,
    storage_usage: float = 0,
    db: Database = Depends(get_db)
):
    """Device heartbeat to report status"""
    await db.update_device_status(device_id, "online", cpu_usage, npu_usage)
    await db.execute(
        "UPDATE devices SET storage_usage = ?, last_seen = CURRENT_TIMESTAMP WHERE device_id = ?",
        (storage_usage, device_id)
    )
    return {"status": "ok"}


@router.delete("/{device_id}")
async def remove_device(device_id: str, db: Database = Depends(get_db)):
    """Remove a device"""
    device = await db.fetchone("SELECT * FROM devices WHERE device_id = ?", (device_id,))
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    await db.execute("DELETE FROM devices WHERE device_id = ?", (device_id,))
    return {"status": "removed", "device_id": device_id}


@router.post("/{device_id}/test")
async def test_device_connection(device_id: str, db: Database = Depends(get_db)):
    """Test connection to a device"""
    device = await db.fetchone("SELECT * FROM devices WHERE device_id = ?", (device_id,))
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    try:
        response = requests.get(
            f"http://{device['ip_address']}:{device['port']}/health",
            timeout=5
        )
        return {"status": "success", "response": response.json()}
    except Exception as e:
        return {"status": "error", "message": str(e)}
