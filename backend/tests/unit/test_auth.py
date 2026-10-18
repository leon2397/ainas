"""
test_auth.py - 认证模块单元测试
===============================
覆盖范围：
  1. 密码哈希与验证
  2. JWT Token 生成与验证
  3. 用户认证流程
  4. 角色与权限检查
  5. Fallback 用户加载

运行：
  cd backend
  pytest tests/unit/test_auth.py -v
"""

import pytest
import sys
import os
import tempfile
from pathlib import Path
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, AsyncMock, patch

# 设置测试环境
os.environ["AI_NAS_JWT_SECRET"] = "test-secret-key-for-unit-tests"
os.environ["AI_NAS_DB_PATH"] = ":memory:"

# 添加 backend 到 path
backend_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_root))

from core.auth import AuthManager, ROLES, PERMISSION_MIN_ROLE, ROLE_LEVELS


class TestPasswordHashing:
    """密码哈希测试"""

    def setup_method(self):
        """每个测试方法前运行"""
        self.auth = AuthManager()

    def test_hash_password_generates_salt(self):
        """测试哈希密码时自动生成 salt"""
        password = "test_password_123"
        hashed, salt = self.auth._hash_password(password)
        
        assert hashed is not None
        assert len(hashed) == 64  # SHA256 hex = 64 chars
        assert salt is not None
        assert len(salt) == 32  # 16 bytes hex = 32 chars

    def test_hash_password_different_salts(self):
        """测试相同密码不同 salt 生成不同哈希"""
        password = "same_password"
        hash1, salt1 = self.auth._hash_password(password)
        hash2, salt2 = self.auth._hash_password(password)
        
        assert hash1 != hash2  # 不同 salt 导致不同哈希
        assert salt1 != salt2

    def test_verify_password_correct(self):
        """测试正确密码验证通过"""
        password = "correct_password"
        hashed, salt = self.auth._hash_password(password)
        
        result = self.auth.verify_password(password, hashed, salt)
        assert result is True

    def test_verify_password_incorrect(self):
        """测试错误密码验证失败"""
        password = "correct_password"
        hashed, salt = self.auth._hash_password(password)
        
        result = self.auth.verify_password("wrong_password", hashed, salt)
        assert result is False

    def test_verify_password_empty(self):
        """测试空密码处理"""
        password = "correct_password"
        hashed, salt = self.auth._hash_password(password)
        
        result = self.auth.verify_password("", hashed, salt)
        assert result is False


class TestRolesAndPermissions:
    """角色与权限测试"""

    def test_roles_defined(self):
        """测试角色定义完整"""
        assert "admin" in ROLES
        assert "editor" in ROLES
        assert "viewer" in ROLES

    def test_role_has_permissions(self):
        """测试每个角色有权限配置"""
        for role, config in ROLES.items():
            assert "permissions" in config
            assert "label" in config
            assert isinstance(config["permissions"], list)

    def test_admin_has_all_permissions(self):
        """测试 admin 角色拥有所有权限"""
        assert "all" in ROLES["admin"]["permissions"]

    def test_permission_min_role_mapping(self):
        """测试权限到最低角色映射"""
        assert PERMISSION_MIN_ROLE["media_read"] == "viewer"
        assert PERMISSION_MIN_ROLE["media_write"] == "editor"
        assert PERMISSION_MIN_ROLE["user_manage"] == "admin"

    def test_role_levels_ascending(self):
        """测试角色层级递增"""
        assert ROLE_LEVELS["viewer"] < ROLE_LEVELS["editor"]
        assert ROLE_LEVELS["editor"] < ROLE_LEVELS["admin"]


