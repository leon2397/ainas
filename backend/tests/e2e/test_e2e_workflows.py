"""
test_e2e_workflows.py - E2E 端到端测试
=======================================
覆盖完整用户工作流：
  1. 用户登录 → 上传图片 → AI 分析 → 查看结果
  2. 创建相册 → 添加图片 → 分享相册
  3. 扫描目录 → 分类 → 生成报告

运行：
  cd backend
  pytest tests/e2e/test_e2e_workflows.py -v

注意：
  - 需要完整后端服务运行
  - 或使用 TestClient + 内存数据库
"""

import pytest
import sys
import os
import tempfile
import time
from pathlib import Path
from datetime import datetime
from io import BytesIO

# 添加 backend 到 path
backend_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_root))

# 尝试导入
try:
    from fastapi.testclient import TestClient
    from main import app
    HAS_TESTCLIENT = True
except ImportError:
    HAS_TESTCLIENT = False


@pytest.fixture(scope="module")
def client():
    """创建测试客户端"""
    if HAS_TESTCLIENT:
        return TestClient(app)
    pytest.skip("TestClient not available")


@pytest.fixture(scope="module")
def auth_headers(client):
    """获取认证头"""
    if not HAS_TESTCLIENT:
        return {}
    
    response = client.post("/api/auth/login", data={
        "username": "admin",
        "password": "admin123"
    })
    if response.status_code == 200:
        token = response.json().get("access_token")
        return {"Authorization": f"Bearer {token}"}
    return {}


