# core/auth.py — forwarding shim (deprecated)
#
# Migrated to modules.mod_auth.service
# This file forwards all exports for backward compatibility.
#
# Update your import to:
#   from modules.mod_auth import AuthManager, auth_manager, get_current_user

import warnings
warnings.warn(
    "core.auth is deprecated, use 'from modules.mod_auth import AuthManager, auth_manager'",
    DeprecationWarning,
    stacklevel=2,
)

from modules.mod_auth.service import (
    AuthManager,
    auth_manager,
    get_current_user,
    require_admin,
    require_editor,
    ROLES,
    ROLE_LEVELS,
    PERMISSION_MIN_ROLE,
    SECRET_KEY,
    ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    security,
)

__all__ = [
    "AuthManager",
    "auth_manager",
    "get_current_user",
    "require_admin",
    "require_editor",
    "ROLES",
    "ROLE_LEVELS",
    "PERMISSION_MIN_ROLE",
    "SECRET_KEY",
    "ALGORITHM",
    "ACCESS_TOKEN_EXPIRE_MINUTES",
    "security",
]
