"""
智能相册推荐模块
AI智能化 - Phase 3.2
基于时间、地点、人物、内容自动推荐相册
"""

from typing import List, Dict, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
import json
import asyncio


@dataclass
class MediaItem:
    """媒体项"""
    id: str
    path: str
    media_type: str  # image, video
    created_at: datetime
    location: Optional[Dict] = None  # {lat, lon, name}
    faces: List[str] = field(default_factory=list)  # 人脸ID列表
    tags: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)


@dataclass
class SmartAlbum:
    """智能相册"""
    id: str
    name: str
    description: str
    album_type: str  # time_based, location_based, people_based, event_based, content_based
    media_ids: List[str]
    cover_image: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    score: float = 0.0  # 推荐分数
    reason: str = ""  # 推荐理由


class SmartAlbumRecommender:
    """智能相册推荐器"""
    
    def __init__(self):
        self._media_items: Dict[str, MediaItem] = {}
        self._albums: Dict[str, SmartAlbum] = {}
        
        # 推荐权重
        self.weights = {
            "time": 0.25,
            "location": 0.20,
            "people": 0.25,
            "event": 0.15,
            "content": 0.15
        }
    
    async def add_media(self, media: MediaItem):
        """添加媒体项"""
        self._media_items[media.id] = media
    
    async def generate_time_based_albums(self) -> List[SmartAlbum]:
        """基于时间生成相册"""
        albums = []
        
        # 按日期分组
        date_groups = defaultdict(list)
        for media in self._media_items.values():
            date_key = media.created_at.strftime("%Y-%m-%d")
            date_groups[date_key].append(media)
        
        # 生成每日相册
        for date_key, media_list in date_groups.items():
            if len(media_list) >= 5:  # 至少5张照片
                date_obj = datetime.strptime(date_key, "%Y-%m-%d")
                
                album = SmartAlbum(
                    id=f"album_time_{date_key}",
                    name=f"{date_obj.year}年{date_obj.month}月{date_obj.day}日",
                    description=f"{date_obj.year}年{date_obj.month}月{date_obj.day}日的回忆",
                    album_type="time_based",
                    media_ids=[m.id for m in media_list],
                    cover_image=media_list[0].id,
                    score=min(len(media_list) / 20, 1.0) * self.weights["time"],
                    reason=f"这一天拍摄了 {len(media_list)} 张照片"
                )
                albums.append(album)
        
        # 生成月度相册
        month_groups = defaultdict(list)
        for media in self._media_items.values():
            month_key = media.created_at.strftime("%Y-%m")
            month_groups[month_key].append(media)
        
        for month_key, media_list in month_groups.items():
            if len(media_list) >= 20:  # 至少20张照片
                year, month = month_key.split('-')
                
                album = SmartAlbum(
                    id=f"album_month_{month_key}",
                    name=f"{year}年{int(month)}月",
                    description=f"{year}年{int(month)}月的精彩瞬间",
                    album_type="time_based",
                    media_ids=[m.id for m in media_list],
                    cover_image=media_list[len(media_list)//2].id,
                    score=min(len(media_list) / 100, 1.0) * self.weights["time"],
                    reason=f"这个月共拍摄了 {len(media_list)} 张照片"
                )
                albums.append(album)
        
        return sorted(albums, key=lambda x: x.score, reverse=True)
    
    async def generate_location_based_albums(self) -> List[SmartAlbum]:
        """基于地点生成相册"""
        albums = []
        
        # 按地点分组
        location_groups = defaultdict(list)
        for media in self._media_items.values():
            if media.location and media.location.get('name'):
                location_name = media.location['name']
                location_groups[location_name].append(media)
        
        # 生成地点相册
        for location_name, media_list in location_groups.items():
            if len(media_list) >= 3:  # 至少3张照片
                album = SmartAlbum(
                    id=f"album_location_{location_name.replace(' ', '_')}",
                    name=location_name,
                    description=f"在 {location_name} 的美好时光",
                    album_type="location_based",
                    media_ids=[m.id for m in media_list],
                    cover_image=media_list[0].id,
                    score=min(len(media_list) / 30, 1.0) * self.weights["location"],
                    reason=f"在 {location_name} 拍摄了 {len(media_list)} 张照片"
                )
                albums.append(album)
        
        return sorted(albums, key=lambda x: x.score, reverse=True)
    
    async def generate_people_based_albums(self, face_engine=None) -> List[SmartAlbum]:
        """基于人物生成相册"""
        albums = []
        
        # 按人物分组
        people_groups = defaultdict(list)
        for media in self._media_items.values():
            for face_id in media.faces:
                people_groups[face_id].append(media)
        
        # 生成人物相册
        for person_id, media_list in people_groups.items():
            if len(media_list) >= 5:  # 至少5张照片
                # 获取人物名称
                person_name = f"人物_{person_id[:8]}"
                if face_engine and hasattr(face_engine, '_identities'):
                    for identity in face_engine._identities.values():
                        if person_id in identity.face_ids:
                            person_name = identity.name
                            break
                
                album = SmartAlbum(
                    id=f"album_person_{person_id}",
                    name=f"{person_name}的相册",
                    description=f"与 {person_name} 在一起的美好时光",
                    album_type="people_based",
                    media_ids=[m.id for m in media_list],
                    cover_image=media_list[0].id,
                    score=min(len(media_list) / 50, 1.0) * self.weights["people"],
                    reason=f"{person_name} 出现在 {len(media_list)} 张照片中"
                )
                albums.append(album)
        
        return sorted(albums, key=lambda x: x.score, reverse=True)
    
    async def generate_event_based_albums(self) -> List[SmartAlbum]:
        """基于事件生成相册"""
        albums = []
        
        # 按时间段聚类 (密度聚类)
        media_list = sorted(self._media_items.values(), key=lambda x: x.created_at)
        
        if len(media_list) < 10:
            return albums
        
        # 简单的事件检测：短时间内大量照片
        events = []
        current_event = [media_list[0]]
        
        for i in range(1, len(media_list)):
            time_diff = (media_list[i].created_at - media_list[i-1].created_at).total_seconds()
            
            if time_diff < 3600:  # 1小时内
                current_event.append(media_list[i])
            else:
                if len(current_event) >= 10:  # 至少10张照片
                    events.append(current_event)
                current_event = [media_list[i]]
        
        if len(current_event) >= 10:
            events.append(current_event)
        
        # 生成事件相册
        for idx, event in enumerate(events):
            start_time = event[0].created_at
            end_time = event[-1].created_at
            duration = (end_time - start_time).total_seconds() / 3600  # 小时
            
            album = SmartAlbum(
                id=f"album_event_{idx}_{start_time.strftime('%Y%m%d')}",
                name=f"精彩活动 {start_time.strftime('%m月%d日')}",
                description=f"{start_time.strftime('%Y年%m月%d日')} 的活动，持续 {duration:.1f} 小时",
                album_type="event_based",
                media_ids=[m.id for m in event],
                cover_image=event[len(event)//2].id,
                score=min(len(event) / 50, 1.0) * self.weights["event"],
                reason=f"活动期间拍摄了 {len(event)} 张照片，持续 {duration:.1f} 小时"
            )
            albums.append(album)
        
        return sorted(albums, key=lambda x: x.score, reverse=True)
    
    async def generate_content_based_albums(self) -> List[SmartAlbum]:
        """基于内容标签生成相册"""
        albums = []
        
        # 按标签分组
        tag_groups = defaultdict(list)
        for media in self._media_items.values():
            for tag in media.tags:
                tag_groups[tag].append(media)
        
        # 生成标签相册
        for tag, media_list in tag_groups.items():
            if len(media_list) >= 5:  # 至少5张照片
                album = SmartAlbum(
                    id=f"album_tag_{tag}",
                    name=f"{tag}",
                    description=f"标记为 '{tag}' 的照片",
                    album_type="content_based",
                    media_ids=[m.id for m in media_list],
                    cover_image=media_list[0].id,
                    score=min(len(media_list) / 30, 1.0) * self.weights["content"],
                    reason=f"有 {len(media_list)} 张照片标记为 '{tag}'"
                )
                albums.append(album)
        
        return sorted(albums, key=lambda x: x.score, reverse=True)
    
    async def generate_all_recommendations(self, face_engine=None) -> Dict[str, List[SmartAlbum]]:
        """生成所有推荐相册"""
        recommendations = {
            "time_based": await self.generate_time_based_albums(),
            "location_based": await self.generate_location_based_albums(),
            "people_based": await self.generate_people_based_albums(face_engine),
            "event_based": await self.generate_event_based_albums(),
            "content_based": await self.generate_content_based_albums()
        }
        
        return recommendations
    
    async def get_top_recommendations(self, limit: int = 10, face_engine=None) -> List[SmartAlbum]:
        """获取 top N 推荐"""
        all_recommendations = await self.generate_all_recommendations(face_engine)
        
        # 合并所有推荐
        all_albums = []
        for category, albums in all_recommendations.items():
            all_albums.extend(albums)
        
        # 按分数排序
        all_albums.sort(key=lambda x: x.score, reverse=True)
        
        return all_albums[:limit]
    
    def to_dict(self, album: SmartAlbum) -> Dict:
        """转换为字典"""
        return {
            "id": album.id,
            "name": album.name,
            "description": album.description,
            "album_type": album.album_type,
            "media_count": len(album.media_ids),
            "cover_image": album.cover_image,
            "created_at": album.created_at.isoformat(),
            "score": round(album.score, 3),
            "reason": album.reason
        }


# 全局推荐器实例
smart_album_recommender = SmartAlbumRecommender()
