"""
审计日志系统单元测试
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import json
import asyncio


class TestAuditLogger:
    """审计日志记录器测试"""
    
    @pytest.fixture
    def audit_logger(self):
        """创建审计日志记录器实例"""
        from core.audit.logger import AuditLogger
        logger = AuditLogger()
        logger.db = Mock()
        logger.buffer = []
        logger.buffer_size = 10
        return logger
    
    def test_log_creation(self, audit_logger):
        """测试日志创建"""
        audit_logger.db.execute = Mock(return_value=None)
        
        log_id = audit_logger.log(
            level="INFO",
            category="AUTH",
            action="login",
            user_id=1,
            username="test_user",
            details={"ip": "192.168.1.1"}
        )
        
        assert log_id is not None
        audit_logger.db.execute.assert_called_once()
    
    def test_log_with_different_levels(self, audit_logger):
        """测试不同级别的日志"""
        audit_logger.db.execute = Mock(return_value=None)
        
        levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        for level in levels:
            log_id = audit_logger.log(
                level=level,
                category="SYSTEM",
                action="test_action"
            )
            assert log_id is not None
    
    def test_log_with_all_categories(self, audit_logger):
        """测试所有审计类别"""
        audit_logger.db.execute = Mock(return_value=None)
        
        categories = ["AUTH", "USER", "MEDIA", "ALBUM", "DEVICE", "SYSTEM", "CONFIG", "SECURITY", "ADMIN"]
        for category in categories:
            log_id = audit_logger.log(
                level="INFO",
                category=category,
                action="test"
            )
            assert log_id is not None
    
    def test_log_with_resource_info(self, audit_logger):
        """测试带资源信息的日志"""
        audit_logger.db.execute = Mock(return_value=None)
        
        log_id = audit_logger.log(
            level="INFO",
            category="MEDIA",
            action="view",
            resource_type="media",
            resource_id="12345",
            details={"filename": "test.jpg"}
        )
        
        assert log_id is not None
    
    def test_async_log(self, audit_logger):
        """测试异步日志记录"""
        audit_logger._write_buffer = Mock(return_value=None)
        
        log_id = audit_logger.async_log(
            level="INFO",
            category="MEDIA",
            action="upload"
        )
        
        # 应该添加到缓冲区
        assert len(audit_logger.buffer) == 1
        assert audit_logger.buffer[0]["action"] == "upload"
    
    def test_buffer_flush_when_full(self, audit_logger):
        """测试缓冲区满时自动刷新"""
        audit_logger._write_buffer = Mock(return_value=None)
        
        # 填充缓冲区
        for i in range(audit_logger.buffer_size):
            audit_logger.async_log(
                level="INFO",
                category="TEST",
                action=f"action_{i}"
            )
        
        # 缓冲区应该被刷新
        audit_logger._write_buffer.assert_called_once()
        assert len(audit_logger.buffer) == 0
    
    def test_manual_flush(self, audit_logger):
        """测试手动刷新缓冲区"""
        audit_logger._write_buffer = Mock(return_value=None)
        
        audit_logger.async_log(level="INFO", category="TEST", action="test")
        audit_logger.flush()
        
        audit_logger._write_buffer.assert_called_once()
        assert len(audit_logger.buffer) == 0


class TestAuditQuery:
    """审计日志查询测试"""
    
    @pytest.fixture
    def audit_logger(self):
        """创建审计日志记录器实例"""
        from core.audit.logger import AuditLogger
        logger = AuditLogger()
        logger.db = Mock()
        return logger
    
    def test_query_all_logs(self, audit_logger):
        """测试查询所有日志"""
        audit_logger.db.fetch_all = Mock(return_value=[
            {"id": 1, "level": "INFO", "category": "AUTH", "action": "login"},
            {"id": 2, "level": "INFO", "category": "MEDIA", "action": "view"}
        ])
        
        logs = audit_logger.query_logs()
        
        assert len(logs) == 2
        assert logs[0]["category"] == "AUTH"
    
    def test_query_by_category(self, audit_logger):
        """测试按类别查询"""
        audit_logger.db.fetch_all = Mock(return_value=[
            {"id": 1, "level": "INFO", "category": "AUTH", "action": "login"}
        ])
        
        logs = audit_logger.query_logs(category="AUTH")
        
        assert len(logs) == 1
        assert logs[0]["category"] == "AUTH"
    
    def test_query_by_level(self, audit_logger):
        """测试按级别查询"""
        audit_logger.db.fetch_all = Mock(return_value=[
            {"id": 1, "level": "ERROR", "category": "SYSTEM", "action": "error"}
        ])
        
        logs = audit_logger.query_logs(level="ERROR")
        
        assert len(logs) == 1
        assert logs[0]["level"] == "ERROR"
    
    def test_query_by_user(self, audit_logger):
        """测试按用户查询"""
        audit_logger.db.fetch_all = Mock(return_value=[
            {"id": 1, "user_id": 1, "username": "test_user", "action": "login"}
        ])
        
        logs = audit_logger.query_logs(user_id=1)
        
        assert len(logs) == 1
        assert logs[0]["user_id"] == 1
    
    def test_query_by_date_range(self, audit_logger):
        """测试按日期范围查询"""
        audit_logger.db.fetch_all = Mock(return_value=[
            {"id": 1, "created_at": "2026-04-06 10:00:00"},
            {"id": 2, "created_at": "2026-04-06 11:00:00"}
        ])
        
        start_date = datetime.now() - timedelta(days=1)
        end_date = datetime.now()
        
        logs = audit_logger.query_logs(start_date=start_date, end_date=end_date)
        
        assert len(logs) == 2
    
    def test_query_with_pagination(self, audit_logger):
        """测试分页查询"""
        audit_logger.db.fetch_all = Mock(return_value=[
            {"id": 11}, {"id": 12}, {"id": 13}
        ])
        audit_logger.db.fetch_val = Mock(return_value=100)  # 总记录数
        
        logs, total = audit_logger.query_logs(limit=10, offset=10)
        
        assert len(logs) == 3
        assert total == 100
    
    def test_query_by_action(self, audit_logger):
        """测试按动作查询"""
        audit_logger.db.fetch_all = Mock(return_value=[
            {"id": 1, "action": "login"},
            {"id": 2, "action": "login"}
        ])
        
        logs = audit_logger.query_logs(action="login")
        
        assert len(logs) == 2
        assert all(log["action"] == "login" for log in logs)
    
    def test_query_by_resource(self, audit_logger):
        """测试按资源查询"""
        audit_logger.db.fetch_all = Mock(return_value=[
            {"id": 1, "resource_type": "media", "resource_id": "123"}
        ])
        
        logs = audit_logger.query_logs(resource_type="media", resource_id="123")
        
        assert len(logs) == 1
        assert logs[0]["resource_type"] == "media"


class TestAuditStats:
    """审计统计测试"""
    
    @pytest.fixture
    def audit_logger(self):
        """创建审计日志记录器实例"""
        from core.audit.logger import AuditLogger
        logger = AuditLogger()
        logger.db = Mock()
        return logger
    
    def test_get_stats_by_category(self, audit_logger):
        """测试按类别统计"""
        audit_logger.db.fetch_all = Mock(return_value=[
            {"category": "AUTH", "count": 50},
            {"category": "MEDIA", "count": 100},
            {"category": "SYSTEM", "count": 25}
        ])
        
        stats = audit_logger.get_stats_by_category()
        
        assert len(stats) == 3
        assert stats["MEDIA"] == 100
    
    def test_get_stats_by_level(self, audit_logger):
        """测试按级别统计"""
        audit_logger.db.fetch_all = Mock(return_value=[
            {"level": "INFO", "count": 150},
            {"level": "WARNING", "count": 20},
            {"level": "ERROR", "count": 5}
        ])
        
        stats = audit_logger.get_stats_by_level()
        
        assert stats["INFO"] == 150
        assert stats["ERROR"] == 5
    
    def test_get_stats_by_user(self, audit_logger):
        """测试按用户统计"""
        audit_logger.db.fetch_all = Mock(return_value=[
            {"user_id": 1, "username": "admin", "count": 100},
            {"user_id": 2, "username": "user1", "count": 50}
        ])
        
        stats = audit_logger.get_stats_by_user()
        
        assert len(stats) == 2
        assert stats[0]["username"] == "admin"
    
    def test_get_stats_by_action(self, audit_logger):
        """测试按动作统计"""
        audit_logger.db.fetch_all = Mock(return_value=[
            {"action": "login", "count": 200},
            {"action": "view", "count": 500},
            {"action": "upload", "count": 50}
        ])
        
        stats = audit_logger.get_stats_by_action()
        
        assert stats["view"] == 500
    
    def test_get_stats_by_time(self, audit_logger):
        """测试按时间统计"""
        audit_logger.db.fetch_all = Mock(return_value=[
            {"date": "2026-04-06", "count": 100},
            {"date": "2026-04-05", "count": 150}
        ])
        
        stats = audit_logger.get_stats_by_time(days=7)
        
        assert len(stats) == 2
    
    def test_get_dashboard_stats(self, audit_logger):
        """测试仪表板统计"""
        audit_logger.db.fetch_val = Mock(side_effect=[
            1000,  # total_logs
            50,    # today_logs
            5,     # error_logs
            10     # unique_users
        ])
        
        stats = audit_logger.get_dashboard_stats()
        
        assert stats["total_logs"] == 1000
        assert stats["today_logs"] == 50
        assert stats["error_logs"] == 5
        assert stats["unique_users"] == 10


class TestAuditExport:
    """审计日志导出测试"""
    
    @pytest.fixture
    def audit_logger(self):
        """创建审计日志记录器实例"""
        from core.audit.logger import AuditLogger
        logger = AuditLogger()
        logger.db = Mock()
        return logger
    
    def test_export_to_json(self, audit_logger, tmp_path):
        """测试导出为JSON"""
        audit_logger.db.fetch_all = Mock(return_value=[
            {"id": 1, "level": "INFO", "category": "AUTH", "action": "login"},
            {"id": 2, "level": "INFO", "category": "MEDIA", "action": "view"}
        ])
        
        output_path = tmp_path / "audit.json"
        result = audit_logger.export_to_json(str(output_path))
        
        assert result is True
        assert output_path.exists()
        
        with open(output_path) as f:
            data = json.load(f)
            assert len(data) == 2
    
    def test_export_to_csv(self, audit_logger, tmp_path):
        """测试导出为CSV"""
        audit_logger.db.fetch_all = Mock(return_value=[
            {"id": 1, "level": "INFO", "category": "AUTH", "action": "login", "created_at": "2026-04-06 10:00:00"},
            {"id": 2, "level": "INFO", "category": "MEDIA", "action": "view", "created_at": "2026-04-06 11:00:00"}
        ])
        
        output_path = tmp_path / "audit.csv"
        result = audit_logger.export_to_csv(str(output_path))
        
        assert result is True
        assert output_path.exists()
        
        with open(output_path) as f:
            content = f.read()
            assert "id,level,category" in content
            assert "INFO,AUTH" in content


class TestAuditActions:
    """审计动作常量测试"""
    
    def test_auth_actions(self):
        """测试认证相关动作"""
        from core.audit.logger import AUTH_ACTIONS
        
        assert "login" in AUTH_ACTIONS
        assert "logout" in AUTH_ACTIONS
        assert "token_refresh" in AUTH_ACTIONS
        assert "password_change" in AUTH_ACTIONS
    
    def test_user_actions(self):
        """测试用户相关动作"""
        from core.audit.logger import USER_ACTIONS
        
        assert "create" in USER_ACTIONS
        assert "update" in USER_ACTIONS
        assert "delete" in USER_ACTIONS
    
    def test_media_actions(self):
        """测试媒体相关动作"""
        from core.audit.logger import MEDIA_ACTIONS
        
        assert "view" in MEDIA_ACTIONS
        assert "upload" in MEDIA_ACTIONS
        assert "delete" in MEDIA_ACTIONS
        assert "download" in MEDIA_ACTIONS
    
    def test_system_actions(self):
        """测试系统相关动作"""
        from core.audit.logger import SYSTEM_ACTIONS
        
        assert "config_update" in SYSTEM_ACTIONS
        assert "backup" in SYSTEM_ACTIONS
        assert "restore" in SYSTEM_ACTIONS


class TestAuditMiddleware:
    """审计中间件测试"""
    
    @pytest.fixture
    def audit_middleware(self):
        """创建审计中间件实例"""
        from middleware.audit.middleware import AuditMiddleware
        middleware = AuditMiddleware(app=Mock())
        middleware.audit_logger = Mock()
        return middleware
    
    @pytest.mark.asyncio
    async def test_log_request(self, audit_middleware):
        """测试记录请求"""
        mock_request = Mock()
        mock_request.method = "GET"
        mock_request.url.path = "/api/media/"
        mock_request.client.host = "192.168.1.1"
        mock_request.headers = {}
        
        audit_middleware.audit_logger.async_log = Mock()
        
        await audit_middleware.log_request(
            request=mock_request,
            user_id=1,
            username="test_user"
        )
        
        audit_middleware.audit_logger.async_log.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_log_response(self, audit_middleware):
        """测试记录响应"""
        mock_request = Mock()
        mock_request.method = "POST"
        mock_request.url.path = "/api/media/upload"
        
        mock_response = Mock()
        mock_response.status_code = 200
        
        audit_middleware.audit_logger.async_log = Mock()
        
        await audit_middleware.log_response(
            request=mock_request,
            response=mock_response,
            user_id=1,
            duration_ms=150
        )
        
        audit_middleware.audit_logger.async_log.assert_called_once()
    
    def test_should_skip_logging(self, audit_middleware):
        """测试跳过日志记录的路径"""
        # 健康检查应该跳过
        assert audit_middleware.should_skip_logging("/health") is True
        assert audit_middleware.should_skip_logging("/status") is True
        
        # API请求应该记录
        assert audit_middleware.should_skip_logging("/api/media/") is False
        assert audit_middleware.should_skip_logging("/api/auth/login") is False
    
    def test_get_resource_info(self, audit_middleware):
        """测试获取资源信息"""
        # 媒体资源
        resource_type, resource_id = audit_middleware.get_resource_info("/api/media/123")
        assert resource_type == "media"
        assert resource_id == "123"
        
        # 相册资源
        resource_type, resource_id = audit_middleware.get_resource_info("/api/albums/456")
        assert resource_type == "album"
        assert resource_id == "456"
        
        # 列表端点
        resource_type, resource_id = audit_middleware.get_resource_info("/api/media/")
        assert resource_type == "media"
        assert resource_id is None
