"""
自动标签模块单元测试
"""
import pytest
from unittest.mock import Mock, patch
import json


class TestTagCategories:
    """标签分类测试"""
    
    def test_scene_tags_defined(self):
        """测试场景标签已定义"""
        from ai.auto_tagging.tagger import AutoTagger
        tagger = AutoTagger()
        
        scene_tags = tagger.get_scene_tags()
        
        assert len(scene_tags) > 0
        assert "beach" in scene_tags or "landscape" in scene_tags
    
    def test_object_tags_defined(self):
        """测试物体标签已定义"""
        from ai.auto_tagging.tagger import AutoTagger
        tagger = AutoTagger()
        
        object_tags = tagger.get_object_tags()
        
        assert len(object_tags) > 0
        assert "car" in object_tags or "building" in object_tags
    
    def test_person_tags_defined(self):
        """测试人物标签已定义"""
        from ai.auto_tagging.tagger import AutoTagger
        tagger = AutoTagger()
        
        person_tags = tagger.get_person_tags()
        
        assert len(person_tags) > 0
        assert "baby" in person_tags or "child" in person_tags
    
    def test_activity_tags_defined(self):
        """测试活动标签已定义"""
        from ai.auto_tagging.tagger import AutoTagger
        tagger = AutoTagger()
        
        activity_tags = tagger.get_activity_tags()
        
        assert len(activity_tags) > 0
        assert "wedding" in activity_tags or "party" in activity_tags


class TestSceneTagging:
    """场景标签测试"""
    
    @pytest.fixture
    def tagger(self):
        """创建标签器实例"""
        from ai.auto_tagging.tagger import AutoTagger
        tagger = AutoTagger()
        tagger.model = Mock()
        return tagger
    
    def test_tag_beach_scene(self, tagger):
        """测试海滩场景标签"""
        tagger.model.predict.return_value = [
            ("beach", 0.95),
            ("ocean", 0.88),
            ("sand", 0.85)
        ]
        
        mock_image = Mock()
        tags = tagger.tag_scene(mock_image)
        
        assert "beach" in [t["tag"] for t in tags]
        assert all(t["confidence"] > 0.5 for t in tags)
    
    def test_tag_mountain_scene(self, tagger):
        """测试山景标签"""
        tagger.model.predict.return_value = [
            ("mountain", 0.92),
            ("landscape", 0.85),
            ("nature", 0.80)
        ]
        
        mock_image = Mock()
        tags = tagger.tag_scene(mock_image)
        
        assert "mountain" in [t["tag"] for t in tags]
    
    def test_tag_city_scene(self, tagger):
        """测试城市场景标签"""
        tagger.model.predict.return_value = [
            ("city", 0.90),
            ("building", 0.85),
            ("urban", 0.82)
        ]
        
        mock_image = Mock()
        tags = tagger.tag_scene(mock_image)
        
        assert "city" in [t["tag"] for t in tags]
    
    def test_tag_indoor_scene(self, tagger):
        """测试室内场景标签"""
        tagger.model.predict.return_value = [
            ("indoor", 0.88),
            ("room", 0.82)
        ]
        
        mock_image = Mock()
        tags = tagger.tag_scene(mock_image)
        
        assert "indoor" in [t["tag"] for t in tags]
    
    def test_scene_confidence_threshold(self, tagger):
        """测试场景置信度阈值"""
        tagger.model.predict.return_value = [
            ("beach", 0.95),
            ("ocean", 0.45),  # 低于阈值
            ("sand", 0.30)    # 低于阈值
        ]
        
        mock_image = Mock()
        tags = tagger.tag_scene(mock_image, min_confidence=0.5)
        
        assert len(tags) == 1
        assert tags[0]["tag"] == "beach"


