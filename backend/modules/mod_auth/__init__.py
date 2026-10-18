"""
mod_auth — AI-NAS 认证与权限模块

提供：
- JWT Token 认证
- 用户管理（数据库持久化 + 内存降级）
- 角色权限控制
- 密码加密

使用方式：
    from modules.mod_auth import AuthManager, require_auth, require_role
"""

from modules.mod_auth.service import (
    AuthManager,
    auth_manager,
    get_current_user,
    require_admin,
    require_editor,
    ROLES,
    ROLE_LEVELS,
    PERMISSION_MIN_ROLE,
)
from modules.mod_auth.crypto import ConfigCrypto, config_crypto

__all__ = [
    "AuthManager",
    "auth_manager",
    "get_current_user",
    "require_admin",
    "require_editor",
    "ROLES",
    "ROLE_LEVELS",
    "PERMISSION_MIN_ROLE",
    "ConfigCrypto",
    "config_crypto",
]
