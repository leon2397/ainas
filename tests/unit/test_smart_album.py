"""
智能相册推荐模块单元测试
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
import json


class TestTimeBasedRecommendation:
    """基于时间的推荐测试"""
    
    @pytest.fixture
    def recommender(self):
        """创建推荐器实例"""
        from ai.smart_album.recommender import SmartAlbumRecommender
        recommender = SmartAlbumRecommender()
        recommender.db = Mock()
        return recommender
    
    def test_recommend_by_date(self, recommender):
        """测试按日期推荐"""
        target_date = datetime(2026, 4, 6)
        
        recommender.db.fetch_all = Mock(return_value=[
            {"id": 1, "file_path": "/2026/04/06/photo1.jpg", "created_at": "2026-04-06 10:00:00"},
            {"id": 2, "file_path": "/2026/04/06/photo2.jpg", "created_at": "2026-04-06 14:00:00"}
        ])
        
        results = recommender.recommend_by_date(target_date)
        
        assert len(results) == 2
    
    def test_recommend_by_date_range(self, recommender):
        """测试按日期范围推荐"""
        start_date = datetime(2026, 4, 1)
        end_date = datetime(2026, 4, 7)
        
        recommender.db.fetch_all = Mock(return_value=[
            {"id": 1, "created_at": "2026-04-01"},
            {"id": 2, "created_at": "2026-04-03"},
            {"id": 3, "created_at": "2026-04-06"}
        ])
        
        results = recommender.recommend_by_date_range(start_date, end_date)
        
        assert len(results) == 3
    
    def test_recommend_by_year(self, recommender):
        """测试按年份推荐"""
        recommender.db.fetch_all = Mock(return_value=[
            {"id": 1, "created_at": "2025-06-15"},
            {"id": 2, "created_at": "2025-08-20"}
        ])
        
        results = recommender.recommend_by_year(2025)
        
        assert len(results) == 2
    
    def test_recommend_by_month(self, recommender):
        """测试按月份推荐"""
        recommender.db.fetch_all = Mock(return_value=[
            {"id": 1, "created_at": "2026-04-05"},
            {"id": 2, "created_at": "2026-04-20"}
        ])
        
        results = recommender.recommend_by_month(2026, 4)
        
        assert len(results) == 2
    
    def test_recommend_by_season(self, recommender):
        """测试按季节推荐"""
        recommender.db.fetch_all = Mock(return_value=[
            {"id": 1, "created_at": "2026-04-01"},  # 春季
            {"id": 2, "created_at": "2026-04-15"},
            {"id": 3, "created_at": "2026-07-01"}  # 夏季
        ])
        
        results = recommender.recommend_by_season(2026, "spring")
        
        assert len(results) == 2  # 只返回春季的照片
    
    def test_recommend_this_day_in_history(self, recommender):
        """测试""""历史上的今天""""推荐"""
        today = datetime.now()
        
        recommender.db.fetch_all = Mock(return_value=[
            {"id": 1, "created_at": f"{today.year-1}-{today.month:02d}-{today.day:02d}"},
            {"id": 2, "created_at": f"{today.year-2}-{today.month:02d}-{today.day:02d}"}
        ])
        
        results = recommender.recommend_this_day_in_history()
        
        assert len(results) == 2
    
    def test_recommend_recent_photos(self, recommender):
        """测试最近照片推荐"""
        recommender.db.fetch_all = Mock(return_value=[
            {"id": 1, "created_at": datetime.now().isoformat()},
            {"id": 2, "created_at": (datetime.now() - timedelta(days=1)).isoformat()},
            {"id": 3, "created_at": (datetime.now() - timedelta(days=2)).isoformat()}
        ])
        
        results = recommender.recommend_recent_photos(days=7, limit=10)
        
        assert len(results) == 3


