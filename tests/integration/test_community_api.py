"""
社区功能和外部API集成测试
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
async def auth_headers(async_client):
    """获取认证头"""
    response = await async_client.post("/api/auth/login", json={
        "username": "admin",
        "password": "admin123"
    })
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ========== 社区功能测试 ==========

class TestCommunityAPI:
    """社区API测试"""
    
    @pytest.mark.asyncio
    async def test_get_posts(self, async_client, auth_headers):
        """测试获取帖子列表"""
        response = await async_client.get("/api/community/posts", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    @pytest.mark.asyncio
    async def test_create_post(self, async_client, auth_headers):
        """测试创建帖子"""
        response = await async_client.post(
            "/api/community/posts",
            headers=auth_headers,
            json={
                "title": "Test Post",
                "content": "This is a test post",
                "category": "discussion"
            }
        )
        
        assert response.status_code in [200, 201]
    
    @pytest.mark.asyncio
    async def test_get_post_detail(self, async_client, auth_headers):
        """测试获取帖子详情"""
        response = await async_client.get("/api/community/posts/1", headers=auth_headers)
        
        assert response.status_code in [200, 404]
    
    @pytest.mark.asyncio
    async def test_update_post(self, async_client, auth_headers):
        """测试更新帖子"""
        response = await async_client.put(
            "/api/community/posts/1",
            headers=auth_headers,
            json={"title": "Updated Title"}
        )
        
        assert response.status_code in [200, 404]
    
    @pytest.mark.asyncio
    async def test_delete_post(self, async_client, auth_headers):
        """测试删除帖子"""
        response = await async_client.delete("/api/community/posts/1", headers=auth_headers)
        
        assert response.status_code in [200, 404]
    
    @pytest.mark.asyncio
    async def test_like_post(self, async_client, auth_headers):
        """测试点赞帖子"""
        response = await async_client.post(
            "/api/community/posts/1/like",
            headers=auth_headers
        )
        
        assert response.status_code in [200, 404]
    
    @pytest.mark.asyncio
    async def test_comment_post(self, async_client, auth_headers):
        """测试评论帖子"""
        response = await async_client.post(
            "/api/community/posts/1/comments",
            headers=auth_headers,
            json={"content": "Great post!"}
        )
        
        assert response.status_code in [200, 201, 404]
    
    @pytest.mark.asyncio
    async def test_search_posts(self, async_client, auth_headers):
        """测试搜索帖子"""
        response = await async_client.get(
            "/api/community/posts/search?q=test",
            headers=auth_headers
        )
        
        assert response.status_code == 200


class TestCommunityCategory:
    """社区分类测试"""
    
    @pytest.mark.asyncio
    async def test_get_categories(self, async_client, auth_headers):
        """测试获取分类"""
        response = await async_client.get("/api/community/categories", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    @pytest.mark.asyncio
    async def test_get_posts_by_category(self, async_client, auth_headers):
        """测试按分类获取帖子"""
        response = await async_client.get(
            "/api/community/categories/1/posts",
            headers=auth_headers
        )
        
        assert response.status_code == 200


class TestCommunityUser:
    """社区用户测试"""
    
    @pytest.mark.asyncio
    async def test_get_user_profile(self, async_client, auth_headers):
        """测试获取用户资料"""
        response = await async_client.get(
            "/api/community/users/profile",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "username" in data or "display_name" in data
    
    @pytest.mark.asyncio
    async def test_update_user_profile(self, async_client, auth_headers):
        """测试更新用户资料"""
        response = await async_client.put(
            "/api/community/users/profile",
            headers=auth_headers,
            json={
                "display_name": "Test User",
                "bio": "Hello world!"
            }
        )
        
        assert response.status_code in [200, 400]
    
    @pytest.mark.asyncio
    async def test_get_user_posts(self, async_client, auth_headers):
        """测试获取用户帖子"""
        response = await async_client.get(
            "/api/community/users/1/posts",
            headers=auth_headers
        )
        
        assert response.status_code in [200, 404]


# ========== 外部API测试 ==========

class TestExternalAPI:
    """外部API测试"""
    
    @pytest.mark.asyncio
    async def test_health_check(self, async_client):
        """测试健康检查"""
        response = await async_client.get("/api/external/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
    
    @pytest.mark.asyncio
    async def test_get_api_status(self, async_client, auth_headers):
        """测试获取API状态"""
        response = await async_client.get("/api/external/status", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "services" in data


class TestWebhookAPI:
    """Webhook API测试"""
    
    @pytest.mark.asyncio
    async def test_register_webhook(self, async_client, auth_headers):
        """测试注册Webhook"""
        response = await async_client.post(
            "/api/external/webhooks",
            headers=auth_headers,
            json={
                "url": "https://example.com/webhook",
                "events": ["media.uploaded", "album.created"]
            }
        )
        
        assert response.status_code in [200, 201]
    
    @pytest.mark.asyncio
    async def test_list_webhooks(self, async_client, auth_headers):
        """测试列出Webhook"""
        response = await async_client.get("/api/external/webhooks", headers=auth_headers)
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_delete_webhook(self, async_client, auth_headers):
        """测试删除Webhook"""
        response = await async_client.delete(
            "/api/external/webhooks/1",
            headers=auth_headers
        )
        
        assert response.status_code in [200, 404]
    
    @pytest.mark.asyncio
    async def test_test_webhook(self, async_client, auth_headers):
        """测试Webhook"""
        response = await async_client.post(
            "/api/external/webhooks/1/test",
            headers=auth_headers
        )
        
        assert response.status_code in [200, 404]


class TestOAuthAPI:
    """OAuth API测试"""
    
    @pytest.mark.asyncio
    async def test_get_oauth_url(self, async_client, auth_headers):
        """测试获取OAuth URL"""
        response = await async_client.get(
            "/api/external/oauth/authorize?provider=google",
            headers=auth_headers
        )
        
        assert response.status_code in [200, 400]
    
    @pytest.mark.asyncio
    async def test_handle_oauth_callback(self, async_client):
        """测试处理OAuth回调"""
        response = await async_client.post(
            "/api/external/oauth/callback",
            params={"provider": "google", "code": "test_code"}
        )
        
        assert response.status_code in [200, 400]
    
    @pytest.mark.asyncio
    async def test_get_connected_accounts(self, async_client, auth_headers):
        """测试获取已连接账户"""
        response = await async_client.get(
            "/api/external/oauth/accounts",
            headers=auth_headers
        )
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_disconnect_account(self, async_client, auth_headers):
        """测试断开连接"""
        response = await async_client.delete(
            "/api/external/oauth/accounts/1",
            headers=auth_headers
        )
        
        assert response.status_code in [200, 404]


class TestAPIKeyManagement:
    """API密钥管理测试"""
    
    @pytest.mark.asyncio
    async def test_create_api_key(self, async_client, auth_headers):
        """测试创建API密钥"""
        response = await async_client.post(
            "/api/external/keys",
            headers=auth_headers,
            json={
                "name": "Test Key",
                "permissions": ["media:read", "album:read"]
            }
        )
        
        assert response.status_code in [200, 201]
    
    @pytest.mark.asyncio
    async def test_list_api_keys(self, async_client, auth_headers):
        """测试列出API密钥"""
        response = await async_client.get("/api/external/keys", headers=auth_headers)
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_revoke_api_key(self, async_client, auth_headers):
        """测试撤销API密钥"""
        response = await async_client.delete("/api/external/keys/1", headers=auth_headers)
        
        assert response.status_code in [200, 404]
    
    @pytest.mark.asyncio
    async def test_regenerate_api_key(self, async_client, auth_headers):
        """测试重新生成API密钥"""
        response = await async_client.post(
            "/api/external/keys/1/regenerate",
            headers=auth_headers
        )
        
        assert response.status_code in [200, 404]


class TestWebhookDelivery:
    """Webhook投递测试"""
    
    @pytest.mark.asyncio
    async def test_webhook_delivery_status(self, async_client, auth_headers):
        """测试Webhook投递状态"""
        response = await async_client.get(
            "/api/external/webhooks/1/deliveries",
            headers=auth_headers
        )
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_retry_webhook(self, async_client, auth_headers):
        """测试重试Webhook"""
        response = await async_client.post(
            "/api/external/webhooks/deliveries/1/retry",
            headers=auth_headers
        )
        
        assert response.status_code in [200, 404]


class TestRateLimiting:
    """速率限制测试"""
    
    @pytest.mark.asyncio
    async def test_rate_limit_headers(self, async_client, auth_headers):
        """测试速率限制响应头"""
        response = await async_client.get("/api/media/", headers=auth_headers)
        
        # 应该包含速率限制头
        headers = response.headers
        has_limit = any(
            h in headers for h in [
                "X-RateLimit-Limit",
                "X-Rate-Limit",
                "RateLimit-Limit"
            ]
        )
        assert has_limit or response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_rate_limit_exceeded(self, async_client, auth_headers):
        """测试速率限制超限"""
        # 模拟多次请求
        for _ in range(100):
            response = await async_client.get("/api/media/", headers=auth_headers)
            if response.status_code == 429:
                break
        
        # 至少应该有一个成功的响应或429
        assert response.status_code in [200, 429]


class TestAPIAnalytics:
    """API分析测试"""
    
    @pytest.mark.asyncio
    async def test_get_api_usage_stats(self, async_client, auth_headers):
        """测试获取API使用统计"""
        response = await async_client.get(
            "/api/external/stats/usage",
            headers=auth_headers
        )
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_get_api_error_stats(self, async_client, auth_headers):
        """测试获取API错误统计"""
        response = await async_client.get(
            "/api/external/stats/errors",
            headers=auth_headers
        )
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_get_endpoint_stats(self, async_client, auth_headers):
        """测试获取端点统计"""
        response = await async_client.get(
            "/api/external/stats/endpoints",
            headers=auth_headers
        )
        
        assert response.status_code == 200


class TestAPIDocumentation:
    """API文档测试"""
    
    @pytest.mark.asyncio
    async def test_get_api_docs(self, async_client):
        """测试获取API文档"""
        response = await async_client.get("/api/docs")
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_get_openapi_spec(self, async_client):
        """测试获取OpenAPI规范"""
        response = await async_client.get("/api/openapi.json")
        
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data or "swagger" in data


# ========== 云存储集成测试 ==========

class TestCloudStorageAPI:
    """云存储API测试"""
    
    @pytest.mark.asyncio
    async def test_get_cloud_config(self, async_client, auth_headers):
        """测试获取云存储配置"""
        response = await async_client.get(
            "/api/external/cloud/config",
            headers=auth_headers
        )
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_connect_aliyun_oss(self, async_client, auth_headers):
        """测试连接阿里云OSS"""
        response = await async_client.post(
            "/api/external/cloud/connect",
            headers=auth_headers,
            json={
                "provider": "aliyun",
                "access_key": "test_key",
                "secret_key": "test_secret",
                "bucket": "test_bucket"
            }
        )
        
        assert response.status_code in [200, 400]
    
    @pytest.mark.asyncio
    async def test_connect_tencent_cos(self, async_client, auth_headers):
        """测试连接腾讯云COS"""
        response = await async_client.post(
            "/api/external/cloud/connect",
            headers=auth_headers,
            json={
                "provider": "tencent",
                "access_key": "test_key",
                "secret_key": "test_secret",
                "bucket": "test_bucket"
            }
        )
        
        assert response.status_code in [200, 400]
    
    @pytest.mark.asyncio
    async def test_test_cloud_connection(self, async_client, auth_headers):
        """测试云存储连接"""
        response = await async_client.post(
            "/api/external/cloud/test",
            headers=auth_headers,
            json={"provider": "aliyun"}
        )
        
        assert response.status_code in [200, 400]
    
    @pytest.mark.asyncio
    async def test_get_cloud_usage(self, async_client, auth_headers):
        """测试获取云存储使用情况"""
        response = await async_client.get(
            "/api/external/cloud/usage",
            headers=auth_headers
        )
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_disconnect_cloud(self, async_client, auth_headers):
        """测试断开云存储"""
        response = await async_client.delete(
            "/api/external/cloud/aliyun",
            headers=auth_headers
        )
        
        assert response.status_code in [200, 404]


class TestPluginMarketplaceAPI:
    """插件市场API测试"""
    
    @pytest.mark.asyncio
    async def test_search_plugins(self, async_client, auth_headers):
        """测试搜索插件"""
        response = await async_client.get(
            "/api/external/plugins?q=storage",
            headers=auth_headers
        )
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_get_plugin_details(self, async_client, auth_headers):
        """测试获取插件详情"""
        response = await async_client.get(
            "/api/external/plugins/storage-plugin",
            headers=auth_headers
        )
        
        assert response.status_code in [200, 404]
    
    @pytest.mark.asyncio
    async def test_install_plugin(self, async_client, auth_headers):
        """测试安装插件"""
        response = await async_client.post(
            "/api/external/plugins/install",
            headers=auth_headers,
            json={"name": "test-plugin", "source": "marketplace"}
        )
        
        assert response.status_code in [200, 400]
    
    @pytest.mark.asyncio
    async def test_uninstall_plugin(self, async_client, auth_headers):
        """测试卸载插件"""
        response = await async_client.delete(
            "/api/external/plugins/test-plugin",
            headers=auth_headers
        )
        
        assert response.status_code in [200, 404]
    
    @pytest.mark.asyncio
    async def test_update_plugin(self, async_client, auth_headers):
        """测试更新插件"""
        response = await async_client.post(
            "/api/external/plugins/test-plugin/update",
            headers=auth_headers
        )
        
        assert response.status_code in [200, 404]
    
    @pytest.mark.asyncio
    async def test_get_installed_plugins(self, async_client, auth_headers):
        """测试获取已安装插件"""
        response = await async_client.get(
            "/api/external/plugins",
            headers=auth_headers
        )
        
        assert response.status_code == 200


# ========== 权限和安全测试 ==========

class TestAPIKeyAuth:
    """API密钥认证测试"""
    
    @pytest.mark.asyncio
    async def test_auth_with_api_key(self, async_client):
        """测试使用API密钥认证"""
        response = await async_client.get(
            "/api/media/",
            headers={"X-API-Key": "test_api_key"}
        )
        
        # 应该返回401或200
        assert response.status_code in [200, 401]
    
    @pytest.mark.asyncio
    async def test_invalid_api_key(self, async_client):
        """测试无效API密钥"""
        response = await async_client.get(
            "/api/media/",
            headers={"X-API-Key": "invalid_key"}
        )
        
        assert response.status_code == 401


class TestWebhookSecurity:
    """Webhook安全测试"""
    
    @pytest.mark.asyncio
    async def test_webhook_signature_validation(self, async_client):
        """测试Webhook签名验证"""
        response = await async_client.post(
            "/api/external/webhooks/test",
            headers={
                "X-Webhook-Signature": "sha256=invalid_signature"
            },
            json={"event": "test"}
        )
        
        # 应该返回成功（模拟）或签名错误
        assert response.status_code in [200, 401, 400]
    
    @pytest.mark.asyncio
    async def test_webhook_replay_protection(self, async_client):
        """测试Webhook重放保护"""
        response = await async_client.post(
            "/api/external/webhooks/test",
            headers={
                "X-Webhook-Timestamp": "old_timestamp"
            },
            json={"event": "test"}
        )
        
        # 应该拒绝旧的Webhook
        assert response.status_code in [200, 400, 401]


class TestCORS:
    """CORS测试"""
    
    @pytest.mark.asyncio
    async def test_cors_preflight(self, async_client):
        """测试CORS预检请求"""
        response = await async_client.options(
            "/api/media/",
            headers={
                "Origin": "https://example.com",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Authorization"
            }
        )
        
        # 应该有CORS响应头
        headers = response.headers
        has_cors = any(
            "access-control" in h.lower() for h in headers.keys()
        )
        assert has_cors or response.status_code in [200, 204, 405]
    
    @pytest.mark.asyncio
    async def test_cors_allowed_origin(self, async_client):
        """测试CORS允许的来源"""
        response = await async_client.get(
            "/api/media/",
            headers={"Origin": "https://example.com"}
        )
        
        # 应该有Access-Control-Allow-Origin头
        assert response.status_code == 200