class TestAuthManager:
    """AuthManager 类测试"""

    def setup_method(self):
        """每个测试方法前运行"""
        self.auth = AuthManager()

    def test_auth_manager_initialization(self):
        """测试 AuthManager 初始化"""
        assert self.auth._db is None
        assert self.auth._fallback_users == {}
        assert self.auth._fallback_loaded is False

    def test_use_db_without_db(self):
        """测试未设置数据库时 _use_db 返回 False"""
        assert self.auth._use_db is False

    def test_set_db(self):
        """测试设置数据库引用"""
        mock_db = Mock()
        self.auth.set_db(mock_db)
        assert self.auth._db is mock_db
        assert self.auth._use_db is True

    def test_load_fallback_users(self):
        """测试加载内存用户（降级方案）"""
        self.auth._load_fallback_users()
        
        assert self.auth._fallback_loaded is True
        assert "admin" in self.auth._fallback_users
        
        admin = self.auth._fallback_users["admin"]
        assert admin["username"] == "admin"
        assert admin["role"] == "admin"
        assert admin["disabled"] is False
        assert "hashed_password" in admin
        assert "salt" in admin

    def test_load_fallback_users_idempotent(self):
        """测试加载内存用户幂等性（多次调用只加载一次）"""
        self.auth._load_fallback_users()
        salt1 = self.auth._fallback_users["admin"]["salt"]
        
        self.auth._load_fallback_users()
        salt2 = self.auth._fallback_users["admin"]["salt"]
        
        # 第二次调用不应重新生成
        assert salt1 == salt2

    @pytest.mark.asyncio
    async def test_get_user_fallback(self):
        """测试获取用户（降级模式）"""
        user = await self.auth.get_user("admin")
        
        assert user is not None
        assert user["username"] == "admin"
        assert user["role"] == "admin"

    @pytest.mark.asyncio
    async def test_get_user_nonexistent(self):
        """测试获取不存在的用户"""
        user = await self.auth.get_user("nonexistent_user_xyz")
        assert user is None

    @pytest.mark.asyncio
    async def test_get_all_users_safe(self):
        """测试获取所有用户（不含密码）"""
        users = await self.auth.get_all_users_safe()
        
        assert len(users) >= 1
        for user in users:
            assert "username" in user
            assert "role" in user
            assert "hashed_password" not in user
            assert "salt" not in user

    @pytest.mark.asyncio
    async def test_create_user_fallback(self):
        """测试创建用户（降级模式）"""
        username = "test_user_" + str(datetime.now().timestamp())
        password = "test_password_123"
        
        user = await self.auth.create_user(username, password, role="viewer")
        
        assert user["username"] == username
        assert user["role"] == "viewer"
        assert user["disabled"] is False
        
        # 验证用户可以登录
        authenticated = await self.auth.authenticate_user(username, password)
        assert authenticated is not None
        assert authenticated["username"] == username

    @pytest.mark.asyncio
    async def test_update_password_fallback(self):
        """测试修改密码（降级模式）"""
        username = "test_user_" + str(datetime.now().timestamp())
        password = "old_password"
        
        # 创建用户
        await self.auth.create_user(username, password, role="viewer")
        
        # 修改密码
        new_password = "new_password_456"
        result = await self.auth.update_password(username, password, new_password)
        assert result is True
        
        # 验证旧密码失效
        auth_old = await self.auth.authenticate_user(username, password)
        assert auth_old is None
        
        # 验证新密码有效
        auth_new = await self.auth.authenticate_user(username, new_password)
        assert auth_new is not None

    @pytest.mark.asyncio
    async def test_update_password_wrong_old(self):
        """测试旧密码错误时修改失败"""
        username = "test_user_" + str(datetime.now().timestamp())
        
        await self.auth.create_user(username, "correct_old", role="viewer")
        
        with pytest.raises(ValueError, match="旧密码错误"):
            await self.auth.update_password(username, "wrong_old", "new_password")

    @pytest.mark.asyncio
    async def test_update_user_role(self):
        """测试更新用户角色"""
        username = "test_user_" + str(datetime.now().timestamp())
        
        await self.auth.create_user(username, "password", role="viewer")
        await self.auth.update_user_role(username, "editor")
        
        user = await self.auth.get_user(username)
        assert user["role"] == "editor"

    @pytest.mark.asyncio
    async def test_update_user_invalid_role(self):
        """测试无效角色"""
        username = "test_user_" + str(datetime.now().timestamp())
        
        with pytest.raises(ValueError, match="无效角色"):
            await self.auth.update_user_role(username, "invalid_role")


class TestJWTToken:
    """JWT Token 测试"""

    def setup_method(self):
        """每个测试方法前运行"""
        self.auth = AuthManager()

    @pytest.mark.asyncio
    async def test_create_access_token(self):
        """测试创建访问令牌"""
        username = "test_user"
        token = self.auth.create_access_token(data={"sub": username})
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    @pytest.mark.asyncio
    async def test_create_access_token_expires(self):
        """测试创建带过期时间的令牌"""
        username = "test_user"
        # 创建 1 秒后过期的 token
        token = self.auth.create_access_token(
            data={"sub": username},
            expires_delta=timedelta(seconds=1)
        )
        
        assert token is not None
        
        # JWT 解码验证过期时间
        from jose import jwt as jose_jwt
        payload = jose_jwt.decode(token, os.environ["AI_NAS_JWT_SECRET"], algorithms=["HS256"])
        
        # 检查过期时间
        exp = payload.get("exp")
        assert exp is not None
        
        # 验证过期时间约为 1 秒后
        import time
        now = int(time.time())
        assert abs(exp - now - 1) < 2  # 允许 2 秒误差

    @pytest.mark.asyncio
    async def test_verify_token_valid(self):
        """测试验证有效令牌（通过解码）"""
        username = "test_user"
        token = self.auth.create_access_token(data={"sub": username})
        
        # 使用 jose 解码验证
        from jose import jwt as jose_jwt
        payload = jose_jwt.decode(
            token,
            os.environ["AI_NAS_JWT_SECRET"],
            algorithms=["HS256"]
        )
        
        assert payload is not None
        assert payload.get("sub") == username

    @pytest.mark.asyncio
    async def test_verify_token_invalid(self):
        """测试验证无效令牌"""
        # 无效 token
        from jose import jwt as jose_jwt, JWTError
        
        with pytest.raises(JWTError):
            jose_jwt.decode(
                "invalid.token.here",
                os.environ["AI_NAS_JWT_SECRET"],
                algorithms=["HS256"]
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
