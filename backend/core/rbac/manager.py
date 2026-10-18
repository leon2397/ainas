"""
RBAC (Role-Based Access Control) 权限管理系统
企业级功能 - Phase 2.1
"""

from enum import Enum
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
import json


class Permission(str, Enum):
    """系统权限定义"""
    # 媒体管理权限
    MEDIA_VIEW = "media:view"
    MEDIA_UPLOAD = "media:upload"
    MEDIA_DELETE = "media:delete"
    MEDIA_EDIT = "media:edit"
    MEDIA_DOWNLOAD = "media:download"
    MEDIA_SHARE = "media:share"
    
    # 相册管理权限
    ALBUM_VIEW = "album:view"
    ALBUM_CREATE = "album:create"
    ALBUM_DELETE = "album:delete"
    ALBUM_EDIT = "album:edit"
    ALBUM_SHARE = "album:share"
    
    # 设备管理权限
    DEVICE_VIEW = "device:view"
    DEVICE_CONTROL = "device:control"
    DEVICE_CONFIG = "device:config"
    
    # 用户管理权限
    USER_VIEW = "user:view"
    USER_CREATE = "user:create"
    USER_DELETE = "user:delete"
    USER_EDIT = "user:edit"
    
    # 系统管理权限
    SYSTEM_CONFIG = "system:config"
    SYSTEM_LOGS = "system:logs"
    SYSTEM_BACKUP = "system:backup"
    SYSTEM_UPDATE = "system:update"
    
    # 审计权限
    AUDIT_VIEW = "audit:view"
    AUDIT_EXPORT = "audit:export"
    
    # 管理员权限
    ADMIN_FULL = "admin:full"


class Role(str, Enum):
    """系统角色定义"""
    SUPER_ADMIN = "super_admin"      # 超级管理员
    ADMIN = "admin"                   # 管理员
    OPERATOR = "operator"             # 操作员
    VIEWER = "viewer"                 # 查看者
    GUEST = "guest"                   # 访客


# 角色权限映射
ROLE_PERMISSIONS: Dict[Role, Set[Permission]] = {
    Role.SUPER_ADMIN: set(Permission),  # 所有权限
    
    Role.ADMIN: {
        Permission.MEDIA_VIEW, Permission.MEDIA_UPLOAD, Permission.MEDIA_DELETE,
        Permission.MEDIA_EDIT, Permission.MEDIA_DOWNLOAD, Permission.MEDIA_SHARE,
        Permission.ALBUM_VIEW, Permission.ALBUM_CREATE, Permission.ALBUM_DELETE,
        Permission.ALBUM_EDIT, Permission.ALBUM_SHARE,
        Permission.DEVICE_VIEW, Permission.DEVICE_CONTROL, Permission.DEVICE_CONFIG,
        Permission.USER_VIEW, Permission.USER_CREATE, Permission.USER_EDIT,
        Permission.SYSTEM_CONFIG, Permission.SYSTEM_LOGS, Permission.SYSTEM_BACKUP,
        Permission.AUDIT_VIEW, Permission.AUDIT_EXPORT,
    },
    
    Role.OPERATOR: {
        Permission.MEDIA_VIEW, Permission.MEDIA_UPLOAD, Permission.MEDIA_EDIT,
        Permission.MEDIA_DOWNLOAD, Permission.MEDIA_SHARE,
        Permission.ALBUM_VIEW, Permission.ALBUM_CREATE, Permission.ALBUM_EDIT,
        Permission.ALBUM_SHARE,
        Permission.DEVICE_VIEW, Permission.DEVICE_CONTROL,
    },
    
    Role.VIEWER: {
        Permission.MEDIA_VIEW, Permission.MEDIA_DOWNLOAD,
        Permission.ALBUM_VIEW,
        Permission.DEVICE_VIEW,
    },
    
    Role.GUEST: {
        Permission.MEDIA_VIEW,
        Permission.ALBUM_VIEW,
    },
}


