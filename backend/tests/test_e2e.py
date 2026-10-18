"""
端到端测试
完整功能流程测试
"""

import pytest
import os
import tempfile
from pathlib import Path
from PIL import Image
import shutil


class TestEndToEndWorkflow:
    """端到端工作流测试"""
    
    @pytest.mark.asyncio
    async def test_complete_scan_classify_workflow(self, client):
        """测试完整的扫描+分类工作流"""
        
        # 1. 创建测试图片
        test_dir = Path(tempfile.mkdtemp())
        test_images = []
        
        for i in range(3):
            img_path = test_dir / f"test_{i}.jpg"
            img = Image.new("RGB", (100, 100), color=(i*50, i*50, i*50))
            img.save(img_path)
            test_images.append(str(img_path))
        
        try:
            # 2. 扫描媒体
            response = await client.post(
                "/api/actions/scan",
                json={
                    "path": str(test_dir),
                    "recursive": True
                }
            )
            assert response.status_code in [200, 202]
            
            # 3. 获取媒体列表
            response = await client.get("/api/media/")
            assert response.status_code == 200
            data = response.json()
            assert "items" in data
            
            # 4. 获取任务状态
            response = await client.get("/api/tasks/")
            assert response.status_code == 200
            
        finally:
            shutil.rmtree(test_dir, ignore_errors=True)
    
    @pytest.mark.asyncio
    async def test_album_workflow(self, client):
        """测试相册工作流"""
        
        # 1. 获取相册列表
        response = await client.get("/api/albums/")
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_device_workflow(self, client):
        """测试设备工作流"""
        
        # 1. 获取设备列表
        response = await client.get("/api/devices/")
        assert response.status_code == 200
        
        # 2. 获取系统监控
        response = await client.get("/api/monitor/system")
        assert response.status_code == 200


class TestPerformanceBenchmarks:
    """性能基准测试"""
    
    @pytest.mark.asyncio
    async def test_response_time_health(self, client):
        """测试健康检查响应时间"""
        import time
        
        start = time.time()
        response = await client.get("/health")
        elapsed = time.time() - start
        
        assert response.status_code == 200
        assert elapsed < 1.0
    
    @pytest.mark.asyncio
    async def test_response_time_list(self, client):
        """测试列表接口响应时间"""
        import time
        
        start = time.time()
        response = await client.get("/api/media/")
        elapsed = time.time() - start
        
        assert response.status_code == 200
        assert elapsed < 2.0


class TestSecurityValidation:
    """安全性验证测试"""
    
    @pytest.mark.asyncio
    async def test_no_auth_required_health(self, client):
        """测试健康检查无需认证"""
        response = await client.get("/health")
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_auth_required_protected(self, client):
        """测试受保护接口"""
        response = await client.get("/auth/me")
        assert response.status_code == 401


class TestDataIntegrity:
    """数据完整性测试"""
    
    @pytest.mark.asyncio
    async def test_database_connection(self, client):
        """测试数据库连接"""
        response = await client.get("/status")
        assert response.status_code == 200
        data = response.json()
        assert data["database"]["connected"] == True
    
    @pytest.mark.asyncio
    async def test_empty_state_consistent(self, client):
        """测试空状态一致性"""
        endpoints = [
            "/api/media/",
            "/api/albums/",
            "/api/devices/",
            "/api/tasks/"
        ]
        
        for endpoint in endpoints:
            response = await client.get(endpoint)
            assert response.status_code == 200