class TestObjectTagging:
    """物体标签测试"""
    
    @pytest.fixture
    def tagger(self):
        """创建标签器实例"""
        from ai.auto_tagging.tagger import AutoTagger
        tagger = AutoTagger()
        tagger.model = Mock()
        return tagger
    
    def test_tag_car_object(self, tagger):
        """测试汽车物体标签"""
        tagger.model.detect_objects.return_value = [
            {"label": "car", "confidence": 0.92, "bbox": [100, 100, 200, 200]},
            {"label": "vehicle", "confidence": 0.88, "bbox": [100, 100, 200, 200]}
        ]
        
        mock_image = Mock()
        tags = tagger.tag_objects(mock_image)
        
        assert "car" in [t["tag"] for t in tags]
    
    def test_tag_food_object(self, tagger):
        """测试食物物体标签"""
        tagger.model.detect_objects.return_value = [
            {"label": "food", "confidence": 0.90},
            {"label": "plate", "confidence": 0.85}
        ]
        
        mock_image = Mock()
        tags = tagger.tag_objects(mock_image)
        
        assert "food" in [t["tag"] for t in tags]
    
    def test_tag_animal_object(self, tagger):
        """测试动物物体标签"""
        tagger.model.detect_objects.return_value = [
            {"label": "dog", "confidence": 0.95},
            {"label": "animal", "confidence": 0.90}
        ]
        
        mock_image = Mock()
        tags = tagger.tag_objects(mock_image)
        
        assert "dog" in [t["tag"] for t in tags]
    
    def test_tag_building_object(self, tagger):
        """测试建筑物标签"""
        tagger.model.detect_objects.return_value = [
            {"label": "building", "confidence": 0.88},
            {"label": "architecture", "confidence": 0.82}
        ]
        
        mock_image = Mock()
        tags = tagger.tag_objects(mock_image)
        
        assert "building" in [t["tag"] for t in tags]
    
    def test_object_count_tracking(self, tagger):
        """测试物体数量追踪"""
        tagger.model.detect_objects.return_value = [
            {"label": "person", "confidence": 0.95},
            {"label": "person", "confidence": 0.92},
            {"label": "person", "confidence": 0.88}
        ]
        
        mock_image = Mock()
        tags = tagger.tag_objects(mock_image)
        
        person_tag = next((t for t in tags if t["tag"] == "person"), None)
        assert person_tag is not None
        assert person_tag.get("count") == 3


class TestPersonTagging:
    """人物标签测试"""
    
    @pytest.fixture
    def tagger(self):
        """创建标签器实例"""
        from ai.auto_tagging.tagger import AutoTagger
        tagger = AutoTagger()
        tagger.face_recognition = Mock()
        return tagger
    
    def test_tag_baby(self, tagger):
        """测试婴儿标签"""
        tagger.face_recognition.detect_faces.return_value = [
            {"age": 1, "gender": "child"}
        ]
        
        mock_image = Mock()
        tags = tagger.tag_persons(mock_image)
        
        assert "baby" in [t["tag"] for t in tags]
    
    def test_tag_child(self, tagger):
        """测试儿童标签"""
        tagger.face_recognition.detect_faces.return_value = [
            {"age": 8, "gender": "child"}
        ]
        
        mock_image = Mock()
        tags = tagger.tag_persons(mock_image)
        
        assert "child" in [t["tag"] for t in tags]
    
    def test_tag_adult(self, tagger):
        """测试成人标签"""
        tagger.face_recognition.detect_faces.return_value = [
            {"age": 30, "gender": "male"}
        ]
        
        mock_image = Mock()
        tags = tagger.tag_persons(mock_image)
        
        assert "adult" in [t["tag"] for t in tags]
    
    def test_tag_group_photo(self, tagger):
        """测试合影标签"""
        tagger.face_recognition.detect_faces.return_value = [
            {"age": 30}, {"age": 28}, {"age": 35}, {"age": 32}
        ]
        
        mock_image = Mock()
        tags = tagger.tag_persons(mock_image)
        
        assert "group" in [t["tag"] for t in tags]
    
    def test_tag_selfie(self, tagger):
        """测试自拍标签"""
        tagger.face_recognition.detect_faces.return_value = [
            {"age": 25}
        ]
        # 模拟自拍检测（人脸占据大部分画面）
        
        mock_image = Mock()
        tags = tagger.tag_persons(mock_image, is_selfie=True)
        
        assert "selfie" in [t["tag"] for t in tags]


class TestActivityTagging:
    """活动标签测试"""
    
    @pytest.fixture
    def tagger(self):
        """创建标签器实例"""
        from ai.auto_tagging.tagger import AutoTagger
        tagger = AutoTagger()
        tagger.model = Mock()
        return tagger
    
    def test_tag_wedding(self, tagger):
        """测试婚礼标签"""
        tagger.model.predict.return_value = [
            ("wedding", 0.95),
            ("bride", 0.88),
            ("ceremony", 0.82)
        ]
        
        mock_image = Mock()
        tags = tagger.tag_activities(mock_image)
        
        assert "wedding" in [t["tag"] for t in tags]
    
    def test_tag_sports(self, tagger):
        """测试运动标签"""
        tagger.model.predict.return_value = [
            ("sports", 0.90),
            ("running", 0.85)
        ]
        
        mock_image = Mock()
        tags = tagger.tag_activities(mock_image)
        
        assert "sports" in [t["tag"] for t in tags]
    
    def test_tag_party(self, tagger):
        """测试聚会标签"""
        tagger.model.predict.return_value = [
            ("party", 0.92),
            ("celebration", 0.85)
        ]
        
        mock_image = Mock()
        tags = tagger.tag_activities(mock_image)
        
        assert "party" in [t["tag"] for t in tags]
    
    def test_tag_travel(self, tagger):
        """测试旅行标签"""
        tagger.model.predict.return_value = [
            ("travel", 0.88),
            ("tourism", 0.82)
        ]
        
        mock_image = Mock()
        tags = tagger.tag_activities(mock_image)
        
        assert "travel" in [t["tag"] for t in tags]