class TestLocationBasedRecommendation:
    """基于地点的推荐测试"""
    
    @pytest.fixture
    def recommender(self):
        """创建推荐器实例"""
        from ai.smart_album.recommender import SmartAlbumRecommender
        recommender = SmartAlbumRecommender()
        recommender.db = Mock()
        return recommender
    
    def test_recommend_by_location_name(self, recommender):
        """测试按地点名称推荐"""
        recommender.db.fetch_all = Mock(return_value=[
            {"id": 1, "location": "北京", "gps_lat": 39.9, "gps_lon": 116.4},
            {"id": 2, "location": "北京", "gps_lat": 39.95, "gps_lon": 116.45}
        ])
        
        results = recommender.recommend_by_location("北京")
        
        assert len(results) == 2
    
    def test_recommend_by_gps_coordinates(self, recommender):
        """测试按GPS坐标推荐"""
        recommender.db.fetch_all = Mock(return_value=[
            {"id": 1, "gps_lat": 39.9, "gps_lon": 116.4, "location": "北京"},
            {"id": 2, "gps_lat": 39.95, "gps_lon": 116.45, "location": "北京"},
            {"id": 3, "gps_lat": 31.2, "gps_lon": 121.5, "location": "上海"}
        ])
        
        # 在北京附近搜索
        results = recommender.recommend_by_coordinates(
            lat=39.9,
            lon=116.4,
            radius_km=10
        )
        
        assert len(results) == 2
    
    def test_recommend_by_country(self, recommender):
        """测试按国家推荐"""
        recommender.db.fetch_all = Mock(return_value=[
            {"id": 1, "country": "中国", "city": "北京"},
            {"id": 2, "country": "中国", "city": "上海"},
            {"id": 3, "country": "日本", "city": "东京"}
        ])
        
        results = recommender.recommend_by_country("中国")
        
        assert len(results) == 2
    
    def test_recommend_by_city(self, recommender):
        """测试按城市推荐"""
        recommender.db.fetch_all = Mock(return_value=[
            {"id": 1, "city": "北京", "location": "天安门"},
            {"id": 2, "city": "北京", "location": "故宫"}
        ])
        
        results = recommender.recommend_by_city("北京")
        
        assert len(results) == 2
    
    def test_recommend_frequent_locations(self, recommender):
        """测试推荐常去地点"""
        recommender.db.fetch_all = Mock(return_value=[
            {"location": "北京", "count": 50},
            {"location": "上海", "count": 30},
            {"location": "广州", "count": 20}
        ])
        
        results = recommender.recommend_frequent_locations(limit=5)
        
        assert len(results) == 3
        assert results[0]["location"] == "北京"  # 最常去
    
    def test_recommend_nearby_photos(self, recommender):
        """测试附近照片推荐"""
        recommender.db.fetch_all = Mock(return_value=[
            {"id": 1, "gps_lat": 39.901, "gps_lon": 116.401, "distance": 0.1},
            {"id": 2, "gps_lat": 39.902, "gps_lon": 116.402, "distance": 0.2}
        ])
        
        results = recommender.recommend_nearby(
            lat=39.9,
            lon=116.4,
            radius_km=1
        )
        
        assert len(results) == 2


class TestPersonBasedRecommendation:
    """基于人物的推荐测试"""
    
    @pytest.fixture
    def recommender(self):
        """创建推荐器实例"""
        from ai.smart_album.recommender import SmartAlbumRecommender
        recommender = SmartAlbumRecommender()
        recommender.db = Mock()
        return recommender
    
    def test_recommend_by_person(self, recommender):
        """测试按人物推荐"""
        recommender.db.fetch_all = Mock(return_value=[
            {"id": 1, "person_name": "张三"},
            {"id": 2, "person_name": "张三"},
            {"id": 3, "person_name": "李四"}
        ])
        
        results = recommender.recommend_by_person("张三")
        
        assert len(results) == 2
    
    def test_recommend_by_multiple_persons(self, recommender):
        """测试按多个人物推荐"""
        recommender.db.fetch_all = Mock(return_value=[
            {"id": 1, "persons": ["张三", "李四"]},
            {"id": 2, "persons": ["张三", "王五"]}
        ])
        
        results = recommender.recommend_by_persons(["张三", "李四"])
        
        assert len(results) == 1  # 只有第一张照片同时包含张三和李四
    
    def test_recommend_frequent_persons(self, recommender):
        """测试推荐常出现的人物"""
        recommender.db.fetch_all = Mock(return_value=[
            {"person_name": "张三", "count": 100},
            {"person_name": "李四", "count": 80},
            {"person_name": "王五", "count": 50}
        ])
        
        results = recommender.recommend_frequent_persons(limit=5)
        
        assert len(results) == 3
        assert results[0]["person_name"] == "张三"
    
    def test_recommend_group_photos(self, recommender):
        """测试推荐合影"""
        recommender.db.fetch_all = Mock(return_value=[
            {"id": 1, "person_count": 5},
            {"id": 2, "person_count": 2},
            {"id": 3, "person_count": 8}
        ])
        
        results = recommender.recommend_group_photos(min_persons=3)
        
        assert len(results) == 2  # 5人和8人的照片