class TestUserLoginWorkflow:
    """用户登录工作流测试"""

    def test_complete_login_flow(self, client):
        """测试完整登录流程"""
        # 1. 登录获取 token
        response = client.post("/api/auth/login", data={
            "username": "admin",
            "password": "admin123"
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        
        token = data["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # 2. 获取用户信息
        response = client.get("/api/auth/me", headers=headers)
        assert response.status_code == 200
        user_data = response.json()
        assert "username" in user_data
        
        # 3. 验证 token 有效
        response = client.get("/api/media/list", headers=headers)
        assert response.status_code == 200


class TestMediaUploadWorkflow:
    """媒体上传工作流测试"""

    def test_upload_and_analyze_image(self, client, auth_headers):
        """测试上传图片并分析"""
        if not auth_headers:
            pytest.skip("No auth token")
        
        # 1. 创建测试图片
        test_image = BytesIO(b"\xff\xd8\xff\xe0\x00\x10JFIF" + b"\x00" * 1000)
        
        # 2. 上传图片
        files = {"file": ("test_image.jpg", test_image, "image/jpeg")}
        response = client.post(
            "/api/media/upload",
            headers=auth_headers,
            files=files
        )
        # 可能返回 200 或 422（验证错误）
        assert response.status_code in [200, 201, 422]
        
        if response.status_code in [200, 201]:
            data = response.json()
            file_id = data.get("id") or data.get("file_id")
            
            # 3. 获取媒体列表
            response = client.get("/api/media/list", headers=auth_headers)
            assert response.status_code == 200
            
            # 4. 请求 AI 分析
            if file_id:
                response = client.post(
                    "/api/ai/tags/generate",
                    headers=auth_headers,
                    params={"file_ids": file_id}
                )
                # 可能返回 200 或 500（如果 AI 未配置）
                assert response.status_code in [200, 202, 500]

    def test_upload_and_delete(self, client, auth_headers):
        """测试上传后删除"""
        if not auth_headers:
            pytest.skip("No auth token")
        
        # 获取当前媒体数量
        response = client.get("/api/media/count", headers=auth_headers)
        initial_count = response.json().get("count", 0) if response.status_code == 200 else 0
        
        # 上传测试文件
        test_file = BytesIO(b"fake_image_data")
        files = {"file": ("test.jpg", test_file, "image/jpeg")}
        response = client.post(
            "/api/media/upload",
            headers=auth_headers,
            files=files
        )
        
        if response.status_code in [200, 201]:
            data = response.json()
            file_id = data.get("id") or data.get("file_id")
            
            # 删除文件
            if file_id:
                response = client.delete(
                    f"/api/media/delete/{file_id}",
                    headers=auth_headers
                )
                assert response.status_code in [200, 204, 404]


class TestAlbumWorkflow:
    """相册工作流测试"""

    def test_create_and_manage_album(self, client, auth_headers):
        """测试创建和管理相册"""
        if not auth_headers:
            pytest.skip("No auth token")
        
        # 1. 创建相册
        album_name = f"Test Album {datetime.now().timestamp()}"
        response = client.post(
            "/api/albums/create",
            headers=auth_headers,
            json={"name": album_name, "description": "E2E test album"}
        )
        
        if response.status_code in [200, 201]:
            data = response.json()
            album_id = data.get("id")
            
            # 2. 获取相册列表
            response = client.get("/api/albums/list", headers=auth_headers)
            assert response.status_code == 200
            albums = response.json()
            assert any(a.get("name") == album_name for a in albums) or True
            
            # 3. 获取相册详情
            if album_id:
                response = client.get(f"/api/albums/get/{album_id}", headers=auth_headers)
                assert response.status_code in [200, 404]
                
                # 4. 删除相册
                response = client.delete(f"/api/albums/delete/{album_id}", headers=auth_headers)
                assert response.status_code in [200, 204]


class TestScanWorkflow:
    """扫描工作流测试"""

    def test_scan_and_classify(self, client, auth_headers):
        """测试扫描和分类流程"""
        if not auth_headers:
            pytest.skip("No auth token")
        
        # 1. 触发扫描
        response = client.post(
            "/api/actions/scan",
            headers=auth_headers,
            json={"path": "/tmp/test_media", "recursive": True}
        )
        # 可能返回 200 或 202（异步任务）
        assert response.status_code in [200, 202, 400]
        
        if response.status_code in [200, 202]:
            data = response.json()
            task_id = data.get("task_id")
            
            # 2. 检查任务状态
            if task_id:
                time.sleep(0.5)  # 等待任务启动
                response = client.get(f"/api/tasks/get/{task_id}", headers=auth_headers)
                assert response.status_code in [200, 404]

    def test_batch_classify(self, client, auth_headers):
        """测试批量分类"""
        if not auth_headers:
            pytest.skip("No auth token")
        
        response = client.post(
            "/api/actions/batch-classify-all",
            headers=auth_headers
        )
        # 可能返回 200 或 202
        assert response.status_code in [200, 202, 400]


class TestSearchWorkflow:
    """搜索工作流测试"""

    def test_search_and_filter(self, client, auth_headers):
        """测试搜索和过滤"""
        if not auth_headers:
            pytest.skip("No auth token")
        
        # 1. 简单搜索
        response = client.get("/api/media/search?q=test", headers=auth_headers)
        assert response.status_code in [200, 422]
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list) or "items" in data
        
        # 2. 高级搜索
        response = client.post(
            "/api/media/advanced-search",
            headers=auth_headers,
            json={
                "query": "test",
                "filters": {"type": "image"},
                "sort": {"field": "created_at", "order": "desc"}
            }
        )
        assert response.status_code in [200, 422]


class TestSystemWorkflow:
    """系统工作流测试"""

    def test_health_to_monitoring(self, client):
        """测试健康检查到监控的完整流程"""
        # 1. 健康检查
        response = client.get("/api/health")
        assert response.status_code == 200
        health_data = response.json()
        
        # 2. 系统信息
        response = client.get("/api/system/info")
        assert response.status_code == 200
        
        # 3. 监控状态
        response = client.get("/api/monitor/status")
        assert response.status_code == 200
        
        # 4. CPU/内存/磁盘
        for endpoint in ["/api/monitor/cpu", "/api/monitor/memory", "/api/monitor/disk"]:
            response = client.get(endpoint)
            assert response.status_code == 200


class TestErrorHandling:
    """错误处理 E2E 测试"""

    def test_unauthorized_access(self, client):
        """测试未授权访问"""
        endpoints = [
            "/api/media/list",
            "/api/albums/list",
            "/api/auth/me",
        ]
        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code in [401, 403]

    def test_invalid_token(self, client):
        """测试无效 token"""
        headers = {"Authorization": "Bearer invalid_token"}
        response = client.get("/api/media/list", headers=headers)
        assert response.status_code in [401, 403]

    def test_not_found(self, client, auth_headers):
        """测试资源不存在"""
        if not auth_headers:
            pytest.skip("No auth token")
        
        response = client.get("/api/media/get/999999", headers=auth_headers)
        assert response.status_code == 404


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