@dataclass
class UserRole:
    """用户角色关联"""
    user_id: str
    role: Role
    assigned_by: str
    assigned_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    is_active: bool = True


@dataclass
class CustomRole:
    """自定义角色"""
    id: str
    name: str
    description: str
    permissions: Set[Permission]
    created_by: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    is_active: bool = True


class RBACManager:
    """RBAC 权限管理器"""
    
    def __init__(self, db=None):
        self.db = db
        self._user_roles: Dict[str, UserRole] = {}
        self._custom_roles: Dict[str, CustomRole] = {}
    
    def assign_role(self, user_id: str, role: Role, assigned_by: str) -> UserRole:
        """为用户分配角色"""
        user_role = UserRole(
            user_id=user_id,
            role=role,
            assigned_by=assigned_by
        )
        self._user_roles[user_id] = user_role
        return user_role
    
    def revoke_role(self, user_id: str) -> bool:
        """撤销用户角色"""
        if user_id in self._user_roles:
            self._user_roles[user_id].is_active = False
            return True
        return False
    
    def get_user_role(self, user_id: str) -> Optional[Role]:
        """获取用户角色"""
        user_role = self._user_roles.get(user_id)
        if user_role and user_role.is_active:
            return user_role.role
        return None
    
    def get_user_permissions(self, user_id: str) -> Set[Permission]:
        """获取用户权限集合"""
        role = self.get_user_role(user_id)
        if not role:
            return set()
        return ROLE_PERMISSIONS.get(role, set()).copy()
    
    def has_permission(self, user_id: str, permission: Permission) -> bool:
        """检查用户是否有特定权限"""
        permissions = self.get_user_permissions(user_id)
        return permission in permissions or Permission.ADMIN_FULL in permissions
    
    def has_any_permission(self, user_id: str, permissions: List[Permission]) -> bool:
        """检查用户是否有任一权限"""
        user_perms = self.get_user_permissions(user_id)
        return any(p in user_perms for p in permissions) or Permission.ADMIN_FULL in user_perms
    
    def has_all_permissions(self, user_id: str, permissions: List[Permission]) -> bool:
        """检查用户是否有所有权限"""
        user_perms = self.get_user_permissions(user_id)
        return all(p in user_perms for p in permissions) or Permission.ADMIN_FULL in user_perms
    
    def create_custom_role(self, name: str, description: str, 
                          permissions: List[Permission], created_by: str) -> CustomRole:
        """创建自定义角色"""
        import uuid
        role_id = str(uuid.uuid4())
        custom_role = CustomRole(
            id=role_id,
            name=name,
            description=description,
            permissions=set(permissions),
            created_by=created_by
        )
        self._custom_roles[role_id] = custom_role
        return custom_role
    
    def get_role_permissions(self, role: Role) -> List[str]:
        """获取角色的权限列表"""
        perms = ROLE_PERMISSIONS.get(role, set())
        return sorted([p.value for p in perms])
    
    def list_roles(self) -> List[Dict]:
        """列出所有系统角色"""
        roles = []
        for role in Role:
            roles.append({
                "id": role.value,
                "name": role.value.replace("_", " ").title(),
                "permissions": self.get_role_permissions(role),
                "is_system": True
            })
        return roles
    
    def check_resource_access(self, user_id: str, resource_type: str, 
                             resource_id: str, action: str) -> bool:
        """检查用户对资源的访问权限"""
        # 将 action 映射到 Permission
        action_map = {
            "view": Permission.MEDIA_VIEW,
            "upload": Permission.MEDIA_UPLOAD,
            "delete": Permission.MEDIA_DELETE,
            "edit": Permission.MEDIA_EDIT,
            "download": Permission.MEDIA_DOWNLOAD,
            "share": Permission.MEDIA_SHARE,
        }
        
        permission = action_map.get(action)
        if not permission:
            return False
        
        return self.has_permission(user_id, permission)


# 全局 RBAC 实例
rbac_manager = RBACManager()