class TestBatchTagging:
    """批量标签测试"""
    
    @pytest.fixture
    def tagger(self):
        """创建标签器实例"""
        from ai.auto_tagging.tagger import AutoTagger
        tagger = AutoTagger()
        tagger.model = Mock()
        tagger.db = Mock()
        return tagger
    
    def test_batch_tag_images(self, tagger):
        """测试批量标签图像"""
        tagger.model.predict.return_value = [
            ("beach", 0.95),
            ("ocean", 0.88)
        ]
        
        image_paths = ["/path/to/image1.jpg", "/path/to/image2.jpg"]
        results = tagger.batch_tag(image_paths)
        
        assert len(results) == 2
    
    def test_batch_tag_with_progress(self, tagger):
        """测试带进度的批量标签"""
        progress_callback = Mock()
        
        tagger.model.predict.return_value = [("tag1", 0.9)]
        
        image_paths = ["/path/1.jpg", "/path/2.jpg", "/path/3.jpg"]
        tagger.batch_tag(image_paths, progress_callback=progress_callback)
        
        assert progress_callback.call_count == 3
    
    def test_batch_tag_async(self, tagger):
        """测试异步批量标签"""
        import asyncio
        
        tagger.model.predict.return_value = [("tag1", 0.9)]
        
        async def test_async():
            image_paths = ["/path/1.jpg", "/path/2.jpg"]
            results = await tagger.batch_tag_async(image_paths)
            return results
        
        results = asyncio.run(test_async())
        assert len(results) == 2


class TestTagManagement:
    """标签管理测试"""
    
    @pytest.fixture
    def tagger(self):
        """创建标签器实例"""
        from ai.auto_tagging.tagger import AutoTagger
        tagger = AutoTagger()
        tagger.db = Mock()
        return tagger
    
    def test_save_tags_to_database(self, tagger):
        """测试保存标签到数据库"""
        tagger.db.execute = Mock(return_value=None)
        
        media_id = 1
        tags = [
            {"tag": "beach", "confidence": 0.95, "category": "scene"},
            {"tag": "ocean", "confidence": 0.88, "category": "scene"}
        ]
        
        result = tagger.save_tags(media_id, tags)
        
        assert result is True
        assert tagger.db.execute.call_count == 2
    
    def test_get_tags_for_media(self, tagger):
        """测试获取媒体的标签"""
        tagger.db.fetch_all = Mock(return_value=[
            {"tag": "beach", "confidence": 0.95, "category": "scene"},
            {"tag": "ocean", "confidence": 0.88, "category": "scene"}
        ])
        
        tags = tagger.get_tags(media_id=1)
        
        assert len(tags) == 2
        assert tags[0]["tag"] == "beach"
    
    def test_update_tags(self, tagger):
        """测试更新标签"""
        tagger.db.execute = Mock(return_value=None)
        
        media_id = 1
        new_tags = [{"tag": "sunset", "confidence": 0.92}]
        
        result = tagger.update_tags(media_id, new_tags)
        
        assert result is True
    
    def test_delete_tags(self, tagger):
        """测试删除标签"""
        tagger.db.execute = Mock(return_value=None)
        
        result = tagger.delete_tags(media_id=1)
        
        assert result is True
    
    def test_get_all_tags(self, tagger):
        """测试获取所有标签"""
        tagger.db.fetch_all = Mock(return_value=[
            {"tag": "beach", "count": 50},
            {"tag": "mountain", "count": 30},
            {"tag": "city", "count": 20}
        ])
        
        tags = tagger.get_all_tags()
        
        assert len(tags) == 3
        assert tags[0]["count"] == 50


