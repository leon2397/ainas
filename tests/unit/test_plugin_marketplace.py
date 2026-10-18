"""
插件市场模块单元测试
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import json


class TestPluginRegistry:
    """插件注册表测试"""
    
    @pytest.fixture
    def registry(self):
        """创建插件注册表"""
        from plugins.marketplace.registry import PluginRegistry
        registry = PluginRegistry()
        registry.db = Mock()
        return registry
    
    def test_register_plugin(self, registry):
        """测试注册插件"""
        registry.db.fetch_one = Mock(return_value=None)  # 插件不存在
        registry.db.execute = Mock(return_value=None)
        registry.db.fetch_val = Mock(return_value=1)
        
        result = registry.register_plugin(
            name="test_plugin",
            version="1.0.0",
            author="test_author",
            description="Test plugin",
            plugin_type="storage"
        )
        
        assert result is not None
        assert result["name"] == "test_plugin"
    
    def test_register_duplicate_plugin(self, registry):
        """测试注册重复插件"""
        registry.db.fetch_one = Mock(return_value={"id": 1, "name": "test_plugin"})
        
        with pytest.raises(ValueError, match="already registered"):
            registry.register_plugin(name="test_plugin", version="1.0.0")
    
    def test_unregister_plugin(self, registry):
        """测试注销插件"""
        registry.db.fetch_one = Mock(return_value={
            "id": 1,
            "name": "test_plugin",
            "is_active": True
        })
        registry.db.execute = Mock(return_value=None)
        
        result = registry.unregister_plugin(name="test_plugin")
        
        assert result is True
    
    def test_get_plugin(self, registry):
        """测试获取插件"""
        registry.db.fetch_one = Mock(return_value={
            "id": 1,
            "name": "test_plugin",
            "version": "1.0.0",
            "is_active": True
        })
        
        plugin = registry.get_plugin(name="test_plugin")
        
        assert plugin is not None
        assert plugin["name"] == "test_plugin"
    
    def test_list_plugins(self, registry):
        """测试列出所有插件"""
        registry.db.fetch_all = Mock(return_value=[
            {"id": 1, "name": "plugin1", "is_active": True},
            {"id": 2, "name": "plugin2", "is_active": False}
        ])
        
        plugins = registry.list_plugins()
        
        assert len(plugins) == 2
    
    def test_list_plugins_by_type(self, registry):
        """测试按类型列出插件"""
        registry.db.fetch_all = Mock(return_value=[
            {"id": 1, "name": "storage_plugin", "plugin_type": "storage"}
        ])
        
        plugins = registry.list_plugins(plugin_type="storage")
        
        assert all(p["plugin_type"] == "storage" for p in plugins)
    
    def test_list_active_plugins(self, registry):
        """测试列出活跃插件"""
        registry.db.fetch_all = Mock(return_value=[
            {"id": 1, "name": "active_plugin", "is_active": True}
        ])
        
        plugins = registry.list_active_plugins()
        
        assert all(p["is_active"] for p in plugins)


class TestPluginInstallation:
    """插件安装测试"""
    
    @pytest.fixture
    def installer(self):
        """创建插件安装器"""
        from plugins.marketplace.installer import PluginInstaller
        installer = PluginInstaller()
        installer.registry = Mock()
        installer.downloader = Mock()
        installer.validator = Mock()
        return installer
    
    def test_install_from_marketplace(self, installer):
        """测试从市场安装插件"""
        installer.registry.fetch_one = Mock(return_value=None)
        installer.downloader.download = Mock(return_value="/tmp/plugin.zip")
        installer.validator.validate = Mock(return_value=True)
        installer.registry.register_plugin = Mock(return_value={"id": 1})
        
        result = installer.install(
            name="marketplace_plugin",
            source="marketplace"
        )
        
        assert result["success"] is True
    
    def test_install_from_url(self, installer):
        """测试从URL安装插件"""
        installer.downloader.download = Mock(return_value="/tmp/plugin.zip")
        installer.validator.validate = Mock(return_value=True)
        installer.registry.register_plugin = Mock(return_value={"id": 1})
        
        result = installer.install(
            name="remote_plugin",
            source="https://example.com/plugin.zip"
        )
        
        assert result["success"] is True
    
    def test_install_from_local(self, installer):
        """测试从本地安装插件"""
        installer.validator.validate = Mock(return_value=True)
        installer.registry.register_plugin = Mock(return_value={"id": 1})
        
        result = installer.install(
            name="local_plugin",
            source="/local/plugin.zip"
        )
        
        assert result["success"] is True
    
    def test_install_with_dependencies(self, installer):
        """测试安装带依赖的插件"""
        installer.downloader.download = Mock(return_value="/tmp/plugin.zip")
        installer.validator.validate = Mock(return_value=True)
        installer.registry.register_plugin = Mock(return_value={"id": 1})
        installer._install_dependency = Mock(return_value=True)
        
        result = installer.install(
            name="plugin_with_deps",
            source="marketplace",
            dependencies=["dep1", "dep2"]
        )
        
        assert result["success"] is True
        assert installer._install_dependency.call_count == 2
    
    def test_install_invalid_plugin(self, installer):
        """测试安装无效插件"""
        installer.downloader.download = Mock(return_value="/tmp/plugin.zip")
        installer.validator.validate = Mock(return_value=False)
        
        with pytest.raises(ValueError, match="Invalid plugin"):
            installer.install(name="invalid", source="marketplace")
    
    def test_install_already_installed(self, installer):
        """测试安装已安装的插件"""
        installer.registry.fetch_one = Mock(return_value={"id": 1})
        
        with pytest.raises(ValueError, match="already installed"):
            installer.install(name="installed_plugin", source="marketplace")


class TestPluginUninstallation:
    """插件卸载测试"""
    
    @pytest.fixture
    def uninstaller(self):
        """创建插件卸载器"""
        from plugins.marketplace.installer import PluginUninstaller
        uninstaller = PluginUninstaller()
        uninstaller.registry = Mock()
        uninstaller.file_manager = Mock()
        return uninstaller
    
    def test_uninstall_plugin(self, uninstaller):
        """测试卸载插件"""
        uninstaller.registry.get_plugin = Mock(return_value={"id": 1, "name": "test"})
        uninstaller.registry.unregister_plugin = Mock(return_value=True)
        uninstaller.file_manager.delete = Mock(return_value=True)
        
        result = uninstaller.uninstall(name="test_plugin")
        
        assert result["success"] is True
    
    def test_uninstall_with_dependents(self, uninstaller):
        """测试卸载被依赖的插件"""
        uninstaller.registry.get_dependents = Mock(return_value=["plugin_a", "plugin_b"])
        
        with pytest.raises(ValueError, match="dependents"):
            uninstaller.uninstall(name="core_plugin", force=False)
    
    def test_force_uninstall(self, uninstaller):
        """测试强制卸载"""
        uninstaller.registry.get_plugin = Mock(return_value={"id": 1})
        uninstaller.registry.unregister_plugin = Mock(return_value=True)
        uninstaller.file_manager.delete = Mock(return_value=True)
        
        result = uninstaller.uninstall(name="core_plugin", force=True)
        
        assert result["success"] is True


class TestPluginUpdate:
    """插件更新测试"""
    
    @pytest.fixture
    def updater(self):
        """创建插件更新器"""
        from plugins.marketplace.updater import PluginUpdater
        updater = PluginUpdater()
        updater.installer = Mock()
        updater.registry = Mock()
        return updater
    
    def test_check_updates(self, updater):
        """测试检查更新"""
        updater.registry.list_active_plugins = Mock(return_value=[
            {"name": "plugin1", "version": "1.0.0"},
            {"name": "plugin2", "version": "2.0.0"}
        ])
        updater._get_latest_version = Mock(side_effect=["1.5.0", "2.0.0"])
        
        updates = updater.check_updates()
        
        assert len(updates) == 1  # 只有plugin1有更新
        assert updates[0]["name"] == "plugin1"
        assert updates[0]["current"] == "1.0.0"
        assert updates[0]["latest"] == "1.5.0"
    
    def test_update_plugin(self, updater):
        """测试更新插件"""
        updater.installer.install = Mock(return_value={"success": True})
        
        result = updater.update(name="test_plugin")
        
        assert result["success"] is True
    
    def test_update_all_plugins(self, updater):
        """测试更新所有插件"""
        updater.check_updates = Mock(return_value=[
            {"name": "plugin1"},
            {"name": "plugin2"}
        ])
        updater.installer.install = Mock(return_value={"success": True})
        
        result = updater.update_all()
        
        assert result["updated"] == 2


class TestPluginMarketplace:
    """插件市场测试"""
    
    @pytest.fixture
    def marketplace(self):
        """创建插件市场"""
        from plugins.marketplace.marketplace import PluginMarketplace
        marketplace = PluginMarketplace()
        marketplace.api_client = Mock()
        return marketplace
    
    def test_search_plugins(self, marketplace):
        """测试搜索插件"""
        marketplace.api_client.search = Mock(return_value=[
            {"name": "plugin1", "description": "test plugin"},
            {"name": "plugin2", "description": "another test"}
        ])
        
        results = marketplace.search(query="test")
        
        assert len(results) == 2
    
    def test_search_with_filters(self, marketplace):
        """测试带过滤器的搜索"""
        marketplace.api_client.search = Mock(return_value=[
            {"name": "storage_plugin", "plugin_type": "storage", "rating": 4.5}
        ])
        
        results = marketplace.search(
            query="storage",
            plugin_type="storage",
            min_rating=4.0
        )
        
        assert len(results) == 1
    
    def test_get_plugin_details(self, marketplace):
        """测试获取插件详情"""
        marketplace.api_client.get_plugin = Mock(return_value={
            "name": "test_plugin",
            "version": "1.0.0",
            "author": "test_author",
            "downloads": 1000,
            "rating": 4.5,
            "description": "A test plugin",
            "screenshots": [],
            "reviews": []
        })
        
        details = marketplace.get_plugin_details(name="test_plugin")
        
        assert details["name"] == "test_plugin"
        assert details["downloads"] == 1000
    
    def test_get_featured_plugins(self, marketplace):
        """测试获取精选插件"""
        marketplace.api_client.get_featured = Mock(return_value=[
            {"name": "featured1", "featured": True},
            {"name": "featured2", "featured": True}
        ])
        
        plugins = marketplace.get_featured_plugins()
        
        assert len(plugins) == 2
    
    def test_get_plugins_by_category(self, marketplace):
        """测试按类别获取插件"""
        marketplace.api_client.get_by_category = Mock(return_value=[
            {"name": "plugin1", "category": "storage"}
        ])
        
        plugins = marketplace.get_plugins_by_category("storage")
        
        assert all(p["category"] == "storage" for p in plugins)
    
    def test_rate_plugin(self, marketplace):
        """测试评价插件"""
        marketplace.api_client.submit_rating = Mock(return_value={"success": True})
        
        result = marketplace.rate_plugin(
            name="test_plugin",
            rating=5,
            review="Great plugin!"
        )
        
        assert result["success"] is True
    
    def test_download_plugin(self, marketplace):
        """测试下载插件"""
        marketplace.api_client.get_download_url = Mock(return_value="https://example.com/plugin.zip")
        
        url = marketplace.get_download_url(name="test_plugin")
        
        assert url is not None


class TestPluginLifecycle:
    """插件生命周期测试"""
    
    @pytest.fixture
    def lifecycle(self):
        """创建插件生命周期管理器"""
        from plugins.marketplace.lifecycle import PluginLifecycle
        lifecycle = PluginLifecycle()
        lifecycle.registry = Mock()
        lifecycle.loader = Mock()
        return lifecycle
    
    def test_enable_plugin(self, lifecycle):
        """测试启用插件"""
        lifecycle.registry.get_plugin = Mock(return_value={
            "id": 1,
            "name": "test_plugin",
            "is_active": False
        })
        lifecycle.loader.load = Mock(return_value=True)
        lifecycle.registry.update = Mock(return_value=True)
        
        result = lifecycle.enable(name="test_plugin")
        
        assert result is True
    
    def test_disable_plugin(self, lifecycle):
        """测试禁用插件"""
        lifecycle.registry.get_plugin = Mock(return_value={
            "id": 1,
            "name": "test_plugin",
            "is_active": True
        })
        lifecycle.loader.unload = Mock(return_value=True)
        lifecycle.registry.update = Mock(return_value=True)
        
        result = lifecycle.disable(name="test_plugin")
        
        assert result is True
    
    def test_reload_plugin(self, lifecycle):
        """测试重载插件"""
        lifecycle.registry.get_plugin = Mock(return_value={"id": 1})
        lifecycle.loader.reload = Mock(return_value=True)
        
        result = lifecycle.reload(name="test_plugin")
        
        assert result is True
    
    def test_start_plugin(self, lifecycle):
        """测试启动插件"""
        lifecycle.loader.load_and_start = Mock(return_value=True)
        
        result = lifecycle.start(name="test_plugin")
        
        assert result is True
    
    def test_stop_plugin(self, lifecycle):
        """测试停止插件"""
        lifecycle.loader.stop = Mock(return_value=True)
        
        result = lifecycle.stop(name="test_plugin")
        
        assert result is True


class TestPluginSecurity:
    """插件安全测试"""
    
    @pytest.fixture
    def security(self):
        """创建插件安全检查器"""
        from plugins.marketplace.security import PluginSecurity
        security = PluginSecurity()
        return security
    
    def test_verify_signature_valid(self, security):
        """测试验证有效签名"""
        result = security.verify_signature(
            plugin_path="/tmp/plugin.zip",
            signature="valid_signature",
            public_key="key"
        )
        
        assert result is True
    
    def test_verify_signature_invalid(self, security):
        """测试验证无效签名"""
        result = security.verify_signature(
            plugin_path="/tmp/plugin.zip",
            signature="invalid_signature",
            public_key="key"
        )
        
        assert result is False
    
    def test_check_dangerous_permissions(self, security):
        """测试检查危险权限"""
        manifest = {
            "permissions": ["file:read", "network:all", "system:execute"]
        }
        
        warnings = security.check_dangerous_permissions(manifest)
        
        assert len(warnings) > 0
        assert "network:all" in warnings
        assert "system:execute" in warnings
    
    def test_scan_for_malware(self, security):
        """测试恶意软件扫描"""
        security.scanner.scan = Mock(return_value={
            "clean": True,
            "threats": []
        })
        
        result = security.scan_plugin(plugin_path="/tmp/plugin.zip")
        
        assert result["clean"] is True
    
    def test_validate_permissions(self, security):
        """测试验证权限"""
        manifest = {
            "permissions": ["media:read", "album:read"]
        }
        
        result = security.validate_permissions(manifest)
        
        assert result["valid"] is True
        assert len(result["allowed"]) == 2


class TestPluginConfig:
    """插件配置测试"""
    
    @pytest.fixture
    def config(self):
        """创建插件配置管理器"""
        from plugins.marketplace.config import PluginConfig
        config = PluginConfig()
        config.db = Mock()
        return config
    
    def test_save_config(self, config):
        """测试保存配置"""
        config.db.execute = Mock(return_value=None)
        
        result = config.save_config(
            plugin_name="test_plugin",
            config={"setting1": "value1", "setting2": 123}
        )
        
        assert result is True
    
    def test_load_config(self, config):
        """测试加载配置"""
        config.db.fetch_one = Mock(return_value={
            "plugin_name": "test_plugin",
            "config": json.dumps({"setting1": "value1"})
        })
        
        config_data = config.load_config(plugin_name="test_plugin")
        
        assert config_data["setting1"] == "value1"
    
    def test_delete_config(self, config):
        """测试删除配置"""
        config.db.execute = Mock(return_value=None)
        
        result = config.delete_config(plugin_name="test_plugin")
        
        assert result is True
    
    def test_reset_config(self, config):
        """测试重置配置"""
        config.db.execute = Mock(return_value=None)
        config.db.fetch_one = Mock(return_value={
            "default_config": json.dumps({"setting": "default"})
        })
        
        result = config.reset_config(plugin_name="test_plugin")
        
        assert result is True


class TestPluginDependency:
    """插件依赖测试"""
    
    @pytest.fixture
    def dependency(self):
        """创建插件依赖解析器"""
        from plugins.marketplace.dependency import PluginDependency
        dep = PluginDependency()
        dep.registry = Mock()
        return dep
    
    def test_resolve_dependencies(self, dependency):
        """测试解析依赖"""
        dependency.registry.get_plugin = Mock(return_value=None)
        dependency._fetch_package_info = Mock(return_value={
            "dependencies": {"dep1": ">=1.0.0", "dep2": ">=2.0.0"}
        })
        
        deps = dependency.resolve(name="plugin", version="1.0.0")
        
        assert "dep1" in deps
        assert "dep2" in deps
    
    def test_check_conflicts(self, dependency):
        """测试检查冲突"""
        dependency.registry.list_active_plugins = Mock(return_value=[
            {"name": "old_plugin", "version": "1.0.0"}
        ])
        
        conflicts = dependency.check_conflicts(
            new_plugin="new_plugin",
            version="2.0.0"
        )
        
        assert isinstance(conflicts, list)
    
    def test_install_order(self, dependency):
        """测试安装顺序"""
        deps = {
            "plugin_a": ["plugin_b", "plugin_c"],
            "plugin_b": ["plugin_c"],
            "plugin_c": []
        }
        
        order = dependency.get_install_order(deps)
        
        # plugin_c 应该在最前面
        assert order[0] == "plugin_c"
