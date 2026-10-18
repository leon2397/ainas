"""
分享保护服务
支持密码保护、限时分享、私密分享
"""

import os
import json
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict
from enum import Enum
from loguru import logger


class ShareType(str, Enum):
    """分享类型"""
    PUBLIC = "public"       # 公开分享
    PASSWORD = "password"   # 密码保护
    TIMED = "timed"         # 限时分享
    ONETIME = "onetime"     # 一次性链接
    PRIVATE = "private"     # 私密分享（仅登录用户）


class ShareStatus(str, Enum):
    """分享状态"""
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    DEPLETED = "depleted"   # 一次性链接已用完


@dataclass
class ShareLink:
    """分享链接"""
    share_id: str
    share_code: str           # 短链接码
    share_type: ShareType
    resource_type: str        # media / album
    resource_ids: List[int]   # 资源ID列表
    password_hash: Optional[str] = None
    expire_at: Optional[datetime] = None
    max_views: Optional[int] = None
    current_views: int = 0
    allowed_users: List[int] = None  # 允许访问的用户ID
    created_by: int = 0
    created_at: datetime = None
    status: ShareStatus = ShareStatus.ACTIVE
    
    def __post_init__(self):
        if self.allowed_users is None:
            self.allowed_users = []
        if self.created_at is None:
            self.created_at = datetime.now()
    
    def to_dict(self) -> dict:
        data = asdict(self)
        data['share_type'] = self.share_type.value
        data['status'] = self.status.value
        if self.expire_at:
            data['expire_at'] = self.expire_at.isoformat()
        if self.created_at:
            data['created_at'] = self.created_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ShareLink':
        data = data.copy()
        data['share_type'] = ShareType(data['share_type'])
        data['status'] = ShareStatus(data['status'])
        if data.get('expire_at'):
            data['expire_at'] = datetime.fromisoformat(data['expire_at'])
        if data.get('created_at'):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        return cls(**data)


