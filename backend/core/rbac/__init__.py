"""
RBAC 初始化模块
"""

from .manager import RBACManager, rbac_manager, Role, Permission
from .decorators import (
    require_permission, require_any_permission, require_all_permissions,
    PermissionChecker, AnyPermissionChecker,
    check_media_view, check_media_upload, check_media_delete, check_admin
)

__all__ = [
    'RBACManager',
    'rbac_manager',
    'Role',
    'Permission',
    'require_permission',
    'require_any_permission',
    'require_all_permissions',
    'PermissionChecker',
    'AnyPermissionChecker',
    'check_media_view',
    'check_media_upload',
    'check_media_delete',
    'check_admin',
]
