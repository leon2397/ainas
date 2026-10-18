"""
RBAC 权限验证装饰器
企业级功能 - Phase 2.1
"""

from functools import wraps
from typing import List, Optional, Callable
from fastapi import HTTPException, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .manager import rbac_manager, Permission


security = HTTPBearer(auto_error=False)


def require_permission(permission: Permission):
    """要求特定权限的装饰器"""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 从 kwargs 获取 request
            request = kwargs.get('request')
            if not request:
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break
            
            if not request:
                raise HTTPException(status_code=500, detail="Request object not found")
            
            # 获取当前用户
            user = getattr(request.state, 'user', None)
            if not user:
                raise HTTPException(status_code=401, detail="Authentication required")
            
            user_id = user.get('id')
            
            # 检查权限
            if not rbac_manager.has_permission(user_id, permission):
                raise HTTPException(status_code=403, detail=f"Permission denied: {permission.value}")
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_any_permission(permissions: List[Permission]):
    """要求任一权限的装饰器"""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = kwargs.get('request')
            if not request:
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break
            
            if not request:
                raise HTTPException(status_code=500, detail="Request object not found")
            
            user = getattr(request.state, 'user', None)
            if not user:
                raise HTTPException(status_code=401, detail="Authentication required")
            
            user_id = user.get('id')
            
            if not rbac_manager.has_any_permission(user_id, permissions):
                raise HTTPException(status_code=403, detail="Permission denied")
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_all_permissions(permissions: List[Permission]):
    """要求所有权限的装饰器"""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = kwargs.get('request')
            if not request:
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break
            
            if not request:
                raise HTTPException(status_code=500, detail="Request object not found")
            
            user = getattr(request.state, 'user', None)
            if not user:
                raise HTTPException(status_code=401, detail="Authentication required")
            
            user_id = user.get('id')
            
            if not rbac_manager.has_all_permissions(user_id, permissions):
                raise HTTPException(status_code=403, detail="Permission denied")
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


class PermissionChecker:
    """权限检查器"""
    
    def __init__(self, permission: Permission):
        self.permission = permission
    
    async def __call__(self, request: Request):
        user = getattr(request.state, 'user', None)
        if not user:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        user_id = user.get('id')
        
        if not rbac_manager.has_permission(user_id, self.permission):
            raise HTTPException(status_code=403, detail=f"Permission denied: {self.permission.value}")
        
        return user


class AnyPermissionChecker:
    """任一权限检查器"""
    
    def __init__(self, permissions: List[Permission]):
        self.permissions = permissions
    
    async def __call__(self, request: Request):
        user = getattr(request.state, 'user', None)
        if not user:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        user_id = user.get('id')
        
        if not rbac_manager.has_any_permission(user_id, self.permissions):
            raise HTTPException(status_code=403, detail="Permission denied")
        
        return user


# 常用权限检查依赖
check_media_view = PermissionChecker(Permission.MEDIA_VIEW)
check_media_upload = PermissionChecker(Permission.MEDIA_UPLOAD)
check_media_delete = PermissionChecker(Permission.MEDIA_DELETE)
check_admin = PermissionChecker(Permission.ADMIN_FULL)