class TestEventBasedRecommendation:
    """基于事件的推荐测试"""
    
    @pytest.fixture
    def recommender(self):
        """创建推荐器实例"""
        from ai.smart_album.recommender import SmartAlbumRecommender
        recommender = SmartAlbumRecommender()
        recommender.db = Mock()
        return recommender
    
    def test_detect_events_by_time_clustering(self, recommender):
        """测试通过时间聚类检测事件"""
        # 模拟一个聚会事件（短时间内大量照片）
        photos = [
            {"id": 1, "created_at": "2026-04-06 18:00:00"},
            {"id": 2, "created_at": "2026-04-06 18:05:00"},
            {"id": 3, "created_at": "2026-04-06 18:10:00"},
            {"id": 4, "created_at": "2026-04-06 18:15:00"}
        ]
        
        events = recommender.detect_events(photos)
        
        assert len(events) >= 1
    
    def test_recommend_by_event_type(self, recommender):
        """测试按事件类型推荐"""
        recommender.db.fetch_all = Mock(return_value=[
            {"id": 1, "event_type": "聚会", "tags": ["party", "friends"]},
            {"id": 2, "event_type": "聚会", "tags": ["party"]},
            {"id": 3, "event_type": "旅行", "tags": ["travel"]}
        ])
        
        results = recommender.recommend_by_event_type("聚会")
        
        assert len(results) == 2
    
    def test_recommend_birthday_photos(self, recommender):
        """测试推荐生日照片"""
        recommender.db.fetch_all = Mock(return_value=[
            {"id": 1, "tags": ["birthday", "cake"], "created_at": "2026-04-06"},
            {"id": 2, "tags": ["party"], "created_at": "2026-04-06"}
        ])
        
        results = recommender.recommend_birthday_photos()
        
        assert len(results) == 1
    
    def test_recommend_travel_photos(self, recommender):
        """测试推荐旅行照片"""
        recommender.db.fetch_all = Mock(return_value=[
            {"id": 1, "tags": ["travel", "beach"], "gps_lat": 25.0, "gps_lon": 121.0},
            {"id": 2, "tags": ["travel", "mountain"], "gps_lat": 35.0, "gps_lon": 135.0}
        ])
        
        results = recommender.recommend_travel_photos()
        
        assert len(results) == 2
    
    def test_recommend_wedding_photos(self, recommender):
        """测试推荐婚礼照片"""
        recommender.db.fetch_all = Mock(return_value=[
            {"id": 1, "tags": ["wedding", "bride"]},
            {"id": 2, "tags": ["wedding", "ceremony"]}
        ])
        
        results = recommender.recommend_wedding_photos()
        
        assert len(results) == 2


