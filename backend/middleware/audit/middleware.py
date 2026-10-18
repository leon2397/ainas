"""
审计日志中间件
企业级功能 - Phase 2.2
"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import time
import uuid

from core.audit import audit_logger, AuditLevel, AuditCategory, AuditAction


class AuditMiddleware(BaseHTTPMiddleware):
    """审计日志中间件"""
    
    def __init__(self, app: ASGIApp, exclude_paths: list = None):
        super().__init__(app)
        self.exclude_paths = exclude_paths or [
            "/health",
            "/status",
            "/docs",
            "/openapi.json",
            "/redoc",
        ]
    
    async def dispatch(self, request: Request, call_next):
        # 生成请求ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # 检查是否需要记录
        path = request.url.path
        if any(path.startswith(excluded) for excluded in self.exclude_paths):
            return await call_next(request)
        
        # 记录开始时间
        start_time = time.time()
        
        # 获取用户信息
        user = getattr(request.state, 'user', None)
        user_id = user.get('id') if user else None
        user_name = user.get('username') if user else None
        
        # 获取客户端信息
        ip_address = self._get_client_ip(request)
        user_agent = request.headers.get('user-agent')
        
        # 处理请求
        try:
            response = await call_next(request)
            duration = time.time() - start_time
            
            # 确定审计级别和动作
            level, action = self._determine_audit_info(request, response)
            
            # 记录成功日志
            await audit_logger.log(
                level=level,
                category=AuditCategory.SYSTEM,
                action=action,
                description=f"{request.method} {path}",
                user_id=user_id,
                user_name=user_name,
                ip_address=ip_address,
                user_agent=user_agent,
                details={
                    "method": request.method,
                    "path": path,
                    "status_code": response.status_code,
                    "duration_ms": round(duration * 1000, 2),
                    "query_params": str(request.query_params),
                },
                success=response.status_code < 400,
                request_id=request_id,
            )
            
            return response
            
        except Exception as e:
            duration = time.time() - start_time
            
            # 记录错误日志
            await audit_logger.log(
                level=AuditLevel.ERROR,
                category=AuditCategory.SYSTEM,
                action=AuditAction.SYSTEM_STOP,
                description=f"Request failed: {request.method} {path}",
                user_id=user_id,
                user_name=user_name,
                ip_address=ip_address,
                user_agent=user_agent,
                details={
                    "method": request.method,
                    "path": path,
                    "error": str(e),
                    "duration_ms": round(duration * 1000, 2),
                },
                success=False,
                error_message=str(e),
                request_id=request_id,
            )
            
            raise
    
    def _get_client_ip(self, request: Request) -> str:
        """获取客户端IP"""
        # 检查代理头
        forwarded = request.headers.get('x-forwarded-for')
        if forwarded:
            return forwarded.split(',')[0].strip()
        
        real_ip = request.headers.get('x-real-ip')
        if real_ip:
            return real_ip
        
        # 直接连接
        if request.client:
            return request.client.host
        
        return "unknown"
    
    def _determine_audit_info(self, request: Request, response: Response):
        """确定审计级别和动作"""
        path = request.url.path
        method = request.method
        
        # 根据状态码确定级别
        if response.status_code >= 500:
            level = AuditLevel.ERROR
        elif response.status_code >= 400:
            level = AuditLevel.WARNING
        else:
            level = AuditLevel.INFO
        
        # 根据路径和动作确定审计动作
        if "/auth/login" in path:
            action = AuditAction.LOGIN if response.status_code < 400 else AuditAction.LOGIN_FAILED
        elif "/auth/logout" in path:
            action = AuditAction.LOGOUT
        elif "/media" in path and method == "POST":
            action = AuditAction.MEDIA_UPLOAD
        elif "/media" in path and method == "DELETE":
            action = AuditAction.MEDIA_DELETE
        elif "/album" in path and method == "POST":
            action = AuditAction.ALBUM_CREATE
        elif "/album" in path and method == "DELETE":
            action = AuditAction.ALBUM_DELETE
        elif "/user" in path and method == "POST":
            action = AuditAction.USER_CREATE
        elif "/user" in path and method == "DELETE":
            action = AuditAction.USER_DELETE
        else:
            action = AuditAction.CONFIG_CHANGE
        
        return level, action
