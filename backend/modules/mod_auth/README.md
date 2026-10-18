# mod_auth — 认证与权限模块

## 职责

提供用户认证、权限管理和加密工具。

## 对外接口

```python
from modules.mod_auth import (
    AuthManager, auth_manager, get_current_user,
    require_admin, require_editor,
    ROLES, ROLE_LEVELS, PERMISSION_MIN_ROLE,
    ConfigCrypto, config_crypto,
)
```

## AuthManager 方法

| 方法 | 说明 |
|------|------|
| `set_db(db)` | 设置数据库引用（startup 时调用）|
| `authenticate_user(username, password)` | 验证用户登录 |
| `get_user(username)` | 获取用户信息 |
| `create_user(name, password, role)` | 创建用户 |
| `update_user_role(name, role)` | 更新角色 |
| `update_password(name, old, new)` | 修改密码 |
| `toggle_user(name, disabled)` | 启用/禁用 |
| `delete_user(name)` | 删除用户 |
| `create_access_token(data)` | 创建 JWT Token |
| `get_current_user(credentials)` | 获取当前用户（FastAPI Depends）|
| `check_permission(user, permission)` | 检查权限 |

## 依赖注入

```python
from fastapi import Depends
from modules.mod_auth import get_current_user, require_admin

@app.get("/api/admin")
async def admin_endpoint(user: dict = Depends(require_admin)):
    ...
```

## 角色定义

| 角色 | 权限 |
|------|------|
| admin | all |
| editor | media_read/write, album_manage, task_manage, ai_run |
| viewer | media_read, album_read |

## ConfigCrypto

配置加密工具，用于加密敏感配置：

```python
from modules.mod_auth import config_crypto

encrypted = config_crypto.encrypt("secret")
plain = config_crypto.decrypt(encrypted)
```

## 依赖

- `core.config_manager`
- `core.logger`
- `modules.mod_database`（可选，降级到内存）