class ShareProtectionService:
    """分享保护服务"""
    
    CODE_LENGTH = 8  # 短链接码长度
    
    def __init__(self, storage_path: str = "./data/shares"):
        self.storage_path = storage_path
        os.makedirs(storage_path, exist_ok=True)
        self.shares_file = os.path.join(storage_path, "shares.json")
        self._shares: Dict[str, ShareLink] = {}
        self._load_shares()
    
    def _load_shares(self):
        """加载分享数据"""
        if os.path.exists(self.shares_file):
            try:
                with open(self.shares_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for share_id, share_data in data.items():
                        self._shares[share_id] = ShareLink.from_dict(share_data)
            except Exception as e:
                logger.info(f"加载分享数据失败: {e}")
    
    def _save_shares(self):
        """保存分享数据"""
        data = {sid: share.to_dict() for sid, share in self._shares.items()}
        with open(self.shares_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _generate_code(self) -> str:
        """生成短链接码"""
        return secrets.token_urlsafe(self.CODE_LENGTH)[:self.CODE_LENGTH]
    
    def _hash_password(self, password: str) -> str:
        """哈希密码"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def create_share(
        self,
        resource_type: str,
        resource_ids: List[int],
        share_type: ShareType = ShareType.PUBLIC,
        password: Optional[str] = None,
        expire_hours: Optional[int] = None,
        max_views: Optional[int] = None,
        allowed_users: Optional[List[int]] = None,
        created_by: int = 0
    ) -> ShareLink:
        """
        创建分享链接
        
        Args:
            resource_type: 资源类型 (media / album)
            resource_ids: 资源ID列表
            share_type: 分享类型
            password: 密码（密码保护时必需）
            expire_hours: 过期时长（小时）
            max_views: 最大访问次数（一次性链接时为1）
            allowed_users: 允许访问的用户ID列表
            created_by: 创建者用户ID
            
        Returns:
            ShareLink 对象
        """
        share_id = secrets.token_urlsafe(16)
        share_code = self._generate_code()
        
        # 密码处理
        password_hash = None
        if share_type == ShareType.PASSWORD and password:
            password_hash = self._hash_password(password)
        
        # 过期时间
        expire_at = None
        if expire_hours:
            expire_at = datetime.now() + timedelta(hours=expire_hours)
        
        # 一次性链接
        if share_type == ShareType.ONETIME:
            max_views = 1
        
        share = ShareLink(
            share_id=share_id,
            share_code=share_code,
            share_type=share_type,
            resource_type=resource_type,
            resource_ids=resource_ids,
            password_hash=password_hash,
            expire_at=expire_at,
            max_views=max_views,
            allowed_users=allowed_users or [],
            created_by=created_by
        )
        
        self._shares[share_id] = share
        self._save_shares()
        
        return share
    
    def get_share(self, share_code: str) -> Optional[ShareLink]:
        """通过分享码获取分享链接"""
        for share in self._shares.values():
            if share.share_code == share_code:
                return share
        return None
    
    def get_share_by_id(self, share_id: str) -> Optional[ShareLink]:
        """通过ID获取分享链接"""
        return self._shares.get(share_id)
    
    def verify_access(
        self,
        share_code: str,
        password: Optional[str] = None,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        验证访问权限
        
        Args:
            share_code: 分享码
            password: 密码
            user_id: 用户ID
            
        Returns:
            验证结果
        """
        share = self.get_share(share_code)
        
        if not share:
            return {"valid": False, "error": "分享链接不存在"}
        
        # 检查状态
        if share.status != ShareStatus.ACTIVE:
            return {"valid": False, "error": "分享链接已失效"}
        
        # 检查过期
        if share.expire_at and datetime.now() > share.expire_at:
            share.status = ShareStatus.EXPIRED
            self._save_shares()
            return {"valid": False, "error": "分享链接已过期"}
        
        # 检查访问次数
        if share.max_views and share.current_views >= share.max_views:
            share.status = ShareStatus.DEPLETED
            self._save_shares()
            return {"valid": False, "error": "分享链接已被访问完毕"}
        
        # 验证密码
        if share.share_type == ShareType.PASSWORD:
            if not password:
                return {"valid": False, "need_password": True, "error": "需要密码访问"}
            if self._hash_password(password) != share.password_hash:
                return {"valid": False, "need_password": True, "error": "密码错误"}
        
        # 验证私密分享
        if share.share_type == ShareType.PRIVATE:
            if not user_id:
                return {"valid": False, "need_login": True, "error": "需要登录访问"}
            if user_id not in share.allowed_users:
                return {"valid": False, "error": "无权访问"}
        
        # 访问次数+1
        share.current_views += 1
        self._save_shares()
        
        return {
            "valid": True,
            "share": share.to_dict()
        }
    
    def revoke_share(self, share_id: str) -> bool:
        """撤销分享链接"""
        share = self._shares.get(share_id)
        if not share:
            return False
        
        share.status = ShareStatus.REVOKED
        self._save_shares()
        return True
    
    def delete_share(self, share_id: str) -> bool:
        """删除分享链接"""
        if share_id in self._shares:
            del self._shares[share_id]
            self._save_shares()
            return True
        return False
    
    def list_shares(
        self,
        user_id: Optional[int] = None,
        resource_type: Optional[str] = None,
        status: Optional[ShareStatus] = None
    ) -> List[ShareLink]:
        """列出分享链接"""
        shares = list(self._shares.values())
        
        if user_id:
            shares = [s for s in shares if s.created_by == user_id]
        if resource_type:
            shares = [s for s in shares if s.resource_type == resource_type]
        if status:
            shares = [s for s in shares if s.status == status]
        
        return sorted(shares, key=lambda x: x.created_at, reverse=True)
    
    def update_share(
        self,
        share_id: str,
        password: Optional[str] = None,
        expire_hours: Optional[int] = None,
        max_views: Optional[int] = None
    ) -> Optional[ShareLink]:
        """更新分享设置"""
        share = self._shares.get(share_id)
        if not share:
            return None
        
        if password is not None:
            share.password_hash = self._hash_password(password)
            share.share_type = ShareType.PASSWORD
        
        if expire_hours is not None:
            share.expire_at = datetime.now() + timedelta(hours=expire_hours)
        
        if max_views is not None:
            share.max_views = max_views
        
        self._save_shares()
        return share
    
    def cleanup_expired(self) -> int:
        """清理过期的分享链接"""
        count = 0
        now = datetime.now()
        
        for share in list(self._shares.values()):
            if share.expire_at and now > share.expire_at:
                if share.status == ShareStatus.ACTIVE:
                    share.status = ShareStatus.EXPIRED
                    count += 1
        
        if count > 0:
            self._save_shares()
        
        return count


# 单例
_share_service = None

def get_share_service() -> ShareProtectionService:
    """获取分享保护服务单例"""
    global _share_service
    if _share_service is None:
        _share_service = ShareProtectionService()
    return _share_service
