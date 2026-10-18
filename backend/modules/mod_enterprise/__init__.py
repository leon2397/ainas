"""
mod_enterprise — AI-NAS 企业级功能模块

提供：
- 多租户支持 (TenantManager)
- 审计日志 (AuditLogger)

使用方式：
    from modules.mod_enterprise import TenantManager, AuditLogger
    from modules.mod_enterprise.core import tenant_manager, audit_logger
"""

from modules.mod_enterprise.core import TenantManager, AuditLogger, tenant_manager, audit_logger

__all__ = [
    "TenantManager",
    "AuditLogger",
    "tenant_manager",
    "audit_logger",
]
