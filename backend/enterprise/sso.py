from loguru import logger
"""
Enterprise SSO Module
V6.0 Phase 4: 企业增强 - 单点登录
支持 OIDC 和 LDAP 认证
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

logger = logger.bind(name="ai_nas.enterprise.sso")

try:
    import msal
    MSAL_AVAILABLE = True
except ImportError:
    MSAL_AVAILABLE = False
    logger.warning("MSAL not available, OIDC features limited")


class SSOProvider(Enum):
    """SSO 提供商类型"""
    OIDC = "oidc"           # OpenID Connect
    LDAP = "ldap"           # LDAP Directory
    SAML = "saml"           # SAML 2.0
    AZURE_AD = "azure_ad"   # Microsoft Azure AD


class SSOStatus(Enum):
    """SSO 状态"""
    DISABLED = "disabled"
    ENABLED = "enabled"
    CONFIGURED = "configured"
    ERROR = "error"


@dataclass
class SSOConfig:
    """SSO 配置"""
    provider: SSOProvider
    status: SSOStatus
    client_id: str
    client_secret: str
    authority: str
    scopes: List[str]
    claims_mapping: Dict[str, str]
    auto_provision: bool  # 是否自动创建用户
    default_role: str
    created_at: datetime
    updated_at: datetime


@dataclass
class SSOUser:
    """SSO 用户信息"""
    sub: str              # 唯一标识符
    email: str
    name: str
    groups: List[str]
    roles: List[str]
    tenant_id: Optional[str]
    raw_claims: Dict[str, Any]


class OIDCAuthProvider:
    """OIDC 认证提供者"""
    
    def __init__(self, config: SSOConfig):
        self.config = config
        self._app = None
        self._initialized = False
    
    def initialize(self) -> bool:
        """初始化 OIDC 提供者"""
        if not MSAL_AVAILABLE:
            logger.error("MSAL library not available")
            return False
        
        try:
            self._app = msal.ConfidentialClientApplication(
                client_id=self.config.client_id,
                client_credential=self.config.client_secret,
                authority=self.config.authority
            )
            self._initialized = True
            logger.info(f"OIDC provider initialized: {self.config.authority}")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize OIDC provider: {e}")
            return False
    
    def authorize_url(self, redirect_uri: str, state: str) -> str:
        """获取授权 URL"""
        if not self._initialized:
            self.initialize()
        
        return self._app.get_authorization_request_url(
            scopes=self.config.scopes,
            redirect_uri=redirect_uri,
            state=state
        )
    
    def exchange_code(self, code: str, redirect_uri: str) -> Optional[Dict]:
        """交换授权码获取令牌"""
        if not self._initialized:
            self.initialize()
        
        try:
            result = self._app.acquire_token_by_authorization_code(
                code=code,
                scopes=self.config.scopes,
                redirect_uri=redirect_uri
            )
            return result
        except Exception as e:
            logger.error(f"Failed to exchange code: {e}")
            return None
    
    def get_user_info(self, access_token: str) -> Optional[SSOUser]:
        """获取用户信息"""
        try:
            import requests
            
            # 获取用户信息端点
            userinfo_endpoint = self.config.authority.rstrip('/') + "/openid/userinfo"
            response = requests.get(
                userinfo_endpoint,
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            if response.status_code == 200:
                claims = response.json()
                return self._map_claims(claims)
            
            return None
        except Exception as e:
            logger.error(f"Failed to get user info: {e}")
            return None
    
    def _map_claims(self, claims: Dict) -> SSOUser:
        """映射声明到用户信息"""
        mapping = self.config.claims_mapping
        
        return SSOUser(
            sub=claims.get(mapping.get("sub", "sub"), ""),
            email=claims.get(mapping.get("email", "email"), ""),
            name=claims.get(mapping.get("name", "name"), ""),
            groups=claims.get(mapping.get("groups", "groups"), []),
            roles=claims.get(mapping.get("roles", "roles"), []),
            tenant_id=claims.get(mapping.get("tenant", "tenant_id")),
            raw_claims=claims
        )


class LDAPAuthProvider:
    """LDAP 认证提供者"""
    
    def __init__(self, config: SSOConfig):
        self.config = config
        self._conn = None
        self._initialized = False
        
        # LDAP 配置
        self.server = ""
        self.port = 389
        self.use_ssl = False
        self.bind_dn = ""
        self.bind_password = ""
        self.user_dn_template = ""
        self.group_dn_template = ""
        self.search_base = ""
    
    def initialize(self) -> bool:
        """初始化 LDAP 提供者"""
        try:
            import ldap
            
            # 连接 LDAP 服务器
            ldap_uri = f"ldap{'s' if self.use_ssl else ''}://{self.server}:{self.port}"
            self._conn = ldap.initialize(ldap_uri)
            self._conn.protocol_version = ldap.VERSION3
            self._conn.set_option(ldap.OPT_REFERRALS, 0)
            
            if self.use_ssl:
                self._conn.start_tls_s()
            
            # 绑定管理员
            self._conn.simple_bind_s(self.bind_dn, self.bind_password)
            
            self._initialized = True
            logger.info(f"LDAP provider initialized: {self.server}")
            return True
            
        except ImportError:
            logger.error("python-ldap library not available")
            return False
        except Exception as e:
            logger.error(f"Failed to initialize LDAP provider: {e}")
            return False
    
    def authenticate(self, username: str, password: str) -> Optional[SSOUser]:
        """LDAP 用户认证"""
        if not self._initialized:
            self.initialize()
        
        try:
            import ldap
            
            # 构建用户 DN
            user_dn = self.user_dn_template.format(username=username)
            
            # 尝试绑定用户
            try:
                self._conn.simple_bind_s(user_dn, password)
            except ldap.INVALID_CREDENTIALS:
                return None
            
            # 搜索用户信息
            search_filter = f"(uid={username})"
            result = self._conn.search_s(
                self.search_base,
                ldap.SCOPE_SUBTREE,
                search_filter,
                ["uid", "mail", "cn", "memberOf", "displayName"]
            )
            
            if not result:
                return None
            
            dn, attrs = result[0]
            return self._map_attributes(dn, attrs)
            
        except Exception as e:
            logger.error(f"LDAP authentication failed: {e}")
            return None
    
    def search_users(self, filter_str: str = "(objectClass=person)") -> List[SSOUser]:
        """搜索 LDAP 用户"""
        if not self._initialized:
            self.initialize()
        
        try:
            import ldap
            
            result = self._conn.search_s(
                self.search_base,
                ldap.SCOPE_SUBTREE,
                filter_str,
                ["uid", "mail", "cn", "memberOf", "displayName"]
            )
            
            return [
                self._map_attributes(dn, attrs) 
                for dn, attrs in result
            ]
        except Exception as e:
            logger.error(f"LDAP search failed: {e}")
            return []
    
    def _map_attributes(self, dn: str, attrs: Dict) -> SSOUser:
        """映射 LDAP 属性到用户信息"""
        def get_first(key):
            val = attrs.get(key, [])
            return val[0].decode() if val else ""
        
        def get_list(key):
            return [v.decode() for v in attrs.get(key, [])]
        
        # 解析组成员关系
        groups = []
        for group_dn in get_list("memberOf"):
            if "cn=" in group_dn:
                cn = group_dn.split(",")[0].replace("cn=", "")
                groups.append(cn)
        
        return SSOUser(
            sub=get_first("uid") or dn,
            email=get_first("mail"),
            name=get_first("displayName") or get_first("cn"),
            groups=groups,
            roles=groups,  # 使用组作为角色
            tenant_id=None,
            raw_claims=attrs
        )


class SSOManager:
    """SSO 管理器"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self.config: Optional[SSOConfig] = None
        self._oidc_provider: Optional[OIDCAuthProvider] = None
        self._ldap_provider: Optional[LDAPAuthProvider] = None
    
    def configure(self, provider_type: SSOProvider, config_data: Dict) -> bool:
        """配置 SSO"""
        try:
            self.config = SSOConfig(
                provider=provider_type,
                status=SSOStatus.CONFIGURED,
                client_id=config_data.get("client_id", ""),
                client_secret=config_data.get("client_secret", ""),
                authority=config_data.get("authority", ""),
                scopes=config_data.get("scopes", ["openid", "profile", "email"]),
                claims_mapping=config_data.get("claims_mapping", {
                    "sub": "sub",
                    "email": "email",
                    "name": "name",
                    "groups": "groups",
                    "roles": "roles"
                }),
                auto_provision=config_data.get("auto_provision", True),
                default_role=config_data.get("default_role", "viewer"),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            # 根据类型初始化提供者
            if provider_type in [SSOProvider.OIDC, SSOProvider.AZURE_AD]:
                self._oidc_provider = OIDCAuthProvider(self.config)
                return self._oidc_provider.initialize()
            elif provider_type == SSOProvider.LDAP:
                self._ldap_provider = LDAPAuthProvider(self.config)
                return self._ldap_provider.initialize()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to configure SSO: {e}")
            return False
    
    def enable(self) -> bool:
        """启用 SSO"""
        if not self.config:
            return False
        
        self.config.status = SSOStatus.ENABLED
        return True
    
    def disable(self) -> bool:
        """禁用 SSO"""
        if not self.config:
            return False
        
        self.config.status = SSOStatus.DISABLED
        return True
    
    def authenticate(self, username: str, password: str) -> Optional[SSOUser]:
        """认证用户"""
        if not self.config or self.config.status != SSOStatus.ENABLED:
            return None
        
        if self._ldap_provider:
            return self._ldap_provider.authenticate(username, password)
        
        return None
    
    def handle_oidc_callback(self, code: str, redirect_uri: str) -> Optional[SSOUser]:
        """处理 OIDC 回调"""
        if not self._oidc_provider:
            return None
        
        result = self._oidc_provider.exchange_code(code, redirect_uri)
        if result and "access_token" in result:
            return self._oidc_provider.get_user_info(result["access_token"])
        
        return None
    
    def provision_user(self, sso_user: SSOUser) -> str:
        """自动创建用户"""
        # 这里应该调用用户服务创建用户
        # 返回用户ID
        return sso_user.sub
    
    def get_status(self) -> Dict:
        """获取 SSO 状态"""
        if not self.config:
            return {
                "enabled": False,
                "provider": None,
                "status": "not_configured"
            }
        
        return {
            "enabled": self.config.status == SSOStatus.ENABLED,
            "provider": self.config.provider.value,
            "status": self.config.status.value,
            "auto_provision": self.config.auto_provision,
            "default_role": self.config.default_role
        }


# 全局实例
sso_manager = SSOManager()


def get_sso_manager() -> SSOManager:
    """获取 SSO 管理器"""
    return sso_manager