class TestTagSearch:
    """标签搜索测试"""
    
    @pytest.fixture
    def tagger(self):
        """创建标签器实例"""
        from ai.auto_tagging.tagger import AutoTagger
        tagger = AutoTagger()
        tagger.db = Mock()
        return tagger
    
    def test_search_by_single_tag(self, tagger):
        """测试按单个标签搜索"""
        tagger.db.fetch_all = Mock(return_value=[
            {"id": 1, "file_path": "/path/1.jpg"},
            {"id": 2, "file_path": "/path/2.jpg"}
        ])
        
        results = tagger.search_by_tag("beach")
        
        assert len(results) == 2
    
    def test_search_by_multiple_tags(self, tagger):
        """测试按多个标签搜索"""
        tagger.db.fetch_all = Mock(return_value=[
            {"id": 1, "file_path": "/path/1.jpg"}
        ])
        
        results = tagger.search_by_tags(["beach", "sunset"], match_all=True)
        
        assert len(results) == 1
    
    def test_search_by_tag_category(self, tagger):
        """测试按标签类别搜索"""
        tagger.db.fetch_all = Mock(return_value=[
            {"id": 1, "tag": "beach", "category": "scene"},
            {"id": 2, "tag": "mountain", "category": "scene"}
        ])
        
        results = tagger.search_by_category("scene")
        
        assert len(results) == 2
    
    def test_get_similar_tags(self, tagger):
        """测试获取相似标签"""
        similar_tags = tagger.get_similar_tags("beach")
        
        assert isinstance(similar_tags, list)


class TestTagConfidence:
    """标签置信度测试"""
    
    @pytest.fixture
    def tagger(self):
        """创建标签器实例"""
        from ai.auto_tagging.tagger import AutoTagger
        return AutoTagger()
    
    def test_filter_by_confidence(self, tagger):
        """测试按置信度过滤"""
        tags = [
            {"tag": "beach", "confidence": 0.95},
            {"tag": "ocean", "confidence": 0.45},
            {"tag": "sand", "confidence": 0.88}
        ]
        
        filtered = tagger.filter_by_confidence(tags, min_confidence=0.5)
        
        assert len(filtered) == 2
        assert "ocean" not in [t["tag"] for t in filtered]
    
    def test_adjust_confidence_threshold(self, tagger):
        """测试调整置信度阈值"""
        tagger.set_confidence_threshold(0.7)
        
        assert tagger.confidence_threshold == 0.7
    
    def test_get_high_confidence_tags(self, tagger):
        """测试获取高置信度标签"""
        tags = [
            {"tag": "beach", "confidence": 0.95},
            {"tag": "ocean", "confidence": 0.88},
            {"tag": "sand", "confidence": 0.45}
        ]
        
        high_conf = tagger.get_high_confidence_tags(tags, threshold=0.8)
        
        assert len(high_conf) == 2


class TestAutoTaggingPipeline:
    """自动标签完整流程测试"""
    
    @pytest.fixture
    def tagger(self):
        """创建标签器实例"""
        from ai.auto_tagging.tagger import AutoTagger
        tagger = AutoTagger()
        tagger.model = Mock()
        tagger.face_recognition = Mock()
        tagger.db = Mock()
        return tagger
    
    def test_full_tagging_pipeline(self, tagger):
        """测试完整标签流程"""
        # 模拟各种检测结果
        tagger.model.predict.return_value = [
            ("beach", 0.95),
            ("ocean", 0.88)
        ]
        tagger.model.detect_objects.return_value = [
            {"label": "person", "confidence": 0.92}
        ]
        tagger.face_recognition.detect_faces.return_value = [
            {"age": 30}
        ]
        tagger.db.execute = Mock(return_value=None)
        
        mock_image = Mock()
        tags = tagger.auto_tag(mock_image, media_id=1)
        
        # 应该包含场景、物体、人物标签
        tag_names = [t["tag"] for t in tags]
        assert "beach" in tag_names or "ocean" in tag_names
        assert "person" in tag_names or "adult" in tag_names
    
    def test_tagging_with_excluded_categories(self, tagger):
        """测试排除某些类别的标签"""
        mock_image = Mock()
        tags = tagger.auto_tag(
            mock_image,
            exclude_categories=["activity"]
        )
        
        # 结果中不应该有活动标签
        for tag in tags:
            assert tag.get("category") != "activity"
    
    def test_tagging_with_max_tags(self, tagger):
        """测试限制最大标签数"""
        tagger.model.predict.return_value = [
            (f"tag_{i}", 0.9 - i * 0.05) for i in range(20)
        ]
        
        mock_image = Mock()
        tags = tagger.auto_tag(mock_image, max_tags=5)
        
        assert len(tags) <= 5
