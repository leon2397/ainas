"""
认证模块单元测试
"""
import pytest
from jose import jwt
from jose.exceptions import JWTError, JWSError
from datetime import datetime, timedelta
from unittest.mock import Mock, patch


class TestAuthManager:
    """认证管理器测试"""
    
    @pytest.fixture
    def auth_manager(self):
        """创建认证管理器实例"""
        from core.auth import AuthManager
        return AuthManager()
    
    def test_password_hashing(self, auth_manager):
        """测试密码哈希"""
        password = "test_password123"
        hashed = auth_manager.hash_password(password)
        
        # 验证哈希值
        assert hashed != password
        assert len(hashed) > 20
        
        # 验证密码匹配
        assert auth_manager.verify_password(password, hashed) is True
        assert auth_manager.verify_password("wrong_password", hashed) is False
    
    def test_create_access_token(self, auth_manager):
        """测试创建访问令牌"""
        user_id = 1
        username = "test_user"
        role = "user"
        
        token = auth_manager.create_access_token(
            user_id=user_id,
            username=username,
            role=role,
            expires_delta=timedelta(hours=1)
        )
        
        # 验证令牌格式
        assert token is not None
        assert isinstance(token, str)
        
        # 解码验证
        payload = jwt.decode(
            token, 
            auth_manager.secret_key, 
            algorithms=[auth_manager.algorithm]
        )
        
        assert payload["sub"] == str(user_id)
        assert payload["username"] == username
        assert payload["role"] == role
        assert "exp" in payload
    
    def test_token_expiration(self, auth_manager):
        """测试令牌过期"""
        # 创建已过期的令牌
        expired_token = auth_manager.create_access_token(
            user_id=1,
            username="test",
            role="user",
            expires_delta=timedelta(seconds=-1)
        )
        
        # 验证过期令牌
        with pytest.raises(jwt.ExpiredSignatureError):
            jwt.decode(
                expired_token,
                auth_manager.secret_key,
                algorithms=[auth_manager.algorithm]
            )
    
    @pytest.mark.asyncio
    async def test_authenticate_user_success(self, auth_manager):
        """测试用户认证成功"""
        # Mock数据库
        mock_db = Mock()
        mock_db.fetch_one = Mock(return_value={
            "id": 1,
            "username": "test_user",
            "password_hash": auth_manager.hash_password("password123"),
            "role": "user",
            "is_active": 1
        })
        
        auth_manager.db = mock_db
        
        user = await auth_manager.authenticate_user("test_user", "password123")
        
        assert user is not None
        assert user["username"] == "test_user"
        assert user["role"] == "user"
    
    @pytest.mark.asyncio
    async def test_authenticate_user_wrong_password(self, auth_manager):
        """测试用户认证失败-密码错误"""
        mock_db = Mock()
        mock_db.fetch_one = Mock(return_value={
            "id": 1,
            "username": "test_user",
            "password_hash": auth_manager.hash_password("password123"),
            "role": "user",
            "is_active": 1
        })
        
        auth_manager.db = mock_db
        
        user = await auth_manager.authenticate_user("test_user", "wrong_password")
        
        assert user is None
    
    @pytest.mark.asyncio
    async def test_authenticate_user_not_found(self, auth_manager):
        """测试用户认证失败-用户不存在"""
        mock_db = Mock()
        mock_db.fetch_one = Mock(return_value=None)
        
        auth_manager.db = mock_db
        
        user = await auth_manager.authenticate_user("nonexistent", "password")
        
        assert user is None
    
    @pytest.mark.asyncio
    async def test_authenticate_user_inactive(self, auth_manager):
        """测试用户认证失败-用户被禁用"""
        mock_db = Mock()
        mock_db.fetch_one = Mock(return_value={
            "id": 1,
            "username": "test_user",
            "password_hash": auth_manager.hash_password("password123"),
            "role": "user",
            "is_active": 0  # 禁用
        })
        
        auth_manager.db = mock_db
        
        user = await auth_manager.authenticate_user("test_user", "password123")
        
        assert user is None


class TestJWTValidation:
    """JWT验证测试"""
    
    @pytest.fixture
    def auth_manager(self):
        from core.auth import AuthManager
        return AuthManager()
    
    def test_valid_token(self, auth_manager):
        """测试有效令牌"""
        token = auth_manager.create_access_token(
            user_id=1,
            username="test",
            role="user"
        )
        
        payload = auth_manager.decode_token(token)
        
        assert payload is not None
        assert payload["sub"] == "1"
    
    def test_invalid_token_format(self, auth_manager):
        """测试无效令牌格式"""
        with pytest.raises(JWTError):
            auth_manager.decode_token("invalid_token")
    
    def test_tampered_token(self, auth_manager):
        """测试被篡改的令牌"""
        token = auth_manager.create_access_token(1, "test", "user")
        tampered = token[:-10] + "XXXXXXXXXX"  # 篡改末尾
        
        with pytest.raises(JWSError):
            auth_manager.decode_token(tampered)


class TestRoleBasedAccess:
    """基于角色的访问控制测试"""
    
    def test_admin_can_access_admin_routes(self):
        """测试管理员可以访问管理路由"""
        from core.auth import require_role
        
        admin_user = {"role": "admin"}
        
        # 管理员应该通过检查
        assert require_role(admin_user, ["admin"]) is True
        assert require_role(admin_user, ["admin", "user"]) is True
    
    def test_user_cannot_access_admin_routes(self):
        """测试普通用户不能访问管理路由"""
        from core.auth import require_role
        
        normal_user = {"role": "user"}
        
        # 普通用户不应该通过管理员检查
        assert require_role(normal_user, ["admin"]) is False
    
    def test_guest_limited_access(self):
        """测试访客权限受限"""
        from core.auth import require_role
        
        guest_user = {"role": "guest"}
        
        # 访客只能访问访客路由
        assert require_role(guest_user, ["guest"]) is True
        assert require_role(guest_user, ["user"]) is False
        assert require_role(guest_user, ["admin"]) is False
