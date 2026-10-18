"""
RBAC权限系统单元测试
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import json


class TestRBACManager:
    """RBAC管理器测试"""
    
    @pytest.fixture
    def rbac_manager(self):
        """创建RBAC管理器实例"""
        from core.rbac.manager import RBACManager
        manager = RBACManager()
        # Mock数据库
        manager.db = Mock()
        return manager
    
    def test_role_creation(self, rbac_manager):
        """测试角色创建"""
        # Mock数据库返回
        rbac_manager.db.fetch_one = Mock(return_value=None)  # 角色不存在
        rbac_manager.db.execute = Mock(return_value=None)
        rbac_manager.db.fetch_val = Mock(return_value=1)  # 返回新角色ID
        
        role = rbac_manager.create_role(
            name="test_role",
            description="测试角色",
            permissions=["media:read", "album:read"]
        )
        
        assert role is not None
        assert role["name"] == "test_role"
        assert "media:read" in role["permissions"]
    
    def test_role_already_exists(self, rbac_manager):
        """测试角色已存在"""
        rbac_manager.db.fetch_one = Mock(return_value={"id": 1, "name": "test_role"})
        
        with pytest.raises(ValueError, match="Role already exists"):
            rbac_manager.create_role(name="test_role")
    
    def test_get_role_by_name(self, rbac_manager):
        """测试通过名称获取角色"""
        rbac_manager.db.fetch_one = Mock(return_value={
            "id": 1,
            "name": "admin",
            "description": "管理员",
            "permissions": json.dumps(["*"]),
            "is_system": 1
        })
        
        role = rbac_manager.get_role_by_name("admin")
        
        assert role is not None
        assert role["name"] == "admin"
        assert role["is_system"] is True
    
    def test_get_role_not_found(self, rbac_manager):
        """测试角色不存在"""
        rbac_manager.db.fetch_one = Mock(return_value=None)
        
        role = rbac_manager.get_role_by_name("nonexistent")
        
        assert role is None
    
    def test_list_roles(self, rbac_manager):
        """测试列出所有角色"""
        rbac_manager.db.fetch_all = Mock(return_value=[
            {"id": 1, "name": "admin", "description": "管理员", "is_system": 1},
            {"id": 2, "name": "user", "description": "普通用户", "is_system": 0}
        ])
        
        roles = rbac_manager.list_roles()
        
        assert len(roles) == 2
        assert roles[0]["name"] == "admin"
    
    def test_update_role_permissions(self, rbac_manager):
        """测试更新角色权限"""
        rbac_manager.db.fetch_one = Mock(return_value={
            "id": 1,
            "name": "operator",
            "is_system": 0
        })
        rbac_manager.db.execute = Mock(return_value=None)
        
        result = rbac_manager.update_role_permissions(
            role_id=1,
            permissions=["media:read", "media:write", "album:read"]
        )
        
        assert result is True
    
    def test_update_system_role_fails(self, rbac_manager):
        """测试更新系统角色失败"""
        rbac_manager.db.fetch_one = Mock(return_value={
            "id": 1,
            "name": "admin",
            "is_system": 1
        })
        
        with pytest.raises(ValueError, match="Cannot modify system role"):
            rbac_manager.update_role_permissions(1, ["media:read"])
    
    def test_delete_role(self, rbac_manager):
        """测试删除角色"""
        rbac_manager.db.fetch_one = Mock(return_value={
            "id": 2,
            "name": "custom_role",
            "is_system": 0
        })
        rbac_manager.db.execute = Mock(return_value=None)
        
        result = rbac_manager.delete_role(2)
        
        assert result is True
    
    def test_delete_system_role_fails(self, rbac_manager):
        """测试删除系统角色失败"""
        rbac_manager.db.fetch_one = Mock(return_value={
            "id": 1,
            "name": "admin",
            "is_system": 1
        })
        
        with pytest.raises(ValueError, match="Cannot delete system role"):
            rbac_manager.delete_role(1)


class TestPermissionCheck:
    """权限检查测试"""
    
    @pytest.fixture
    def rbac_manager(self):
        """创建RBAC管理器实例"""
        from core.rbac.manager import RBACManager
        manager = RBACManager()
        manager.db = Mock()
        return manager
    
    def test_check_permission_exact_match(self, rbac_manager):
        """测试精确权限匹配"""
        rbac_manager.db.fetch_one = Mock(return_value={
            "permissions": json.dumps(["media:read", "album:read"])
        })
        
        result = rbac_manager.check_permission("user", "media:read")
        
        assert result is True
    
    def test_check_permission_no_match(self, rbac_manager):
        """测试权限不匹配"""
        rbac_manager.db.fetch_one = Mock(return_value={
            "permissions": json.dumps(["media:read"])
        })
        
        result = rbac_manager.check_permission("user", "album:delete")
        
        assert result is False
    
    def test_check_permission_wildcard(self, rbac_manager):
        """测试通配符权限"""
        rbac_manager.db.fetch_one = Mock(return_value={
            "permissions": json.dumps(["*"])
        })
        
        result = rbac_manager.check_permission("admin", "any:permission")
        
        assert result is True
    
    def test_check_permission_resource_wildcard(self, rbac_manager):
        """测试资源级通配符"""
        rbac_manager.db.fetch_one = Mock(return_value={
            "permissions": json.dumps(["media:*"])
        })
        
        assert rbac_manager.check_permission("user", "media:read") is True
        assert rbac_manager.check_permission("user", "media:write") is True
        assert rbac_manager.check_permission("user", "media:delete") is True
        assert rbac_manager.check_permission("user", "album:read") is False
    
    def test_check_multiple_permissions_all_required(self, rbac_manager):
        """测试检查多个权限 - 全部需要"""
        rbac_manager.db.fetch_one = Mock(return_value={
            "permissions": json.dumps(["media:read", "media:write", "album:read"])
        })
        
        result = rbac_manager.check_permissions(
            "user",
            ["media:read", "album:read"],
            require_all=True
        )
        
        assert result is True
    
    def test_check_multiple_permissions_all_required_fails(self, rbac_manager):
        """测试检查多个权限 - 缺少权限"""
        rbac_manager.db.fetch_one = Mock(return_value={
            "permissions": json.dumps(["media:read"])
        })
        
        result = rbac_manager.check_permissions(
            "user",
            ["media:read", "album:read"],
            require_all=True
        )
        
        assert result is False
    
    def test_check_multiple_permissions_any_allowed(self, rbac_manager):
        """测试检查多个权限 - 任一即可"""
        rbac_manager.db.fetch_one = Mock(return_value={
            "permissions": json.dumps(["media:read"])
        })
        
        result = rbac_manager.check_permissions(
            "user",
            ["media:read", "album:read"],
            require_all=False
        )
        
        assert result is True


class TestUserRoleAssignment:
    """用户角色分配测试"""
    
    @pytest.fixture
    def rbac_manager(self):
        """创建RBAC管理器实例"""
        from core.rbac.manager import RBACManager
        manager = RBACManager()
        manager.db = Mock()
        return manager
    
    def test_assign_role_to_user(self, rbac_manager):
        """测试分配角色给用户"""
        rbac_manager.db.fetch_one = Mock(return_value={"id": 1, "name": "operator"})
        rbac_manager.db.execute = Mock(return_value=None)
        
        result = rbac_manager.assign_role_to_user(user_id=1, role_name="operator")
        
        assert result is True
    
    def test_assign_role_user_not_found(self, rbac_manager):
        """测试分配角色给用户不存在"""
        rbac_manager.db.fetch_one = Mock(return_value=None)
        
        with pytest.raises(ValueError, match="Role not found"):
            rbac_manager.assign_role_to_user(user_id=1, role_name="nonexistent")
    
    def test_get_user_role(self, rbac_manager):
        """测试获取用户角色"""
        rbac_manager.db.fetch_one = Mock(return_value={
            "id": 1,
            "name": "admin",
            "permissions": json.dumps(["*"]),
            "is_system": 1
        })
        
        role = rbac_manager.get_user_role(user_id=1)
        
        assert role is not None
        assert role["name"] == "admin"
    
    def test_get_user_role_default(self, rbac_manager):
        """测试获取用户默认角色"""
        rbac_manager.db.fetch_one = Mock(side_effect=[
            None,  # 用户没有角色
            {"id": 2, "name": "viewer", "permissions": json.dumps(["media:read"])}
        ])
        
        role = rbac_manager.get_user_role(user_id=999)
        
        assert role is not None
        assert role["name"] == "viewer"
    
    def test_remove_user_role(self, rbac_manager):
        """测试移除用户角色"""
        rbac_manager.db.execute = Mock(return_value=None)
        
        result = rbac_manager.remove_user_role(user_id=1)
        
        assert result is True


class TestRoleHierarchy:
    """角色层级测试"""
    
    @pytest.fixture
    def rbac_manager(self):
        """创建RBAC管理器实例"""
        from core.rbac.manager import RBACManager
        manager = RBACManager()
        manager.db = Mock()
        return manager
    
    def test_role_inherits_permissions(self, rbac_manager):
        """测试角色继承权限"""
        rbac_manager.db.fetch_one = Mock(return_value={
            "id": 2,
            "name": "operator",
            "parent_role_id": 1,
            "permissions": json.dumps(["album:*"])
        })
        rbac_manager.db.fetch_val = Mock(return_value=json.dumps(["media:*"]))
        
        permissions = rbac_manager.get_role_permissions_with_inheritance("operator")
        
        assert "media:*" in permissions
        assert "album:*" in permissions
    
    def test_role_inheritance_chain(self, rbac_manager):
        """测试角色继承链"""
        # admin -> manager -> operator
        rbac_manager.db.fetch_one = Mock(side_effect=[
            {"id": 3, "name": "operator", "parent_role_id": 2, "permissions": json.dumps([])},
            {"id": 2, "name": "manager", "parent_role_id": 1, "permissions": json.dumps(["device:*"])},
            {"id": 1, "name": "admin", "parent_role_id": None, "permissions": json.dumps(["*"])}
        ])
        
        permissions = rbac_manager.get_role_permissions_with_inheritance("operator")
        
        assert "*" in permissions
        assert "device:*" in permissions


class TestSystemRoles:
    """系统角色测试"""
    
    @pytest.fixture
    def rbac_manager(self):
        """创建RBAC管理器实例"""
        from core.rbac.manager import RBACManager
        manager = RBACManager()
        manager.db = Mock()
        return manager
    
    def test_super_admin_has_all_permissions(self, rbac_manager):
        """测试超级管理员拥有所有权限"""
        rbac_manager.db.fetch_one = Mock(return_value={
            "permissions": json.dumps(["*"])
        })
        
        assert rbac_manager.check_permission("super_admin", "any:action") is True
        assert rbac_manager.check_permission("super_admin", "system:config") is True
    
    def test_admin_permissions(self, rbac_manager):
        """测试管理员权限"""
        rbac_manager.db.fetch_one = Mock(return_value={
            "permissions": json.dumps([
                "user:*",
                "system:*",
                "audit:*",
                "media:read",
                "album:read"
            ])
        })
        
        assert rbac_manager.check_permission("admin", "user:create") is True
        assert rbac_manager.check_permission("admin", "system:config") is True
        assert rbac_manager.check_permission("admin", "audit:read") is True
    
    def test_operator_permissions(self, rbac_manager):
        """测试操作员权限"""
        rbac_manager.db.fetch_one = Mock(return_value={
            "permissions": json.dumps([
                "media:*",
                "album:*",
                "device:*"
            ])
        })
        
        assert rbac_manager.check_permission("operator", "media:write") is True
        assert rbac_manager.check_permission("operator", "user:create") is False
    
    def test_viewer_permissions(self, rbac_manager):
        """测试查看者权限"""
        rbac_manager.db.fetch_one = Mock(return_value={
            "permissions": json.dumps([
                "media:read",
                "album:read",
                "device:read"
            ])
        })
        
        assert rbac_manager.check_permission("viewer", "media:read") is True
        assert rbac_manager.check_permission("viewer", "media:write") is False
    
    def test_guest_permissions(self, rbac_manager):
        """测试访客权限"""
        rbac_manager.db.fetch_one = Mock(return_value={
            "permissions": json.dumps([
                "media:read"
            ])
        })
        
        assert rbac_manager.check_permission("guest", "media:read") is True
        assert rbac_manager.check_permission("guest", "album:read") is False


class TestRBACDecorators:
    """RBAC装饰器测试"""
    
    @pytest.fixture
    def mock_user(self):
        """创建模拟用户"""
        return {
            "id": 1,
            "username": "test_user",
            "role": "operator"
        }
    
    def test_require_permission_decorator(self, mock_user):
        """测试权限装饰器"""
        from core.rbac.decorators import require_permission
        
        @require_permission("media:read")
        def protected_function(user):
            return "success"
        
        # Mock权限检查
        with patch('core.rbac.decorators.rbac_manager.check_permission', return_value=True):
            result = protected_function(mock_user)
            assert result == "success"
    
    def test_require_permission_decorator_denied(self, mock_user):
        """测试权限装饰器拒绝访问"""
        from core.rbac.decorators import require_permission
        
        @require_permission("admin:action")
        def protected_function(user):
            return "success"
        
        with patch('core.rbac.decorators.rbac_manager.check_permission', return_value=False):
            with pytest.raises(PermissionError):
                protected_function(mock_user)
    
    def test_require_role_decorator(self, mock_user):
        """测试角色装饰器"""
        from core.rbac.decorators import require_role
        
        @require_role(["admin", "operator"])
        def admin_function(user):
            return "admin success"
        
        result = admin_function(mock_user)
        assert result == "admin success"
    
    def test_require_role_decorator_denied(self, mock_user):
        """测试角色装饰器拒绝访问"""
        from core.rbac.decorators import require_role
        
        @require_role(["admin"])
        def admin_only_function(user):
            return "admin only"
        
        with pytest.raises(PermissionError):
            admin_only_function(mock_user)
