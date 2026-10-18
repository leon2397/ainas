"""
管理员API集成测试
"""
import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import Mock, patch


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
async def admin_headers(async_client):
    """获取管理员认证头"""
    response = await async_client.post("/api/auth/login", json={
        "username": "admin",
        "password": "admin123"
    })
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def operator_headers(async_client):
    """获取操作员认证头"""
    response = await async_client.post("/api/auth/login", json={
        "username": "operator",
        "password": "operator123"
    })
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestUserManagement:
    """用户管理API测试"""
    
    @pytest.mark.asyncio
    async def test_list_users(self, async_client, admin_headers):
        """测试获取用户列表"""
        response = await async_client.get("/api/admin/users", headers=admin_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "users" in data
        assert "total" in data
        assert isinstance(data["users"], list)
    
    @pytest.mark.asyncio
    async def test_list_users_with_pagination(self, async_client, admin_headers):
        """测试分页获取用户列表"""
        response = await async_client.get(
            "/api/admin/users?skip=0&limit=10",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["users"]) <= 10
    
    @pytest.mark.asyncio
    async def test_list_users_with_search(self, async_client, admin_headers):
        """测试搜索用户"""
        response = await async_client.get(
            "/api/admin/users?search=admin",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        # 应该包含admin用户
        assert any(user["username"] == "admin" for user in data["users"])
    
    @pytest.mark.asyncio
    async def test_create_user(self, async_client, admin_headers):
        """测试创建用户"""
        response = await async_client.post(
            "/api/admin/users",
            headers=admin_headers,
            json={
                "username": "new_test_user",
                "email": "test@example.com",
                "password": "password123",
                "role": "viewer"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "new_test_user"
        assert data["role"] == "viewer"
    
    @pytest.mark.asyncio
    async def test_create_user_duplicate_username(self, async_client, admin_headers):
        """测试创建重复用户"""
        response = await async_client.post(
            "/api/admin/users",
            headers=admin_headers,
            json={
                "username": "admin",  # 已存在的用户
                "email": "admin2@example.com",
                "password": "password123"
            }
        )
        
        assert response.status_code == 400
        assert "error" in response.json()
    
    @pytest.mark.asyncio
    async def test_get_user_detail(self, async_client, admin_headers):
        """测试获取用户详情"""
        # 先获取用户列表找到ID
        list_response = await async_client.get("/api/admin/users", headers=admin_headers)
        users = list_response.json()["users"]
        
        if users:
            user_id = users[0]["id"]
            response = await async_client.get(
                f"/api/admin/users/{user_id}",
                headers=admin_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == user_id
    
    @pytest.mark.asyncio
    async def test_update_user(self, async_client, admin_headers):
        """测试更新用户"""
        # 先创建一个用户
        create_response = await async_client.post(
            "/api/admin/users",
            headers=admin_headers,
            json={
                "username": "user_to_update",
                "email": "update@example.com",
                "password": "password123"
            }
        )
        
        if create_response.status_code == 200:
            user_id = create_response.json()["id"]
            
            response = await async_client.put(
                f"/api/admin/users/{user_id}",
                headers=admin_headers,
                json={
                    "email": "updated@example.com",
                    "is_active": False
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["email"] == "updated@example.com"
            assert data["is_active"] is False
    
    @pytest.mark.asyncio
    async def test_delete_user(self, async_client, admin_headers):
        """测试删除用户"""
        # 先创建一个用户
        create_response = await async_client.post(
            "/api/admin/users",
            headers=admin_headers,
            json={
                "username": "user_to_delete",
                "email": "delete@example.com",
                "password": "password123"
            }
        )
        
        if create_response.status_code == 200:
            user_id = create_response.json()["id"]
            
            response = await async_client.delete(
                f"/api/admin/users/{user_id}",
                headers=admin_headers
            )
            
            assert response.status_code == 200
            
            # 验证用户已删除
            get_response = await async_client.get(
                f"/api/admin/users/{user_id}",
                headers=admin_headers
            )
            assert get_response.status_code == 404


class TestRoleManagement:
    """角色管理API测试"""
    
    @pytest.mark.asyncio
    async def test_list_roles(self, async_client, admin_headers):
        """测试获取角色列表"""
        response = await async_client.get("/api/admin/roles", headers=admin_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # 应该包含系统角色
        role_names = [r["name"] for r in data]
        assert "super_admin" in role_names or "admin" in role_names
    
    @pytest.mark.asyncio
    async def test_get_role_permissions(self, async_client, admin_headers):
        """测试获取角色权限"""
        response = await async_client.get(
            "/api/admin/roles/admin/permissions",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "permissions" in data
        assert isinstance(data["permissions"], list)
    
    @pytest.mark.asyncio
    async def test_assign_role_to_user(self, async_client, admin_headers):
        """测试分配角色给用户"""
        # 先创建一个用户
        create_response = await async_client.post(
            "/api/admin/users",
            headers=admin_headers,
            json={
                "username": "role_test_user",
                "email": "role@example.com",
                "password": "password123"
            }
        )
        
        if create_response.status_code == 200:
            user_id = create_response.json()["id"]
            
            response = await async_client.post(
                f"/api/admin/users/{user_id}/role",
                headers=admin_headers,
                json={"role": "operator"}
            )
            
            assert response.status_code == 200
            
            # 验证角色已分配
            user_response = await async_client.get(
                f"/api/admin/users/{user_id}",
                headers=admin_headers
            )
            assert user_response.json()["role"] == "operator"
    
    @pytest.mark.asyncio
    async def test_update_role_permissions(self, async_client, admin_headers):
        """测试更新角色权限"""
        response = await async_client.put(
            "/api/admin/roles/operator/permissions",
            headers=admin_headers,
            json={
                "permissions": ["media:*", "album:*", "device:read"]
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "media:*" in data["permissions"]


class TestAuditLogAPI:
    """审计日志API测试"""
    
    @pytest.mark.asyncio
    async def test_list_audit_logs(self, async_client, admin_headers):
        """测试获取审计日志列表"""
        response = await async_client.get("/api/admin/audit-logs", headers=admin_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "logs" in data
        assert "total" in data
    
    @pytest.mark.asyncio
    async def test_list_audit_logs_with_filter(self, async_client, admin_headers):
        """测试过滤审计日志"""
        response = await async_client.get(
            "/api/admin/audit-logs?category=AUTH&level=INFO",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        # 所有返回的日志应该符合过滤条件
        for log in data["logs"]:
            assert log["category"] == "AUTH"
            assert log["level"] == "INFO"
    
    @pytest.mark.asyncio
    async def test_get_audit_stats(self, async_client, admin_headers):
        """测试获取审计统计"""
        response = await async_client.get("/api/admin/audit-stats", headers=admin_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "total_logs" in data
        assert "today_logs" in data
        assert "error_logs" in data
    
    @pytest.mark.asyncio
    async def test_export_audit_logs_json(self, async_client, admin_headers):
        """测试导出审计日志为JSON"""
        response = await async_client.post(
            "/api/admin/audit-logs/export",
            headers=admin_headers,
            params={"format": "json"}
        )
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
    
    @pytest.mark.asyncio
    async def test_export_audit_logs_csv(self, async_client, admin_headers):
        """测试导出审计日志为CSV"""
        response = await async_client.post(
            "/api/admin/audit-logs/export",
            headers=admin_headers,
            params={"format": "csv"}
        )
        
        assert response.status_code == 200
        assert "text/csv" in response.headers["content-type"]


class TestSystemConfig:
    """系统配置API测试"""
    
    @pytest.mark.asyncio
    async def test_get_system_config(self, async_client, admin_headers):
        """测试获取系统配置"""
        response = await async_client.get("/api/admin/system-config", headers=admin_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
    
    @pytest.mark.asyncio
    async def test_update_system_config(self, async_client, admin_headers):
        """测试更新系统配置"""
        response = await async_client.put(
            "/api/admin/system-config",
            headers=admin_headers,
            json={
                "max_upload_size": 104857600,
                "allowed_formats": ["jpg", "png", "mp4"]
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["max_upload_size"] == 104857600
    
    @pytest.mark.asyncio
    async def test_get_system_stats(self, async_client, admin_headers):
        """测试获取系统统计"""
        response = await async_client.get("/api/admin/system-stats", headers=admin_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "storage" in data
        assert "media_count" in data
        assert "user_count" in data


class TestPermissionControl:
    """权限控制测试"""
    
    @pytest.mark.asyncio
    async def test_operator_cannot_access_admin_api(self, async_client, operator_headers):
        """测试操作员不能访问管理员API"""
        response = await async_client.get("/api/admin/users", headers=operator_headers)
        
        assert response.status_code == 403
    
    @pytest.mark.asyncio
    async def test_operator_cannot_create_user(self, async_client, operator_headers):
        """测试操作员不能创建用户"""
        response = await async_client.post(
            "/api/admin/users",
            headers=operator_headers,
            json={
                "username": "should_fail",
                "email": "fail@example.com",
                "password": "password123"
            }
        )
        
        assert response.status_code == 403
    
    @pytest.mark.asyncio
    async def test_admin_can_access_all_apis(self, async_client, admin_headers):
        """测试管理员可以访问所有API"""
        endpoints = [
            "/api/admin/users",
            "/api/admin/roles",
            "/api/admin/audit-logs",
            "/api/admin/system-config"
        ]
        
        for endpoint in endpoints:
            response = await async_client.get(endpoint, headers=admin_headers)
            assert response.status_code == 200, f"Failed to access {endpoint}"
    
    @pytest.mark.asyncio
    async def test_cannot_delete_super_admin(self, async_client, admin_headers):
        """测试不能删除超级管理员"""
        # 假设ID为1的是超级管理员
        response = await async_client.delete(
            "/api/admin/users/1",
            headers=admin_headers
        )
        
        assert response.status_code == 403


class TestAdminDashboard:
    """管理员仪表板测试"""
    
    @pytest.mark.asyncio
    async def test_get_dashboard_summary(self, async_client, admin_headers):
        """测试获取仪表板摘要"""
        response = await async_client.get("/api/admin/dashboard", headers=admin_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "total_users" in data
        assert "total_media" in data
        assert "total_albums" in data
        assert "recent_activities" in data
    
    @pytest.mark.asyncio
    async def test_get_recent_activities(self, async_client, admin_headers):
        """测试获取最近活动"""
        response = await async_client.get(
            "/api/admin/activities?limit=10",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 10
    
    @pytest.mark.asyncio
    async def test_get_system_health(self, async_client, admin_headers):
        """测试获取系统健康状态"""
        response = await async_client.get("/api/admin/health", headers=admin_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "services" in data
        assert "database" in data["services"]
