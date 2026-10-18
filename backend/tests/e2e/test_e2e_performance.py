"""
test_e2e_performance.py - E2E 性能测试
======================================
测试场景：
  1. 并发上传
  2. 大量媒体文件查询
  3. 长时间运行稳定性

运行：
  pytest tests/e2e/test_e2e_performance.py -v --timeout=300
"""

import pytest
import sys
import time
import concurrent.futures
from pathlib import Path
from io import BytesIO

backend_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_root))

try:
    from fastapi.testclient import TestClient
    from main import app
    HAS_TESTCLIENT = True
except ImportError:
    HAS_TESTCLIENT = False


@pytest.fixture(scope="module")
def client():
    if HAS_TESTCLIENT:
        return TestClient(app)
    pytest.skip("TestClient not available")


@pytest.fixture(scope="module")
def auth_headers(client):
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


class TestConcurrentOperations:
    """并发操作性能测试"""

    @pytest.mark.slow
    def test_concurrent_list_requests(self, client, auth_headers):
        """测试并发列表查询"""
        if not auth_headers:
            pytest.skip("No auth token")
        
        def make_request():
            return client.get("/api/media/list", headers=auth_headers)
        
        start = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request) for _ in range(10)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        elapsed = time.time() - start
        
        # 所有请求应该成功
        assert all(r.status_code == 200 for r in results)
        # 10个并发请求应该在5秒内完成
        assert elapsed < 5.0

    @pytest.mark.slow
    def test_rapid_health_checks(self, client):
        """测试快速健康检查"""
        start = time.time()
        
        for _ in range(20):
            response = client.get("/api/health")
            assert response.status_code == 200
        
        elapsed = time.time() - start
        # 20次健康检查应该在2秒内完成
        assert elapsed < 2.0


class TestLargeDatasetOperations:
    """大数据集操作测试"""

    def test_pagination_performance(self, client, auth_headers):
        """测试分页性能"""
        if not auth_headers:
            pytest.skip("No auth token")
        
        start = time.time()
        
        # 请求多页数据
        for page in range(1, 6):
            response = client.get(
                f"/api/media/list?page={page}&limit=20",
                headers=auth_headers
            )
            assert response.status_code == 200
        
        elapsed = time.time() - start
        # 5页数据应该在1秒内完成
        assert elapsed < 1.0


class TestMemoryStability:
    """内存稳定性测试"""

    @pytest.mark.slow
    def test_repeated_operations(self, client, auth_headers):
        """测试重复操作的内存稳定性"""
        if not auth_headers:
            pytest.skip("No auth token")
        
        for i in range(50):
            # 列表查询
            response = client.get("/api/media/list", headers=auth_headers)
            assert response.status_code == 200
            
            # 数量查询
            response = client.get("/api/media/count", headers=auth_headers)
            assert response.status_code == 200
            
            # 健康检查
            response = client.get("/api/health")
            assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
