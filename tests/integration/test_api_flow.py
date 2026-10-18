"""
集成测试 - API流程测试
"""
import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import Mock, AsyncMock, patch


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


class TestAuthFlow:
    """认证流程集成测试"""
    
    @pytest.mark.asyncio
    async def test_login_flow(self, async_client):
        """测试完整登录流程"""
        # 1. 登录获取token
        response = await async_client.post("/api/auth/login", json={
            "username": "admin",
            "password": "admin123"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        
        token = data["access_token"]
        
        # 2. 使用token访问受保护接口
        response = await async_client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        user = response.json()
        assert user["username"] == "admin"
    
    @pytest.mark.asyncio
    async def test_invalid_login(self, async_client):
        """测试无效登录"""
        response = await async_client.post("/api/auth/login", json={
            "username": "admin",
            "password": "wrong_password"
        })
        
        assert response.status_code == 401
        assert "error" in response.json()
    
    @pytest.mark.asyncio
    async def test_access_without_token(self, async_client):
        """测试无token访问"""
        response = await async_client.get("/api/auth/me")
        
        assert response.status_code == 401


class TestMediaFlow:
    """媒体流程集成测试"""
    
    @pytest.fixture
    async def auth_headers(self, async_client):
        """获取认证头"""
        response = await async_client.post("/api/auth/login", json={
            "username": "admin",
            "password": "admin123"
        })
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    @pytest.mark.asyncio
    async def test_media_crud_flow(self, async_client, auth_headers):
        """测试媒体CRUD流程"""
        # 1. 获取媒体列表（空）
        response = await async_client.get("/api/media/", headers=auth_headers)
        assert response.status_code == 200
        initial_count = len(response.json())
        
        # 2. 扫描媒体（模拟）
        response = await async_client.post(
            "/api/actions/scan",
            headers=auth_headers,
            json={"path": "./test_data", "recursive": True}
        )
        assert response.status_code == 200
        
        # 3. 获取媒体列表（应该有数据）
        response = await async_client.get("/api/media/", headers=auth_headers)
        assert response.status_code == 200
        # 注意：实际测试需要准备测试数据
    
    @pytest.mark.asyncio
    async def test_search_media(self, async_client, auth_headers):
        """测试搜索媒体"""
        response = await async_client.get(
            "/api/media/search/?keyword=test",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        assert isinstance(response.json(), list)


class TestAlbumFlow:
    """相册流程集成测试"""
    
    @pytest.fixture
    async def auth_headers(self, async_client):
        """获取认证头"""
        response = await async_client.post("/api/auth/login", json={
            "username": "admin",
            "password": "admin123"
        })
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    @pytest.mark.asyncio
    async def test_create_and_manage_album(self, async_client, auth_headers):
        """测试创建和管理相册"""
        # 1. 创建相册
        response = await async_client.post(
            "/api/albums/",
            headers=auth_headers,
            json={
                "name": "测试相册",
                "album_type": "custom",
                "description": "用于测试的相册"
            }
        )
        
        assert response.status_code == 200
        album = response.json()
        album_id = album["id"]
        assert album["name"] == "测试相册"
        
        # 2. 获取相册详情
        response = await async_client.get(
            f"/api/albums/{album_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        assert response.json()["id"] == album_id
        
        # 3. 删除相册
        response = await async_client.delete(
            f"/api/albums/{album_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200


class TestDeviceFlow:
    """设备流程集成测试"""
    
    @pytest.fixture
    async def auth_headers(self, async_client):
        """获取认证头"""
        response = await async_client.post("/api/auth/login", json={
            "username": "admin",
            "password": "admin123"
        })
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    @pytest.mark.asyncio
    async def test_device_lifecycle(self, async_client, auth_headers):
        """测试设备生命周期"""
        # 1. 添加设备
        response = await async_client.post(
            "/api/devices/add",
            headers=auth_headers,
            json={
                "device_id": "test-device-001",
                "device_name": "测试设备",
                "ip": "192.168.1.100",
                "port": 8000,
                "npu_type": "cpu"
            }
        )
        
        assert response.status_code == 200
        
        # 2. 获取设备列表
        response = await async_client.get("/api/devices/", headers=auth_headers)
        assert response.status_code == 200
        devices = response.json()
        assert any(d["device_id"] == "test-device-001" for d in devices)
        
        # 3. 发送心跳
        response = await async_client.post(
            "/api/devices/heartbeat",
            headers=auth_headers,
            params={
                "device_id": "test-device-001",
                "cpu_usage": 30.5,
                "memory_usage": 45.2
            }
        )
        
        assert response.status_code == 200
        
        # 4. 删除设备
        response = await async_client.delete(
            "/api/devices/test-device-001",
            headers=auth_headers
        )
        
        assert response.status_code == 200


class TestTaskFlow:
    """任务流程集成测试"""
    
    @pytest.fixture
    async def auth_headers(self, async_client):
        """获取认证头"""
        response = await async_client.post("/api/auth/login", json={
            "username": "admin",
            "password": "admin123"
        })
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    @pytest.mark.asyncio
    async def test_task_operations(self, async_client, auth_headers):
        """测试任务操作"""
        # 1. 获取任务列表
        response = await async_client.get("/api/tasks/", headers=auth_headers)
        assert response.status_code == 200
        
        # 2. 创建分类任务（通过actions）
        response = await async_client.post(
            "/api/actions/classify",
            headers=auth_headers,
            json={"file_id": None, "device_id": None, "force": False}
        )
        
        assert response.status_code == 200
        task = response.json()
        task_id = task.get("task_id")
        
        if task_id:
            # 3. 获取任务详情
            response = await async_client.get(
                f"/api/tasks/{task_id}",
                headers=auth_headers
            )
            assert response.status_code == 200


class TestSystemEndpoints:
    """系统端点测试"""
    
    @pytest.mark.asyncio
    async def test_health_check(self, async_client):
        """测试健康检查"""
        response = await async_client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
    
    @pytest.mark.asyncio
    async def test_status_endpoint(self, async_client):
        """测试状态端点"""
        response = await async_client.get("/status")
        
        assert response.status_code == 200
        data = response.json()
        assert "version" in data
        assert "uptime" in data