class TestContentBasedRecommendation:
    """基于内容的推荐测试"""
    
    @pytest.fixture
    def recommender(self):
        """创建推荐器实例"""
        from ai.smart_album.recommender import SmartAlbumRecommender
        recommender = SmartAlbumRecommender()
        recommender.db = Mock()
        return recommender
    
    def test_recommend_by_tags(self, recommender):
        """测试按标签推荐"""
        recommender.db.fetch_all = Mock(return_value=[
            {"id": 1, "tags": ["beach", "sunset"]},
            {"id": 2, "tags": ["beach", "ocean"]},
            {"id": 3, "tags": ["mountain"]}
        ])
        
        results = recommender.recommend_by_tags(["beach"])
        
        assert len(results) == 2
    
    def test_recommend_by_multiple_tags(self, recommender):
        """测试按多个标签推荐"""
        recommender.db.fetch_all = Mock(return_value=[
            {"id": 1, "tags": ["beach", "sunset", "ocean"]},
            {"id": 2, "tags": ["beach", "ocean"]},
            {"id": 3, "tags": ["sunset", "mountain"]}
        ])
        
        results = recommender.recommend_by_tags(["beach", "sunset"])
        
        # 应该优先返回同时包含两个标签的照片
        assert results[0]["id"] == 1
    
    def test_recommend_scenery_photos(self, recommender):
        """测试推荐风景照片"""
        recommender.db.fetch_all = Mock(return_value=[
            {"id": 1, "tags": ["landscape", "mountain"], "category": "scenery"},
            {"id": 2, "tags": ["portrait"], "category": "people"}
        ])
        
        results = recommender.recommend_scenery_photos()
        
        assert len(results) == 1
    
    def test_recommend_food_photos(self, recommender):
        """测试推荐美食照片"""
        recommender.db.fetch_all = Mock(return_value=[
            {"id": 1, "tags": ["food", "dinner"]},
            {"id": 2, "tags": ["food", "dessert"]}
        ])
        
        results = recommender.recommend_food_photos()
        
        assert len(results) == 2
    
    def test_recommend_pet_photos(self, recommender):
        """测试推荐宠物照片"""
        recommender.db.fetch_all = Mock(return_value=[
            {"id": 1, "tags": ["dog", "pet"]},
            {"id": 2, "tags": ["cat", "pet"]}
        ])
        
        results = recommender.recommend_pet_photos()
        
        assert len(results) == 2
    
    def test_recommend_selfies(self, recommender):
        """测试推荐自拍"""
        recommender.db.fetch_all = Mock(return_value=[
            {"id": 1, "tags": ["selfie"], "person_count": 1},
            {"id": 2, "tags": ["portrait"], "person_count": 1}
        ])
        
        results = recommender.recommend_selfies()
        
        assert len(results) == 1


class TestSmartAlbumCreation:
    """智能相册创建测试"""
    
    @pytest.fixture
    def recommender(self):
        """创建推荐器实例"""
        from ai.smart_album.recommender import SmartAlbumRecommender
        recommender = SmartAlbumRecommender()
        recommender.db = Mock()
        return recommender
    
    def test_create_smart_album_by_date(self, recommender):
        """测试按日期创建智能相册"""
        recommender.db.fetch_all = Mock(return_value=[
            {"id": 1}, {"id": 2}, {"id": 3}
        ])
        recommender.db.execute = Mock(return_value=None)
        recommender.db.fetch_val = Mock(return_value=1)
        
        album_id = recommender.create_smart_album(
            name="2026年4月",
            criteria={"type": "date", "year": 2026, "month": 4}
        )
        
        assert album_id is not None
    
    def test_create_smart_album_by_person(self, recommender):
        """测试按人物创建智能相册"""
        recommender.db.fetch_all = Mock(return_value=[
            {"id": 1}, {"id": 2}
        ])
        recommender.db.execute = Mock(return_value=None)
        recommender.db.fetch_val = Mock(return_value=1)
        
        album_id = recommender.create_smart_album(
            name="张三的照片",
            criteria={"type": "person", "person_name": "张三"}
        )
        
        assert album_id is not None
    
    def test_create_smart_album_by_location(self, recommender):
        """测试按地点创建智能相册"""
        recommender.db.fetch_all = Mock(return_value=[
            {"id": 1}, {"id": 2}, {"id": 3}
        ])
        recommender.db.execute = Mock(return_value=None)
        recommender.db.fetch_val = Mock(return_value=1)
        
        album_id = recommender.create_smart_album(
            name="北京之旅",
            criteria={"type": "location", "city": "北京"}
        )
        
        assert album_id is not None
    
    def test_update_smart_album(self, recommender):
        """测试更新智能相册"""
        recommender.db.execute = Mock(return_value=None)
        
        result = recommender.update_smart_album(
            album_id=1,
            criteria={"type": "date", "year": 2026}
        )
        
        assert result is True
    
    def test_refresh_smart_album(self, recommender):
        """测试刷新智能相册内容"""
        recommender.db.fetch_one = Mock(return_value={
            "id": 1,
            "criteria": json.dumps({"type": "person", "person_name": "张三"})
        })
        recommender.db.fetch_all = Mock(return_value=[
            {"id": 1}, {"id": 2}
        ])
        recommender.db.execute = Mock(return_value=None)
        
        result = recommender.refresh_smart_album(album_id=1)
        
        assert result is True


