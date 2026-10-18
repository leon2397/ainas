"""
API 限流中间件
防止恶意请求和暴力破解
"""

import time
from typing import Dict, Optional, Callable
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from collections import defaultdict


class RateLimiter:
    """简单内存限流器"""
    
    def __init__(
        self,
        requests_per_minute: int = 60,
        burst_size: int = 10
    ):
        self.requests_per_minute = requests_per_minute
        self.burst_size = burst_size
        self.requests: Dict[str, list] = defaultdict(list)
    
    def is_allowed(self, key: str) -> bool:
        """
        检查请求是否允许
        
        Args:
            key: 限流键（通常是 IP 或用户ID）
            
        Returns:
            True 如果允许，False 如果被限流
        """
        now = time.time()
        window_start = now - 60  # 1分钟窗口
        
        # 清理旧请求
        self.requests[key] = [
            req_time for req_time in self.requests[key]
            if req_time > window_start
        ]
        
        # 检查是否超过限制
        if len(self.requests[key]) >= self.requests_per_minute:
            return False
        
        # 记录请求
        self.requests[key].append(now)
        return True
    
    def get_remaining(self, key: str) -> int:
        """获取剩余请求次数"""
        now = time.time()
        window_start = now - 60
        
        # 清理旧请求
        self.requests[key] = [
            req_time for req_time in self.requests[key]
            if req_time > window_start
        ]
        
        return max(0, self.requests_per_minute - len(self.requests[key]))


class RateLimitMiddleware(BaseHTTPMiddleware):
    """限流中间件"""
    
    def __init__(
        self,
        app,
        default_limit: int = 60,
        auth_limit: int = 10,  # 登录接口更严格
        exempt_paths: list = None
    ):
        super().__init__(app)
        self.default_limiter = RateLimiter(default_limit)
        self.auth_limiter = RateLimiter(auth_limit)
        self.exempt_paths = exempt_paths or ["/health", "/docs", "/openapi.json"]
    
    async def dispatch(self, request: Request, call_next: Callable):
        """处理请求"""
        path = request.url.path
        
        # 跳过豁免路径
        if any(path.startswith(exempt) for exempt in self.exempt_paths):
            return await call_next(request)
        
        # 获取客户端标识
        client_ip = request.client.host if request.client else "unknown"
        
        # 选择限流器
        if path.startswith("/auth/login"):
            limiter = self.auth_limiter
            limit_type = "authentication"
        else:
            limiter = self.default_limiter
            limit_type = "general"
        
        # 检查限流
        if not limiter.is_allowed(client_ip):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded for {limit_type} requests. Please try again later.",
                headers={"Retry-After": "60"}
            )
        
        # 继续处理请求
        response = await call_next(request)
        
        # 添加限流头
        remaining = limiter.get_remaining(client_ip)
        response.headers["X-RateLimit-Limit"] = str(limiter.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """安全响应头中间件"""
    
    async def dispatch(self, request: Request, call_next: Callable):
        """添加安全响应头"""
        response = await call_next(request)
        
        # 安全响应头
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
            "img-src 'self' data: blob:; "
            "font-src 'self' https://cdnjs.cloudflare.com https://cdn.jsdelivr.net; "
            "connect-src 'self' ws: wss: http: https:; "
            "media-src 'self' blob: data:"
        )
        
        return response
