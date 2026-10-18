from loguru import logger
"""
Multi-Tenant Module
V6.0 Phase 4: 企业增强 - 多租户支持
支持租户隔离和数据分离
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from contextvars import ContextVar
from contextlib import contextmanager

logger = logger.bind(name="ai_nas.enterprise.multitenant")

# 租户上下文变量
tenant_context: ContextVar[Optional[str]] = ContextVar("tenant_id", default=None)


class TenantStatus(Enum):
    """租户状态"""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DELETED = "deleted"
    TRIAL = "trial"


@dataclass
class Tenant:
    """租户"""
    id: str
    name: str
    slug: str
    status: TenantStatus
    plan: str  # free, basic, pro, enterprise
    settings: Dict[str, Any] = field(default_factory=dict)
    storage_quota_gb: int = 100
    user_quota: int = 10
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "status": self.status.value,
            "plan": self.plan,
            "settings": self.settings,
            "storage_quota_gb": self.storage_quota_gb,
            "user_quota": self.user_quota,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None
        }


@dataclass
class TenantConfig:
    """租户配置"""
    tenant_id: str
    features: Dict[str, bool] = field(default_factory=dict)
    limits: Dict[str, int] = field(default_factory=dict)
    branding: Dict[str, str] = field(default_factory=dict)
    custom_domain: Optional[str] = None
    
    # 功能开关
    enable_ai: bool = True
    enable_cloud_sync: bool = False
    enable_plugins: bool = False
    enable_sso: bool = False
    enable_audit_export: bool = False
    
    # 限制
    max_media_files: int = 10000
    max_albums: int = 100
    max_devices: int = 5
    max_api_calls_per_day: int = 1000


class TenantContext:
    """租户上下文管理器"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._tenants: Dict[str, Tenant] = {}
            cls._instance._configs: Dict[str, TenantConfig] = {}
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self._load_tenants()
    
    def _load_tenants(self):
        """加载租户数据"""
        tenants_file = "data/tenants/tenants.json"
        os.makedirs(os.path.dirname(tenants_file), exist_ok=True)
        
        if os.path.exists(tenants_file):
            try:
                with open(tenants_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for tenant_data in data:
                        tenant = Tenant(
                            id=tenant_data["id"],
                            name=tenant_data["name"],
                            slug=tenant_data["slug"],
                            status=TenantStatus(tenant_data["status"]),
                            plan=tenant_data["plan"],
                            settings=tenant_data.get("settings", {}),
                            storage_quota_gb=tenant_data.get("storage_quota_gb", 100),
                            user_quota=tenant_data.get("user_quota", 10),
                            created_at=datetime.fromisoformat(tenant_data.get("created_at", datetime.utcnow().isoformat())),
                            updated_at=datetime.fromisoformat(tenant_data.get("updated_at", datetime.utcnow().isoformat()))
                        )
                        self._tenants[tenant.id] = tenant
                        
                        # 加载配置
                        self._configs[tenant.id] = TenantConfig(
                            tenant_id=tenant.id,
                            features=tenant_data.get("features", {}),
                            limits=tenant_data.get("limits", {}),
                            branding=tenant_data.get("branding", {}),
                            custom_domain=tenant_data.get("custom_domain")
                        )
                logger.info(f"Loaded {len(self._tenants)} tenants")
            except Exception as e:
                logger.error(f"Failed to load tenants: {e}")
    
    def _save_tenants(self):
        """保存租户数据"""
        tenants_file = "data/tenants/tenants.json"
        os.makedirs(os.path.dirname(tenants_file), exist_ok=True)
        
        data = []
        for tenant in self._tenants.values():
            tenant_dict = tenant.to_dict()
            if tenant.id in self._configs:
                config = self._configs[tenant.id]
                tenant_dict["features"] = {
                    "enable_ai": config.enable_ai,
                    "enable_cloud_sync": config.enable_cloud_sync,
                    "enable_plugins": config.enable_plugins,
                    "enable_sso": config.enable_sso,
                    "enable_audit_export": config.enable_audit_export,
                    **config.features
                }
                tenant_dict["limits"] = {
                    "max_media_files": config.max_media_files,
                    "max_albums": config.max_albums,
                    "max_devices": config.max_devices,
                    "max_api_calls_per_day": config.max_api_calls_per_day,
                    **config.limits
                }
                tenant_dict["branding"] = config.branding
                tenant_dict["custom_domain"] = config.custom_domain
            data.append(tenant_dict)
        
        with open(tenants_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    @contextmanager
    def current_tenant(self, tenant_id: str):
        """设置当前租户上下文"""
        token = tenant_context.set(tenant_id)
        try:
            yield self._tenants.get(tenant_id)
        finally:
            tenant_context.reset(token)
    
    def get_current_tenant_id(self) -> Optional[str]:
        """获取当前租户ID"""
        return tenant_context.get()
    
    def get_current_tenant(self) -> Optional[Tenant]:
        """获取当前租户"""
        tenant_id = self.get_current_tenant_id()
        return self._tenants.get(tenant_id) if tenant_id else None
    
    def get_current_config(self) -> Optional[TenantConfig]:
        """获取当前租户配置"""
        tenant_id = self.get_current_tenant_id()
        return self._configs.get(tenant_id) if tenant_id else None
    
    def create_tenant(self, name: str, slug: str, plan: str = "free") -> Tenant:
        """创建租户"""
        import uuid
        
        tenant = Tenant(
            id=str(uuid.uuid4()),
            name=name,
            slug=slug,
            status=TenantStatus.ACTIVE,
            plan=plan,
            settings={}
        )
        
        self._tenants[tenant.id] = tenant
        
        # 创建默认配置
        config = TenantConfig(tenant_id=tenant.id)
        if plan == "free":
            config.max_media_files = 1000
            config.max_albums = 10
            config.max_devices = 1
        elif plan == "basic":
            config.max_media_files = 10000
            config.max_albums = 100
            config.max_devices = 5
        elif plan == "pro":
            config.enable_cloud_sync = True
            config.enable_plugins = True
        elif plan == "enterprise":
            config.enable_ai = True
            config.enable_cloud_sync = True
            config.enable_plugins = True
            config.enable_sso = True
            config.enable_audit_export = True
        
        self._configs[tenant.id] = config
        self._save_tenants()
        
        logger.info(f"Created tenant: {name} ({tenant.id})")
        return tenant
    
    def update_tenant(self, tenant_id: str, data: Dict) -> bool:
        """更新租户"""
        tenant = self._tenants.get(tenant_id)
        if not tenant:
            return False
        
        if "name" in data:
            tenant.name = data["name"]
        if "status" in data:
            tenant.status = TenantStatus(data["status"])
        if "plan" in data:
            tenant.plan = data["plan"]
        if "settings" in data:
            tenant.settings = data["settings"]
        
        tenant.updated_at = datetime.utcnow()
        self._save_tenants()
        
        return True
    
    def delete_tenant(self, tenant_id: str) -> bool:
        """删除租户"""
        if tenant_id in self._tenants:
            self._tenants[tenant_id].status = TenantStatus.DELETED
            self._save_tenants()
            return True
        return False
    
    def get_tenant(self, tenant_id: str) -> Optional[Tenant]:
        """获取租户"""
        return self._tenants.get(tenant_id)
    
    def get_tenant_by_slug(self, slug: str) -> Optional[Tenant]:
        """通过 slug 获取租户"""
        for tenant in self._tenants.values():
            if tenant.slug == slug:
                return tenant
        return None
    
    def list_tenants(self, status: Optional[TenantStatus] = None) -> List[Tenant]:
        """列出租户"""
        if status:
            return [t for t in self._tenants.values() if t.status == status]
        return list(self._tenants.values())
    
    def update_config(self, tenant_id: str, config_data: Dict) -> bool:
        """更新租户配置"""
        config = self._configs.get(tenant_id)
        if not config:
            return False
        
        # 更新功能开关
        if "features" in config_data:
            for key, value in config_data["features"].items():
                if hasattr(config, key):
                    setattr(config, key, value)
                else:
                    config.features[key] = value
        
        # 更新限制
        if "limits" in config_data:
            for key, value in config_data["limits"].items():
                if hasattr(config, key):
                    setattr(config, key, value)
                else:
                    config.limits[key] = value
        
        # 更新品牌
        if "branding" in config_data:
            config.branding = config_data["branding"]
        
        if "custom_domain" in config_data:
            config.custom_domain = config_data["custom_domain"]
        
        self._save_tenants()
        return True
    
    def check_quota(self, tenant_id: str, resource: str, current: int) -> bool:
        """检查配额"""
        config = self._configs.get(tenant_id)
        if not config:
            return True
        
        limits = {
            "media_files": config.max_media_files,
            "albums": config.max_albums,
            "devices": config.max_devices,
            "api_calls": config.max_api_calls_per_day
        }
        
        limit = limits.get(resource, float('inf'))
        return current < limit


class TenantAwareService:
    """租户感知服务基类"""
    
    def __init__(self):
        self.context = TenantContext()
    
    def _get_tenant_id(self) -> Optional[str]:
        """获取当前租户ID"""
        return self.context.get_current_tenant_id()
    
    def _filter_by_tenant(self, data: List[Dict]) -> List[Dict]:
        """按租户过滤数据"""
        tenant_id = self._get_tenant_id()
        if not tenant_id:
            return data
        
        return [item for item in data if item.get("tenant_id") == tenant_id]
    
    def _add_tenant_id(self, data: Dict) -> Dict:
        """添加租户ID到数据"""
        tenant_id = self._get_tenant_id()
        if tenant_id:
            data["tenant_id"] = tenant_id
        return data


# 全局实例
tenant_context_manager = TenantContext()


def get_tenant_context() -> TenantContext:
    """获取租户上下文"""
    return tenant_context_manager
