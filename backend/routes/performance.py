from loguru import logger
"""
Performance Monitoring API Routes
Provides endpoints for system performance metrics
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional
import logging

from core.performance import get_performance_monitor

logger = logger.bind(name="ai_nas")
router = APIRouter(prefix="/api/monitor", tags=["monitor"])


class EndpointStats(BaseModel):
    count: int
    avg_ms: float
    min_ms: float
    max_ms: float
    p95_ms: float


class SystemStats(BaseModel):
    cpu_percent: float
    memory_total_gb: float
    memory_used_gb: float
    memory_percent: float
    process_memory_mb: float


class PerformanceStats(BaseModel):
    uptime_seconds: float
    total_requests: int
    total_errors: int
    error_rate: float
    requests_per_second: float
    endpoints: Dict[str, EndpointStats]
    system: Optional[SystemStats]


class EndpointHealth(BaseModel):
    endpoint: str
    requests: int
    avg_ms: float
    status: str


@router.get("/performance", response_model=PerformanceStats)
async def get_performance_stats():
    """
    Get comprehensive performance statistics
    """
    try:
        monitor = get_performance_monitor()
        stats = monitor.get_stats()
        
        # Convert nested dicts to models
        endpoints = {}
        for path, data in stats.get("endpoints", {}).items():
            endpoints[path] = EndpointStats(**data)
        
        system = None
        if "system" in stats and isinstance(stats["system"], dict) and "error" not in stats["system"]:
            system = SystemStats(**stats["system"])
        
        return PerformanceStats(
            uptime_seconds=stats["uptime_seconds"],
            total_requests=stats["total_requests"],
            total_errors=stats["total_errors"],
            error_rate=stats["error_rate"],
            requests_per_second=stats["requests_per_second"],
            endpoints=endpoints,
            system=system
        )
    except Exception as e:
        logger.error(f"Error getting performance stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/endpoints", response_model=List[EndpointHealth])
async def get_endpoint_health():
    """
    Get health status of all endpoints
    """
    try:
        monitor = get_performance_monitor()
        stats = monitor.get_stats()
        
        endpoints = []
        for path, data in stats.get("endpoints", {}).items():
            avg_ms = data.get("avg_ms", 0)
            # Determine status based on response time
            if avg_ms < 100:
                status = "healthy"
            elif avg_ms < 500:
                status = "slow"
            else:
                status = "degraded"
            
            endpoints.append(EndpointHealth(
                endpoint=path,
                requests=data.get("count", 0),
                avg_ms=avg_ms,
                status=status
            ))
        
        # Sort by request count descending
        endpoints.sort(key=lambda x: x.requests, reverse=True)
        
        return endpoints
    except Exception as e:
        logger.error(f"Error getting endpoint health: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def get_monitor_health():
    """
    Quick health check for monitoring
    """
    try:
        monitor = get_performance_monitor()
        stats = monitor.get_stats()
        
        # Determine overall health
        error_rate = stats.get("error_rate", 0)
        cpu_percent = stats.get("system", {}).get("cpu_percent", 0) if isinstance(stats.get("system"), dict) else 0
        memory_percent = stats.get("system", {}).get("memory_percent", 0) if isinstance(stats.get("system"), dict) else 0
        
        if error_rate > 10 or cpu_percent > 90 or memory_percent > 90:
            status = "degraded"
        elif error_rate > 5 or cpu_percent > 70 or memory_percent > 70:
            status = "slow"
        else:
            status = "healthy"
        
        return {
            "status": status,
            "error_rate": error_rate,
            "cpu_percent": cpu_percent,
            "memory_percent": memory_percent,
            "requests_per_second": stats.get("requests_per_second", 0)
        }
    except Exception as e:
        logger.error(f"Error in health check: {e}")
        return {
            "status": "unknown",
            "error": str(e)
        }