class TestRecommendationRanking:
    """推荐排序测试"""
    
    @pytest.fixture
    def recommender(self):
        """创建推荐器实例"""
        from ai.smart_album.recommender import SmartAlbumRecommender
        return SmartAlbumRecommender()
    
    def test_rank_by_relevance(self, recommender):
        """测试按相关性排序"""
        photos = [
            {"id": 1, "relevance_score": 0.9},
            {"id": 2, "relevance_score": 0.7},
            {"id": 3, "relevance_score": 0.95}
        ]
        
        ranked = recommender.rank_by_relevance(photos)
        
        assert ranked[0]["id"] == 3  # 最高分在前
        assert ranked[2]["id"] == 2  # 最低分在后
    
    def test_rank_by_quality(self, recommender):
        """测试按质量排序"""
        photos = [
            {"id": 1, "quality_score": 0.8},
            {"id": 2, "quality_score": 0.95},
            {"id": 3, "quality_score": 0.7}
        ]
        
        ranked = recommender.rank_by_quality(photos)
        
        assert ranked[0]["id"] == 2
    
    def test_rank_by_recency(self, recommender):
        """测试按时间排序"""
        from datetime import datetime, timedelta
        
        now = datetime.now()
        photos = [
            {"id": 1, "created_at": (now - timedelta(days=2)).isoformat()},
            {"id": 2, "created_at": now.isoformat()},
            {"id": 3, "created_at": (now - timedelta(days=1)).isoformat()}
        ]
        
        ranked = recommender.rank_by_recency(photos)
        
        assert ranked[0]["id"] == 2  # 最新的在前


class TestRecommendationAPI:
    """推荐API测试"""
    
    @pytest.fixture
    def recommender(self):
        """创建推荐器实例"""
        from ai.smart_album.recommender import SmartAlbumRecommender
        recommender = SmartAlbumRecommender()
        recommender.db = Mock()
        return recommender
    
    def test_get_recommendations_combined(self, recommender):
        """测试获取综合推荐"""
        recommender.db.fetch_all = Mock(return_value=[
            {"id": 1, "relevance_score": 0.9},
            {"id": 2, "relevance_score": 0.8}
        ])
        
        results = recommender.get_recommendations(
            user_id=1,
            dimensions=["time", "location", "person"],
            limit=10
        )
        
        assert len(results) == 2
    
    def test_get_daily_recommendations(self, recommender):
        """测试获取每日推荐"""
        recommender.db.fetch_all = Mock(return_value=[
            {"id": 1}, {"id": 2}, {"id": 3}
        ])
        
        results = recommender.get_daily_recommendations(user_id=1)
        
        assert len(results) == 3
    
    def test_get_weekly_highlights(self, recommender):
        """测试获取每周精选"""
        recommender.db.fetch_all = Mock(return_value=[
            {"id": 1, "quality_score": 0.95},
            {"id": 2, "quality_score": 0.9}
        ])
        
        results = recommender.get_weekly_highlights()
        
        assert len(results) == 2
    
    def test_get_memory_flashback(self, recommender):
        """测试获取回忆闪回"""
        # 模拟""""去年的今天""""
        recommender.db.fetch_all = Mock(return_value=[
            {"id": 1, "created_at": "2025-04-06"},
            {"id": 2, "created_at": "2025-04-06"}
        ])
        
        results = recommender.get_memory_flashback(years_ago=1)
        
        assert len(results) == 2
