"""
社区功能模块
生态化扩展 - Phase 4.4
支持用户分享、评论、点赞等社交功能
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
import json
from pathlib import Path


class ShareType(Enum):
    """分享类型"""
    PUBLIC = "public"  # 公开分享
    PASSWORD = "password"  # 密码分享
    EXPIRE = "expire"  # 限时分享
    PRIVATE = "private"  # 私密分享


class CommentStatus(Enum):
    """评论状态"""
    ACTIVE = "active"
    HIDDEN = "hidden"
    DELETED = "deleted"


@dataclass
class Share:
    """分享"""
    id: str
    user_id: str
    media_ids: List[str]
    album_id: Optional[str]
    share_type: ShareType
    title: str
    description: str
    password: Optional[str]
    expire_at: Optional[datetime]
    view_count: int
    download_count: int
    like_count: int
    created_at: datetime
    is_active: bool


@dataclass
class Comment:
    """评论"""
    id: str
    share_id: str
    user_id: str
    parent_id: Optional[str]  # 回复的评论ID
    content: str
    status: CommentStatus
    like_count: int
    created_at: datetime
    updated_at: datetime


@dataclass
class Like:
    """点赞"""
    id: str
    user_id: str
    target_type: str  # share, comment
    target_id: str
    created_at: datetime


@dataclass
class Follow:
    """关注"""
    id: str
    follower_id: str  # 关注者
    following_id: str  # 被关注者
    created_at: datetime


class CommunityService:
    """社区服务"""
    
    def __init__(self, storage_path: str = "data/community"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self._shares: Dict[str, Share] = {}
        self._comments: Dict[str, Comment] = {}
        self._likes: Dict[str, Like] = {}
        self._follows: Dict[str, Follow] = {}
        
        self._load_data()
    
    def _load_data(self):
        """加载数据"""
        # 加载分享
        shares_file = self.storage_path / "shares.json"
        if shares_file.exists():
            with open(shares_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for s in data:
                    share = Share(
                        id=s["id"],
                        user_id=s["user_id"],
                        media_ids=s["media_ids"],
                        album_id=s.get("album_id"),
                        share_type=ShareType(s["share_type"]),
                        title=s["title"],
                        description=s["description"],
                        password=s.get("password"),
                        expire_at=datetime.fromisoformat(s["expire_at"]) if s.get("expire_at") else None,
                        view_count=s["view_count"],
                        download_count=s["download_count"],
                        like_count=s["like_count"],
                        created_at=datetime.fromisoformat(s["created_at"]),
                        is_active=s["is_active"]
                    )
                    self._shares[share.id] = share
    
    def _save_shares(self):
        """保存分享"""
        shares_file = self.storage_path / "shares.json"
        data = []
        for share in self._shares.values():
            data.append({
                "id": share.id,
                "user_id": share.user_id,
                "media_ids": share.media_ids,
                "album_id": share.album_id,
                "share_type": share.share_type.value,
                "title": share.title,
                "description": share.description,
                "password": share.password,
                "expire_at": share.expire_at.isoformat() if share.expire_at else None,
                "view_count": share.view_count,
                "download_count": share.download_count,
                "like_count": share.like_count,
                "created_at": share.created_at.isoformat(),
                "is_active": share.is_active
            })
        with open(shares_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    async def create_share(self, user_id: str, share_data: Dict) -> Share:
        """创建分享"""
        import uuid
        
        share_id = str(uuid.uuid4())
        
        share = Share(
            id=share_id,
            user_id=user_id,
            media_ids=share_data["media_ids"],
            album_id=share_data.get("album_id"),
            share_type=ShareType(share_data.get("share_type", "public")),
            title=share_data.get("title", ""),
            description=share_data.get("description", ""),
            password=share_data.get("password"),
            expire_at=datetime.fromisoformat(share_data["expire_at"]) if share_data.get("expire_at") else None,
            view_count=0,
            download_count=0,
            like_count=0,
            created_at=datetime.utcnow(),
            is_active=True
        )
        
        self._shares[share_id] = share
        self._save_shares()
        
        return share
    
    async def get_share(self, share_id: str, password: str = None) -> Optional[Share]:
        """获取分享"""
        share = self._shares.get(share_id)
        
        if not share or not share.is_active:
            return None
        
        # 检查是否过期
        if share.expire_at and share.expire_at < datetime.utcnow():
            return None
        
        # 检查密码
        if share.share_type == ShareType.PASSWORD:
            if password != share.password:
                return None
        
        # 增加浏览数
        share.view_count += 1
        self._save_shares()
        
        return share
    
    async def list_public_shares(self, limit: int = 20, offset: int = 0) -> List[Share]:
        """列出公开分享"""
        public_shares = [
            s for s in self._shares.values()
            if s.share_type == ShareType.PUBLIC and s.is_active
        ]
        
        # 按时间排序
        public_shares.sort(key=lambda x: x.created_at, reverse=True)
        
        return public_shares[offset:offset + limit]
    
    async def list_user_shares(self, user_id: str) -> List[Share]:
        """列出用户的分享"""
        return [
            s for s in self._shares.values()
            if s.user_id == user_id
        ]
    
    async def delete_share(self, share_id: str, user_id: str) -> bool:
        """删除分享"""
        share = self._shares.get(share_id)
        
        if not share or share.user_id != user_id:
            return False
        
        share.is_active = False
        self._save_shares()
        
        return True
    
    async def add_comment(self, share_id: str, user_id: str, content: str, 
                         parent_id: str = None) -> Comment:
        """添加评论"""
        import uuid
        
        comment_id = str(uuid.uuid4())
        
        comment = Comment(
            id=comment_id,
            share_id=share_id,
            user_id=user_id,
            parent_id=parent_id,
            content=content,
            status=CommentStatus.ACTIVE,
            like_count=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        self._comments[comment_id] = comment
        
        return comment
    
    async def get_comments(self, share_id: str) -> List[Comment]:
        """获取评论"""
        comments = [
            c for c in self._comments.values()
            if c.share_id == share_id and c.status == CommentStatus.ACTIVE
        ]
        
        # 按时间排序
        comments.sort(key=lambda x: x.created_at)
        
        return comments
    
    async def like_share(self, share_id: str, user_id: str) -> bool:
        """点赞分享"""
        # 检查是否已经点赞
        like_key = f"{user_id}_share_{share_id}"
        
        if like_key in self._likes:
            # 取消点赞
            del self._likes[like_key]
            
            share = self._shares.get(share_id)
            if share:
                share.like_count = max(0, share.like_count - 1)
                self._save_shares()
            
            return False  # 返回False表示已取消
        
        # 添加点赞
        import uuid
        like = Like(
            id=str(uuid.uuid4()),
            user_id=user_id,
            target_type="share",
            target_id=share_id,
            created_at=datetime.utcnow()
        )
        
        self._likes[like_key] = like
        
        share = self._shares.get(share_id)
        if share:
            share.like_count += 1
            self._save_shares()
        
        return True
    
    async def follow_user(self, follower_id: str, following_id: str) -> bool:
        """关注用户"""
        if follower_id == following_id:
            return False
        
        follow_key = f"{follower_id}_{following_id}"
        
        if follow_key in self._follows:
            # 取消关注
            del self._follows[follow_key]
            return False
        
        # 添加关注
        import uuid
        follow = Follow(
            id=str(uuid.uuid4()),
            follower_id=follower_id,
            following_id=following_id,
            created_at=datetime.utcnow()
        )
        
        self._follows[follow_key] = follow
        
        return True
    
    async def get_followers(self, user_id: str) -> List[str]:
        """获取粉丝列表"""
        return [
            f.follower_id for f in self._follows.values()
            if f.following_id == user_id
        ]
    
    async def get_following(self, user_id: str) -> List[str]:
        """获取关注列表"""
        return [
            f.following_id for f in self._follows.values()
            if f.follower_id == user_id
        ]
    
    async def get_feed(self, user_id: str, limit: int = 20) -> List[Share]:
        """获取动态 feed"""
        # 获取关注的用户
        following = await self.get_following(user_id)
        
        # 获取这些用户的分享
        shares = [
            s for s in self._shares.values()
            if s.user_id in following and s.share_type == ShareType.PUBLIC
        ]
        
        # 按时间排序
        shares.sort(key=lambda x: x.created_at, reverse=True)
        
        return shares[:limit]


# 全局实例
community_service = CommunityService()
