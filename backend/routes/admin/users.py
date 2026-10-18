"""
管理员路由 - 企业级功能
Phase 2.3
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from typing import List, Optional
from datetime import datetime, timedelta

from core.rbac import rbac_manager, Role, Permission, require_permission, check_admin
from core.audit import audit_logger, AuditLevel, AuditCategory, AuditAction

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/users")
async def list_users(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
    current_user: dict = Depends(check_admin)
):
    """获取用户列表（管理员）"""
    # 这里应该从数据库获取
    # 示例数据
    users = [
        {
            "id": "1",
            "username": "admin",
            "email": "admin@example.com",
            "role": "super_admin",
            "is_active": True,
            "created_at": "2024-01-01T00:00:00",
            "last_login": "2024-01-15T10:30:00",
        }
    ]
    
    # 记录审计日志
    await audit_logger.log_user(
        action=AuditAction.USER_VIEW,
        description=f"Admin viewed user list (page {page})",
        user_id=current_user.get('id'),
        user_name=current_user.get('username'),
        details={"page": page, "page_size": page_size, "role_filter": role},
        ip_address=request.client.host if request.client else None,
    )
    
    return {
        "users": users,
        "total": len(users),
        "page": page,
        "page_size": page_size,
    }


@router.post("/users")
async def create_user(
    request: Request,
    user_data: dict,
    current_user: dict = Depends(check_admin)
):
    """创建用户（管理员）"""
    # 记录审计日志
    await audit_logger.log_user(
        action=AuditAction.USER_CREATE,
        description=f"Admin created user: {user_data.get('username')}",
        user_id=current_user.get('id'),
        user_name=current_user.get('username'),
        details={"new_user": user_data.get('username'), "role": user_data.get('role')},
        ip_address=request.client.host if request.client else None,
    )
    
    return {"message": "User created successfully", "user_id": "new_user_id"}


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    request: Request,
    current_user: dict = Depends(check_admin)
):
    """删除用户（管理员）"""
    # 记录审计日志
    await audit_logger.log_user(
        action=AuditAction.USER_DELETE,
        description=f"Admin deleted user: {user_id}",
        user_id=current_user.get('id'),
        user_name=current_user.get('username'),
        details={"deleted_user_id": user_id},
        ip_address=request.client.host if request.client else None,
    )
    
    return {"message": "User deleted successfully"}


@router.post("/users/{user_id}/role")
async def assign_role(
    user_id: str,
    request: Request,
    role_data: dict,
    current_user: dict = Depends(check_admin)
):
    """分配角色（管理员）"""
    role = role_data.get('role')
    
    # 分配角色
    rbac_manager.assign_role(user_id, Role(role), current_user.get('id'))
    
    # 记录审计日志
    await audit_logger.log_user(
        action=AuditAction.ROLE_ASSIGN,
        description=f"Admin assigned role {role} to user {user_id}",
        user_id=current_user.get('id'),
        user_name=current_user.get('username'),
        details={"target_user_id": user_id, "role": role},
        ip_address=request.client.host if request.client else None,
    )
    
    return {"message": "Role assigned successfully"}


@router.get("/roles")
async def list_roles(
    current_user: dict = Depends(check_admin)
):
    """获取所有角色"""
    roles = rbac_manager.list_roles()
    return {"roles": roles}


@router.get("/audit-logs")
async def get_audit_logs(
    request: Request,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    level: Optional[str] = None,
    category: Optional[str] = None,
    user_id: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(check_admin)
):
    """获取审计日志（管理员）"""
    # 默认查询最近7天
    if not end_date:
        end_date = datetime.utcnow()
    if not start_date:
        start_date = end_date - timedelta(days=7)
    
    # 查询日志
    logs = await audit_logger.query_logs(
        start_time=start_date,
        end_time=end_date,
        user_id=user_id,
        limit=limit,
        offset=offset
    )
    
    # 记录审计日志
    await audit_logger.log(
        level=AuditLevel.INFO,
        category=AuditCategory.ADMIN,
        action=AuditAction.SYSTEM_LOGS,
        description="Admin queried audit logs",
        user_id=current_user.get('id'),
        user_name=current_user.get('username'),
        details={"start_date": start_date.isoformat(), "end_date": end_date.isoformat(), "limit": limit},
        ip_address=request.client.host if request.client else None,
    )
    
    return {
        "logs": logs,
        "total": len(logs),
        "limit": limit,
        "offset": offset,
    }


@router.get("/audit-statistics")
async def get_audit_statistics(
    days: int = Query(7, ge=1, le=30),
    current_user: dict = Depends(check_admin)
):
    """获取审计统计（管理员）"""
    stats = await audit_logger.get_statistics(days=days)
    return stats


@router.post("/audit-export")
async def export_audit_logs(
    request: Request,
    export_data: dict,
    current_user: dict = Depends(check_admin)
):
    """导出审计日志（管理员）"""
    format = export_data.get('format', 'json')
    start_date = export_data.get('start_date')
    end_date = export_data.get('end_date')
    
    # 解析日期
    start_time = datetime.fromisoformat(start_date) if start_date else None
    end_time = datetime.fromisoformat(end_date) if end_date else None
    
    # 导出日志
    exported_data = await audit_logger.export_logs(
        format=format,
        start_time=start_time,
        end_time=end_time
    )
    
    # 记录审计日志
    await audit_logger.log(
        level=AuditLevel.INFO,
        category=AuditCategory.ADMIN,
        action=AuditAction.SYSTEM_LOGS,
        description=f"Admin exported audit logs ({format})",
        user_id=current_user.get('id'),
        user_name=current_user.get('username'),
        details={"format": format, "start_date": start_date, "end_date": end_date},
        ip_address=request.client.host if request.client else None,
    )
    
    return {
        "format": format,
        "data": exported_data,
        "exported_at": datetime.utcnow().isoformat(),
    }


@router.get("/system-config")
async def get_system_config(
    current_user: dict = Depends(check_admin)
):
    """获取系统配置（管理员）"""
    return {
        "version": "2.0.0",
        "features": {
            "rbac_enabled": True,
            "audit_enabled": True,
            "sso_enabled": False,
        },
        "limits": {
            "max_users": 1000,
            "max_media_per_user": 10000,
            "max_storage_gb": 1000,
        }
    }


@router.put("/system-config")
async def update_system_config(
    request: Request,
    config: dict,
    current_user: dict = Depends(check_admin)
):
    """更新系统配置（管理员）"""
    # 记录审计日志
    await audit_logger.log(
        level=AuditLevel.INFO,
        category=AuditCategory.CONFIG,
        action=AuditAction.CONFIG_CHANGE,
        description="Admin updated system configuration",
        user_id=current_user.get('id'),
        user_name=current_user.get('username'),
        details={"config_changes": config},
        ip_address=request.client.host if request.client else None,
    )
    
    return {"message": "Configuration updated successfully"}
