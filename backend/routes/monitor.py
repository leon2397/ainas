"""
System Monitor API Routes
"""

from fastapi import APIRouter, Query
from typing import Optional

from services.monitor import get_monitor

router = APIRouter(prefix="/api/monitor", tags=["Monitor"])


@router.get("/status")
async def get_status():
    """Get complete system status"""
    monitor = get_monitor()
    return monitor.get_full_status()


@router.get("/cpu")
async def get_cpu():
    """Get CPU information"""
    monitor = get_monitor()
    return monitor.get_cpu_info()


@router.get("/memory")
async def get_memory():
    """Get memory information"""
    monitor = get_monitor()
    return monitor.get_memory_info()


@router.get("/disk")
async def get_disk(path: Optional[str] = Query(None)):
    """Get disk information"""
    monitor = get_monitor()
    return monitor.get_disk_info(path)


@router.get("/network")
async def get_network():
    """Get network information"""
    monitor = get_monitor()
    return monitor.get_network_info()


@router.get("/process")
async def get_process():
    """Get current process information"""
    monitor = get_monitor()
    return monitor.get_process_info()


@router.get("/alerts")
async def get_alerts():
    """Get system alerts"""
    monitor = get_monitor()
    return {
        "alerts": monitor.get_alerts()
    }


@router.get("/system")
async def get_system():
    """Get basic system information"""
    monitor = get_monitor()
    return monitor.get_system_info()
