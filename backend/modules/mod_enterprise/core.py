"""
Enterprise Features - Multi-tenant and Audit Support
V7.0 Phase 1: Enterprise Module
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
from loguru import logger


class Tenant:
    """租户/组织"""
    
    def __init__(self, tenant_id: str, name: str, config: Dict = None):
        self.tenant_id = tenant_id
        self.name = name
        self.config = config or {}
        self.created_at = datetime.now()
        self.users: List[str] = []
    
    def add_user(self, user_id: str):
        """添加用户到租户"""
        if user_id not in self.users:
            self.users.append(user_id)
            logger.info(f"[Tenant] Added user {user_id} to {self.name}")
    
    def remove_user(self, user_id: str):
        """从租户移除用户"""
        if user_id in self.users:
            self.users.remove(user_id)
            logger.info(f"[Tenant] Removed user {user_id} from {self.name}")


class TenantManager:
    """租户管理器"""
    
    def __init__(self):
        self._tenants: Dict[str, Tenant] = {}
    
    def create_tenant(self, tenant_id: str, name: str, config: Dict = None) -> Tenant:
        """创建租户"""
        if tenant_id in self._tenants:
            raise ValueError(f"Tenant {tenant_id} already exists")
        
        tenant = Tenant(tenant_id, name, config)
        self._tenants[tenant_id] = tenant
        logger.info(f"[Tenant] Created: {name} ({tenant_id})")
        return tenant
    
    def get_tenant(self, tenant_id: str) -> Optional[Tenant]:
        """获取租户"""
        return self._tenants.get(tenant_id)
    
    def list_tenants(self) -> List[Tenant]:
        """列出所有租户"""
        return list(self._tenants.values())
    
    def delete_tenant(self, tenant_id: str) -> bool:
        """删除租户"""
        if tenant_id in self._tenants:
            del self._tenants[tenant_id]
            logger.info(f"[Tenant] Deleted: {tenant_id}")
            return True
        return False


class AuditEvent:
    """审计事件"""
    
    def __init__(self, action: str, user_id: str, resource: str, details: Dict = None):
        self.timestamp = datetime.now()
        self.action = action
        self.user_id = user_id
        self.resource = resource
        self.details = details or {}
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "action": self.action,
            "user_id": self.user_id,
            "resource": self.resource,
            "details": self.details,
        }


class AuditLogger:
    """审计日志记录器"""
    
    def __init__(self, max_entries: int = 10000):
        self._entries: List[AuditEvent] = []
        self._max_entries = max_entries
    
    def log(self, action: str, user_id: str, resource: str, details: Dict = None):
        """记录审计事件"""
        event = AuditEvent(action, user_id, resource, details)
        self._entries.append(event)
        
        # 限制条目数
        if len(self._entries) > self._max_entries:
            self._entries.pop(0)
        
        logger.info(f"[Audit] {action} by {user_id} on {resource}")
    
    def query(self, user_id: str = None, action: str = None, limit: int = 100) -> List[AuditEvent]:
        """查询审计日志"""
        results = self._entries
        
        if user_id:
            results = [e for e in results if e.user_id == user_id]
        if action:
            results = [e for e in results if e.action == action]
        
        return results[-limit:]
    
    def get_recent(self, limit: int = 50) -> List[Dict]:
        """获取最近的审计记录"""
        return [e.to_dict() for e in self._entries[-limit:]]


# 全局实例
tenant_manager = TenantManager()
audit_logger = AuditLogger()
