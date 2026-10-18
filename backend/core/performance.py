"""
Performance Monitoring Middleware
Tracks request latency and resource usage
"""

import time
import psutil
from typing import Dict
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from collections import defaultdict
from loguru import logger


class PerformanceMonitor:
    """Track performance metrics"""
    
    def __init__(self, window_size: int = 1000):
        self.window_size = window_size
        self.request_times: Dict[str, list] = defaultdict(list)
        self.total_requests = 0
        self.total_errors = 0
        self.start_time = time.time()
    
    def record_request(self, path: str, duration_ms: float, status_code: int):
        """Record a request"""
        self.request_times[path].append(duration_ms)
        if len(self.request_times[path]) > self.window_size:
            self.request_times[path] = self.request_times[path][-self.window_size:]
        self.total_requests += 1
        if status_code >= 400:
            self.total_errors += 1
    
    def get_stats(self) -> Dict:
        """Get performance statistics"""
        uptime = time.time() - self.start_time
        
        # Calculate average response time per endpoint
        endpoint_stats = {}
        for path, times in self.request_times.items():
            if times:
                endpoint_stats[path] = {
                    "count": len(times),
                    "avg_ms": round(sum(times) / len(times), 2),
                    "min_ms": round(min(times), 2),
                    "max_ms": round(max(times), 2),
                    "p95_ms": round(sorted(times)[int(len(times) * 0.95)], 2) if len(times) > 20 else max(times)
                }
        
        # Get system metrics
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            process = psutil.Process()
            process_memory = process.memory_info()
            
            system_stats = {
                "cpu_percent": round(cpu_percent, 1),
                "memory_total_gb": round(memory.total / (1024**3), 2),
                "memory_used_gb": round(memory.used / (1024**3), 2),
                "memory_percent": memory.percent,
                "process_memory_mb": round(process_memory.rss / (1024**2), 2)
            }
        except Exception:
            system_stats = {"error": "Unable to get system stats"}
        
        return {
            "uptime_seconds": round(uptime, 1),
            "total_requests": self.total_requests,
            "total_errors": self.total_errors,
            "error_rate": round(self.total_errors / self.total_requests * 100, 2) if self.total_requests > 0 else 0,
            "requests_per_second": round(self.total_requests / uptime, 2) if uptime > 0 else 0,
            "endpoints": endpoint_stats,
            "system": system_stats
        }


# Global performance monitor
_performance_monitor = PerformanceMonitor()


def get_performance_monitor() -> PerformanceMonitor:
    """Get the global performance monitor"""
    return _performance_monitor


class PerformanceMiddleware(BaseHTTPMiddleware):
    """Middleware to track request performance"""
    
    async def dispatch(self, request: Request, call_next):
        # Skip for static files and health checks
        path = request.url.path
        if path.startswith("/static") or path == "/health":
            return await call_next(request)
        
        start_time = time.time()
        response = await call_next(request)
        duration_ms = (time.time() - start_time) * 1000
        
        # Record metrics
        _performance_monitor.record_request(
            path=path,
            duration_ms=duration_ms,
            status_code=response.status_code
        )
        
        # Add performance header
        response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"
        
        return response