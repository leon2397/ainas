"""
超时控制模块
防止API请求和处理超时
"""

import asyncio
from functools import wraps
from typing import Optional, Any, Callable
import time


# 默认超时配置（秒）
DEFAULT_TIMEOUT = 30
SCAN_TIMEOUT = 300  # 5分钟
AI_TIMEOUT = 60  # 1分钟


class TimeoutError(Exception):
    """超时异常"""
    pass


async def with_timeout(coro, timeout: float = DEFAULT_TIMEOUT) -> Any:
    """
    异步函数超时包装器
    
    Args:
        coro: 协程函数
        timeout: 超时时间（秒）
    
    Returns:
        协程结果
    
    Raises:
        TimeoutError: 超时时抛出
    """
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError:
        raise TimeoutError(f"Operation timed out after {timeout}s")


def timeout_decorator(timeout: float = DEFAULT_TIMEOUT):
    """超时装饰器"""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await with_timeout(func(*args, **kwargs), timeout=timeout)
        return wrapper
    return decorator


class RateLimiter:
    """简单的内存限流器"""
    
    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.requests = []
    
    def is_allowed(self) -> bool:
        """检查是否允许请求"""
        now = time.time()
        # 清理超过1分钟的请求
        self.requests = [t for t in self.requests if now - t < 60]
        
        if len(self.requests) >= self.requests_per_minute:
            return False
        
        self.requests.append(now)
        return True
    
    def get_remaining(self) -> int:
        """获取剩余请求次数"""
        now = time.time()
        self.requests = [t for t in self.requests if now - t < 60]
        return max(0, self.requests_per_minute - len(self.requests))


# 全局限流器
rate_limiter = RateLimiter(requests_per_minute=60)


class CircuitBreaker:
    """熔断器 - 防止连续失败"""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: float = 60
    ):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failures = 0
        self.last_failure_time = 0
        self.state = "closed"  # closed, open, half_open
    
    def record_failure(self):
        """记录失败"""
        self.failures += 1
        self.last_failure_time = time.time()
        
        if self.failures >= self.failure_threshold:
            self.state = "open"
    
    def record_success(self):
        """记录成功"""
        self.failures = 0
        self.state = "closed"
    
    def is_open(self) -> bool:
        """检查是否熔断"""
        if self.state == "open":
            # 检查是否超时可以恢复
            if time.time() - self.last_failure_time > self.timeout:
                self.state = "half_open"
                return False
            return True
        return False
    
    def can_proceed(self) -> bool:
        """是否可以继续"""
        if self.state == "open":
            return not self.is_open()
        return True


# 全局熔断器
scan_circuit_breaker = CircuitBreaker(failure_threshold=3, timeout=60)
