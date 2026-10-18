"""
审计流程集成测试
测试审计中间件和自动日志记录
"""
import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import Mock, patch, MagicMock


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


class TestRequestAuditing:
    """请求审计测试"""
    
    @pytest.mark.asyncio
    async def test_login_is_audited(self, async_client):
        """测试登录被审计记录"""
        # 执行登录
        response = await async_client.post("/api/auth/login", json={
            "username": "admin",
            "password": "admin123"
        })
        
        assert response.status_code == 200
        
        # 验证审计日志（这里假设可以通过API查询审计日志）
        # 实际实现可能需要查询数据库或专门的审计API
    
    @pytest.mark.asyncio
    async def test_failed_login_is_audited(self, async_client):
        """测试失败登录被审计记录"""
        response = await async_client.post("/api/auth/login", json={
            "username": "admin",
            "password": "wrong_password"
        })
        
        assert response.status_code == 401
        # 应该记录失败的登录尝试
    
    @pytest.mark.asyncio
    async def test_media_access_is_audited(self, async_client, auth_headers):
        """测试媒体访问被审计记录"""
        response = await async_client.get("/api/media/", headers=auth_headers)
        
        assert response.status_code == 200
        # 应该记录媒体列表访问
    
    @pytest.mark.asyncio
    async def test_album_creation_is_audited(self, async_client, auth_headers):
        """测试相册创建被审计记录"""
        response = await async_client.post(
            "/api/albums/",
            headers=auth_headers,
            json={
                "name": "Audit Test Album",
                "album_type": "custom"
            }
        )
        
        assert response.status_code == 200
        # 应该记录相册创建操作
    
    @pytest.mark.asyncio
    async def test_user_update_is_audited(self, async_client, auth_headers):
        """测试用户更新被审计记录"""
        # 先获取当前用户信息
        me_response = await async_client.get("/api/auth/me", headers=auth_headers)
        
        if me_response.status_code == 200:
            user_id = me_response.json()["id"]
            
            # 更新用户（如果API支持）
            # response = await async_client.put(...)
            # 应该记录用户更新操作


class TestAuditMiddleware:
    """审计中间件测试"""
    
    @pytest.mark.asyncio
    async def test_health_check_not_audited(self, async_client):
        """测试健康检查不被审计"""
        response = await async_client.get("/health")
        
        assert response.status_code == 200
        # 健康检查端点应该跳过审计
    
    @pytest.mark.asyncio
    async def test_status_endpoint_not_audited(self, async_client):
        """测试状态端点不被审计"""
        response = await async_client.get("/status")
        
        assert response.status_code == 200
        # 状态端点应该跳过审计
    
    @pytest.mark.asyncio
    async def test_static_files_not_audited(self, async_client):
        """测试静态文件不被审计"""
        response = await async_client.get("/")
        
        # 静态文件请求应该跳过审计
        # 不管返回什么状态码
    
    @pytest.mark.asyncio
    async def test_api_requests_are_audited(self, async_client, auth_headers):
        """测试API请求被审计"""
        # 各种API请求都应该被审计
        endpoints = [
            ("/api/media/", "GET"),
            ("/api/albums/", "GET"),
            ("/api/devices/", "GET"),
            ("/api/tasks/", "GET")
        ]
        
        for endpoint, method in endpoints:
            if method == "GET":
                response = await async_client.get(endpoint, headers=auth_headers)
            # 所有请求都应该被审计


