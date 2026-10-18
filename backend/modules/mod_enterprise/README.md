# mod_enterprise — 企业级功能模块

## 职责

多租户支持、审计日志、高级权限控制。

## 对外接口

```python
from modules.mod_enterprise import (
    TenantManager,    # 租户管理
    AuditLogger,      # 审计日志
    tenant_manager,   # 全局租户管理器实例
    audit_logger,     # 全局审计日志实例
)
```

## TenantManager

| 方法 | 说明 |
|------|------|
| `create_tenant(id, name, config)` | 创建租户 |
| `get_tenant(id)` | 获取租户 |
| `list_tenants()` | 列出所有租户 |
| `delete_tenant(id)` | 删除租户 |

## AuditLogger

| 方法 | 说明 |
|------|------|
| `log(action, user_id, resource, details)` | 记录审计事件 |
| `query(user_id, action, limit)` | 查询审计日志 |
| `get_recent(limit)` | 获取最近记录 |

## 依赖

- `core.logger` (loguru)
