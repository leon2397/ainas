"""
AI功能API集成测试
"""
import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import Mock, patch
import json


@pytest.fixture(scope="module")
def event_loop():
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
async def test_app():
    """创建测试应用"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))
    
    from main import app
    return app


@pytest.fixture
async def async_client(test_app):
    """创建异步测试客户端"""
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
async def auth_headers(async_client):
    """获取认证头"""
    response = await async_client.post("/api/auth/login", json={
        "username": "admin",
        "password": "admin123"
    })
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestFaceRecognitionAPI:
    """人脸识别API测试"""
    
    @pytest.mark.asyncio
    async def test_detect_faces_api(self, async_client, auth_headers):
        """测试人脸检测API"""
        # 模拟上传图片
        response = await async_client.post(
            "/api/ai/faces/detect",
            headers=auth_headers,
            files={"file": ("test.jpg", b"fake_image_data", "image/jpeg")}
        )
        
        assert response.status_code in [200, 202]  # 接受或处理中
    
    @pytest.mark.asyncio
    async def test_recognize_faces_api(self, async_client, auth_headers):
        """测试人脸识别API"""
        response = await async_client.post(
            "/api/ai/faces/recognize",
            headers=auth_headers,
            files={"file": ("test.jpg", b"fake_image_data", "image/jpeg")}
        )
        
        assert response.status_code in [200, 202]
    
    @pytest.mark.asyncio
    async def test_get_faces_list(self, async_client, auth_headers):
        """测试获取人脸列表API"""
        response = await async_client.get("/api/ai/faces", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    @pytest.mark.asyncio
    async def test_get_faces_by_person(self, async_client, auth_headers):
        """测试按人物获取人脸API"""
        response = await async_client.get(
            "/api/ai/faces?person_name=张三",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    @pytest.mark.asyncio
    async def test_assign_person_name(self, async_client, auth_headers):
        """测试分配人名API"""
        response = await async_client.post(
            "/api/ai/faces/1/assign",
            headers=auth_headers,
            json={"person_name": "张三"}
        )
        
        assert response.status_code in [200, 404]  # 成功或人脸不存在
    
    @pytest.mark.asyncio
    async def test_cluster_faces_api(self, async_client, auth_headers):
        """测试人脸聚类API"""
        response = await async_client.post(
            "/api/ai/faces/cluster",
            headers=auth_headers,
            json={"n_clusters": 5}
        )
        
        assert response.status_code in [200, 202]
    
    @pytest.mark.asyncio
    async def test_get_face_clusters(self, async_client, auth_headers):
        """测试获取人脸聚类API"""
        response = await async_client.get("/api/ai/faces/clusters", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    @pytest.mark.asyncio
    async def test_delete_face(self, async_client, auth_headers):
        """测试删除人脸API"""
        response = await async_client.delete("/api/ai/faces/1", headers=auth_headers)
        
        assert response.status_code in [200, 404]


class TestSmartAlbumAPI:
    """智能相册API测试"""
    
    @pytest.mark.asyncio
    async def test_get_smart_albums(self, async_client, auth_headers):
        """测试获取智能相册列表"""
        response = await async_client.get("/api/ai/smart-albums", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    @pytest.mark.asyncio
    async def test_create_smart_album_by_date(self, async_client, auth_headers):
        """测试按日期创建智能相册"""
        response = await async_client.post(
            "/api/ai/smart-albums",
            headers=auth_headers,
            json={
                "name": "2026年4月",
                "type": "date",
                "criteria": {"year": 2026, "month": 4}
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
    
    @pytest.mark.asyncio
    async def test_create_smart_album_by_person(self, async_client, auth_headers):
        """测试按人物创建智能相册"""
        response = await async_client.post(
            "/api/ai/smart-albums",
            headers=auth_headers,
            json={
                "name": "张三的照片",
                "type": "person",
                "criteria": {"person_name": "张三"}
            }
        )
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_create_smart_album_by_location(self, async_client, auth_headers):
        """测试按地点创建智能相册"""
        response = await async_client.post(
            "/api/ai/smart-albums",
            headers=auth_headers,
            json={
                "name": "北京之旅",
                "type": "location",
                "criteria": {"city": "北京"}
            }
        )
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_refresh_smart_album(self, async_client, auth_headers):
        """测试刷新智能相册"""
        response = await async_client.post(
            "/api/ai/smart-albums/1/refresh",
            headers=auth_headers
        )
        
        assert response.status_code in [200, 404]
    
    @pytest.mark.asyncio
    async def test_delete_smart_album(self, async_client, auth_headers):
        """测试删除智能相册"""
        response = await async_client.delete("/api/ai/smart-albums/1", headers=auth_headers)
        
        assert response.status_code in [200, 404]
    
    @pytest.mark.asyncio
    async def test_get_recommendations(self, async_client, auth_headers):
        """测试获取推荐"""
        response = await async_client.get(
            "/api/ai/recommendations",
            headers=auth_headers,
            params={"type": "time", "limit": 10}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    @pytest.mark.asyncio
    async def test_get_daily_recommendations(self, async_client, auth_headers):
        """测试获取每日推荐"""
        response = await async_client.get(
            "/api/ai/recommendations/daily",
            headers=auth_headers
        )
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_get_memory_flashback(self, async_client, auth_headers):
        """测试获取回忆闪回"""
        response = await async_client.get(
            "/api/ai/recommendations/memory",
            headers=auth_headers,
            params={"years_ago": 1}
        )
        
        assert response.status_code == 200


class TestAutoTaggingAPI:
    """自动标签API测试"""
    
    @pytest.mark.asyncio
    async def test_auto_tag_image(self, async_client, auth_headers):
        """测试自动标签图片"""
        response = await async_client.post(
            "/api/ai/tags/auto",
            headers=auth_headers,
            json={"media_id": 1}
        )
        
        assert response.status_code in [200, 202]
    
    @pytest.mark.asyncio
    async def test_batch_auto_tag(self, async_client, auth_headers):
        """测试批量自动标签"""
        response = await async_client.post(
            "/api/ai/tags/auto/batch",
            headers=auth_headers,
            json={"media_ids": [1, 2, 3]}
        )
        
        assert response.status_code in [200, 202]
    
    @pytest.mark.asyncio
    async def test_get_tags_for_media(self, async_client, auth_headers):
        """测试获取媒体标签"""
        response = await async_client.get("/api/ai/tags?media_id=1", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    @pytest.mark.asyncio
    async def test_add_manual_tag(self, async_client, auth_headers):
        """测试添加手动标签"""
        response = await async_client.post(
            "/api/ai/tags",
            headers=auth_headers,
            json={
                "media_id": 1,
                "tag": "vacation",
                "confidence": 1.0
            }
        )
        
        assert response.status_code in [200, 201]
    
    @pytest.mark.asyncio
    async def test_delete_tag(self, async_client, auth_headers):
        """测试删除标签"""
        response = await async_client.delete("/api/ai/tags/1", headers=auth_headers)
        
        assert response.status_code in [200, 404]
    
    @pytest.mark.asyncio
    async def test_search_by_tag(self, async_client, auth_headers):
        """测试按标签搜索"""
        response = await async_client.get(
            "/api/ai/tags/search?tag=beach",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    @pytest.mark.asyncio
    async def test_get_all_tags(self, async_client, auth_headers):
        """测试获取所有标签"""
        response = await async_client.get("/api/ai/tags/all", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    @pytest.mark.asyncio
    async def test_get_tags_by_category(self, async_client, auth_headers):
        """测试按类别获取标签"""
        response = await async_client.get(
            "/api/ai/tags/all?category=scene",
            headers=auth_headers
        )
        
        assert response.status_code == 200


class TestSimilarityAPI:
    """相似度检测API测试"""
    
    @pytest.mark.asyncio
    async def test_check_similarity(self, async_client, auth_headers):
        """测试检查相似度"""
        response = await async_client.post(
            "/api/ai/similarity/check",
            headers=auth_headers,
            json={"media_id_1": 1, "media_id_2": 2}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "similarity" in data
    
    @pytest.mark.asyncio
    async def test_find_duplicates(self, async_client, auth_headers):
        """测试查找重复"""
        response = await async_client.post(
            "/api/ai/similarity/duplicates",
            headers=auth_headers,
            json={"threshold": 0.95}
        )
        
        assert response.status_code in [200, 202]
    
    @pytest.mark.asyncio
    async def test_get_duplicate_groups(self, async_client, auth_headers):
        """测试获取重复组"""
        response = await async_client.get(
            "/api/ai/similarity/duplicates",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "duplicates" in data
    
    @pytest.mark.asyncio
    async def test_find_similar_images(self, async_client, auth_headers):
        """测试查找相似图片"""
        response = await async_client.get(
            "/api/ai/similarity/similar?media_id=1&threshold=0.85",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    @pytest.mark.asyncio
    async def test_merge_duplicates(self, async_client, auth_headers):
        """测试合并重复"""
        response = await async_client.post(
            "/api/ai/similarity/merge",
            headers=auth_headers,
            json={
                "keep_id": 1,
                "remove_ids": [2, 3]
            }
        )
        
        assert response.status_code in [200, 400]
    
    @pytest.mark.asyncio
    async def test_get_similarity_report(self, async_client, auth_headers):
        """测试获取相似度报告"""
        response = await async_client.get(
            "/api/ai/similarity/report",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "total_images" in data


class TestAITaskAPI:
    """AI任务API测试"""
    
    @pytest.mark.asyncio
    async def test_get_ai_tasks(self, async_client, auth_headers):
        """测试获取AI任务列表"""
        response = await async_client.get("/api/ai/tasks", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    @pytest.mark.asyncio
    async def test_get_ai_task_status(self, async_client, auth_headers):
        """测试获取AI任务状态"""
        response = await async_client.get("/api/ai/tasks/1", headers=auth_headers)
        
        assert response.status_code in [200, 404]
    
    @pytest.mark.asyncio
    async def test_cancel_ai_task(self, async_client, auth_headers):
        """测试取消AI任务"""
        response = await async_client.post("/api/ai/tasks/1/cancel", headers=auth_headers)
        
        assert response.status_code in [200, 404]


class TestAIStatsAPI:
    """AI统计API测试"""
    
    @pytest.mark.asyncio
    async def test_get_ai_stats(self, async_client, auth_headers):
        """测试获取AI统计"""
        response = await async_client.get("/api/ai/stats", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "faces_detected" in data
        assert "tags_generated" in data
    
    @pytest.mark.asyncio
    async def test_get_face_stats(self, async_client, auth_headers):
        """测试获取人脸统计"""
        response = await async_client.get("/api/ai/stats/faces", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "total_faces" in data
        assert "unique_persons" in data
    
    @pytest.mark.asyncio
    async def test_get_tag_stats(self, async_client, auth_headers):
        """测试获取标签统计"""
        response = await async_client.get("/api/ai/stats/tags", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "total_tags" in data
        assert "tags_by_category" in data


class TestAIPermissions:
    """AI功能权限测试"""
    
    @pytest.mark.asyncio
    async def test_viewer_cannot_trigger_face_recognition(self, async_client):
        """测试查看者不能触发人脸识别"""
        # 以viewer身份登录
        login_response = await async_client.post("/api/auth/login", json={
            "username": "viewer",
            "password": "viewer123"
        })
        
        if login_response.status_code == 200:
            token = login_response.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            
            response = await async_client.post(
                "/api/ai/faces/cluster",
                headers=headers
            )
            
            assert response.status_code == 403
    
    @pytest.mark.asyncio
    async def test_operator_can_use_ai_features(self, async_client):
        """测试操作员可以使用AI功能"""
        login_response = await async_client.post("/api/auth/login", json={
            "username": "operator",
            "password": "operator123"
        })
        
        if login_response.status_code == 200:
            token = login_response.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            
            # 操作员应该可以查看AI结果
            response = await async_client.get("/api/ai/faces", headers=headers)
            
            assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_guest_cannot_access_ai_api(self, async_client):
        """测试访客不能访问AI API"""
        login_response = await async_client.post("/api/auth/login", json={
            "username": "guest",
            "password": "guest123"
        })
        
        if login_response.status_code == 200:
            token = login_response.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            
            response = await async_client.get("/api/ai/faces", headers=headers)
            
            assert response.status_code == 403


class TestAIConfiguration:
    """AI配置测试"""
    
    @pytest.mark.asyncio
    async def test_get_ai_config(self, async_client, auth_headers):
        """测试获取AI配置"""
        response = await async_client.get("/api/ai/config", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "enabled_features" in data
    
    @pytest.mark.asyncio
    async def test_update_ai_config(self, async_client, auth_headers):
        """测试更新AI配置"""
        response = await async_client.put(
            "/api/ai/config",
            headers=auth_headers,
            json={
                "face_recognition_enabled": True,
                "auto_tagging_enabled": True,
                "similarity_detection_enabled": False
            }
        )
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_get_npu_status(self, async_client, auth_headers):
        """测试获取NPU状态"""
        response = await async_client.get("/api/ai/npu/status", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "available" in data
        assert "type" in data