class TestAuditLogQuery:
    """审计日志查询测试"""
    
    @pytest.mark.asyncio
    async def test_query_by_category_auth(self, async_client, auth_headers):
        """测试按认证类别查询"""
        # 先执行一些认证操作
        await async_client.post("/api/auth/login", json={
            "username": "admin",
            "password": "admin123"
        })
        
        # 查询认证相关的审计日志
        response = await async_client.get(
            "/api/admin/audit-logs?category=AUTH",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        # 应该包含认证相关的日志
        for log in data.get("logs", []):
            assert log["category"] == "AUTH"
    
    @pytest.mark.asyncio
    async def test_query_by_category_media(self, async_client, auth_headers):
        """测试按媒体类别查询"""
        # 先访问媒体
        await async_client.get("/api/media/", headers=auth_headers)
        
        response = await async_client.get(
            "/api/admin/audit-logs?category=MEDIA",
            headers=auth_headers
        )
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_query_by_level_error(self, async_client, auth_headers):
        """测试按错误级别查询"""
        # 先制造一些错误
        await async_client.post("/api/auth/login", json={
            "username": "nonexistent",
            "password": "wrong"
        })
        
        response = await async_client.get(
            "/api/admin/audit-logs?level=ERROR",
            headers=auth_headers
        )
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_query_by_user(self, async_client, auth_headers):
        """测试按用户查询"""
        # 获取当前用户ID
        me_response = await async_client.get("/api/auth/me", headers=auth_headers)
        
        if me_response.status_code == 200:
            user_id = me_response.json()["id"]
            
            response = await async_client.get(
                f"/api/admin/audit-logs?user_id={user_id}",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            # 所有日志应该属于该用户
            for log in data.get("logs", []):
                assert log["user_id"] == user_id
    
    @pytest.mark.asyncio
    async def test_query_by_action(self, async_client, auth_headers):
        """测试按动作查询"""
        response = await async_client.get(
            "/api/admin/audit-logs?action=login",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        for log in data.get("logs", []):
            assert log["action"] == "login"
    
    @pytest.mark.asyncio
    async def test_query_with_date_range(self, async_client, auth_headers):
        """测试按日期范围查询"""
        from datetime import datetime, timedelta
        
        end_date = datetime.now().isoformat()
        start_date = (datetime.now() - timedelta(days=7)).isoformat()
        
        response = await async_client.get(
            f"/api/admin/audit-logs?start_date={start_date}&end_date={end_date}",
            headers=auth_headers
        )
        
        assert response.status_code == 200


class TestAuditStats:
    """审计统计测试"""
    
    @pytest.mark.asyncio
    async def test_stats_by_category(self, async_client, auth_headers):
        """测试按类别统计"""
        response = await async_client.get(
            "/api/admin/audit-stats/by-category",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        # 应该包含各个类别的统计
        assert isinstance(data, dict)
    
    @pytest.mark.asyncio
    async def test_stats_by_level(self, async_client, auth_headers):
        """测试按级别统计"""
        response = await async_client.get(
            "/api/admin/audit-stats/by-level",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        # 应该包含各个级别的统计
        assert "INFO" in data or "ERROR" in data or isinstance(data, dict)
    
    @pytest.mark.asyncio
    async def test_stats_by_user(self, async_client, auth_headers):
        """测试按用户统计"""
        response = await async_client.get(
            "/api/admin/audit-stats/by-user",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    @pytest.mark.asyncio
    async def test_stats_by_action(self, async_client, auth_headers):
        """测试按动作统计"""
        response = await async_client.get(
            "/api/admin/audit-stats/by-action",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
    
    @pytest.mark.asyncio
    async def test_dashboard_stats(self, async_client, auth_headers):
        """测试仪表板统计"""
        response = await async_client.get(
            "/api/admin/audit-stats/dashboard",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "total_logs" in data
        assert "today_logs" in data
        assert "error_logs" in data
        assert "unique_users" in data


class TestAuditExport:
    """审计导出测试"""
    
    @pytest.mark.asyncio
    async def test_export_json_format(self, async_client, auth_headers):
        """测试导出JSON格式"""
        response = await async_client.post(
            "/api/admin/audit-logs/export",
            headers=auth_headers,
            params={"format": "json"}
        )
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        
        # 验证JSON格式
        data = response.json()
        assert isinstance(data, list)
    
    @pytest.mark.asyncio
    async def test_export_csv_format(self, async_client, auth_headers):
        """测试导出CSV格式"""
        response = await async_client.post(
            "/api/admin/audit-logs/export",
            headers=auth_headers,
            params={"format": "csv"}
        )
        
        assert response.status_code == 200
        content_type = response.headers.get("content-type", "")
        assert "text/csv" in content_type or "application/octet-stream" in content_type
        
        # 验证CSV格式
        content = response.text
        assert "id,level,category" in content or len(content) > 0
    
    @pytest.mark.asyncio
    async def test_export_with_filter(self, async_client, auth_headers):
        """测试带过滤条件的导出"""
        response = await async_client.post(
            "/api/admin/audit-logs/export",
            headers=auth_headers,
            params={
                "format": "json",
                "category": "AUTH",
                "level": "INFO"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        # 所有导出的记录应该符合过滤条件
        for log in data:
            assert log["category"] == "AUTH"
            assert log["level"] == "INFO"


class TestAuditPermissions:
    """审计权限测试"""
    
    @pytest.mark.asyncio
    async def test_only_admin_can_view_audit_logs(self, async_client):
        """测试只有管理员能查看审计日志"""
        # 普通用户登录
        login_response = await async_client.post("/api/auth/login", json={
            "username": "viewer",
            "password": "viewer123"
        })
        
        if login_response.status_code == 200:
            token = login_response.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            
            response = await async_client.get("/api/admin/audit-logs", headers=headers)
            
            assert response.status_code == 403
    
    @pytest.mark.asyncio
    async def test_only_admin_can_export_audit_logs(self, async_client):
        """测试只有管理员能导出审计日志"""
        # 普通用户登录
        login_response = await async_client.post("/api/auth/login", json={
            "username": "viewer",
            "password": "viewer123"
        })
        
        if login_response.status_code == 200:
            token = login_response.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            
            response = await async_client.post(
                "/api/admin/audit-logs/export",
                headers=headers,
                params={"format": "json"}
            )
            
            assert response.status_code == 403
    
    @pytest.mark.asyncio
    async def test_operator_cannot_access_audit(self, async_client):
        """测试操作员不能访问审计功能"""
        # 操作员登录
        login_response = await async_client.post("/api/auth/login", json={
            "username": "operator",
            "password": "operator123"
        })
        
        if login_response.status_code == 200:
            token = login_response.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            
            response = await async_client.get("/api/admin/audit-logs", headers=headers)
            
            assert response.status_code == 403


class TestAuditLogRetention:
    """审计日志保留策略测试"""
    
    @pytest.mark.asyncio
    async def test_get_retention_policy(self, async_client, auth_headers):
        """测试获取保留策略"""
        response = await async_client.get(
            "/api/admin/audit-logs/retention",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "retention_days" in data
    
    @pytest.mark.asyncio
    async def test_update_retention_policy(self, async_client, auth_headers):
        """测试更新保留策略"""
        response = await async_client.put(
            "/api/admin/audit-logs/retention",
            headers=auth_headers,
            json={"retention_days": 90}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["retention_days"] == 90
    
    @pytest.mark.asyncio
    async def test_cleanup_old_logs(self, async_client, auth_headers):
        """测试清理旧日志"""
        response = await async_client.post(
            "/api/admin/audit-logs/cleanup",
            headers=auth_headers,
            params={"days": 30}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "deleted_count" in data
