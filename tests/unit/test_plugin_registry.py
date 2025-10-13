"""
Tests for Plugin Registry

Tests plugin registration, lookup, and lifecycle management.
"""

import tempfile
from pathlib import Path

import pytest

from src.plugins.base import BasePlugin, PluginMetadata, PluginType
from src.plugins.registry import PluginRegistry


class MockAgentPlugin(BasePlugin):
    """Mock agent plugin for testing."""

    @property
    def metadata(self):
        return PluginMetadata(
            name="mock-agent",
            version="1.0.0",
            author="Test",
            description="Mock agent plugin",
            plugin_type=PluginType.AGENT,
            dependencies=[],
        )

    def initialize(self):
        self.initialized = True

    def validate(self):
        return True


class MockToolPlugin(BasePlugin):
    """Mock tool plugin for testing."""

    @property
    def metadata(self):
        return PluginMetadata(
            name="mock-tool",
            version="1.0.0",
            author="Test",
            description="Mock tool plugin",
            plugin_type=PluginType.TOOL,
            dependencies=[],
        )

    def initialize(self):
        self.initialized = True

    def validate(self):
        return True


class TestPluginRegistry:
    """Test PluginRegistry functionality."""

    def test_registry_creation(self):
        """Test creating a plugin registry."""
        registry = PluginRegistry()
        assert len(registry.get_plugin_names()) == 0

    def test_register_plugin(self):
        """Test registering a plugin instance."""
        registry = PluginRegistry()
        plugin = MockAgentPlugin()
        plugin.enable()

        registry.register(plugin)

        assert "mock-agent" in registry.get_plugin_names()
        assert registry.get("mock-agent") == plugin

    def test_register_plugin_with_custom_name(self):
        """Test registering plugin with custom name."""
        registry = PluginRegistry()
        plugin = MockAgentPlugin()

        registry.register(plugin, name="custom-name")

        assert "custom-name" in registry.get_plugin_names()
        assert registry.get("custom-name") == plugin

    def test_register_duplicate_plugin(self):
        """Test registering plugin with duplicate name."""
        registry = PluginRegistry()
        plugin1 = MockAgentPlugin()
        plugin2 = MockAgentPlugin()

        registry.register(plugin1)

        with pytest.raises(ValueError, match="already registered"):
            registry.register(plugin2)

    def test_register_class(self):
        """Test registering a plugin class."""
        registry = PluginRegistry()

        registry.register_class(MockAgentPlugin)

        assert "mock-agent" in registry.get_plugin_names()

    def test_register_class_with_custom_name(self):
        """Test registering class with custom name."""
        registry = PluginRegistry()

        registry.register_class(MockAgentPlugin, name="custom-agent")

        assert "custom-agent" in registry.get_plugin_names()

    def test_lazy_loading(self):
        """Test lazy loading of registered class."""
        registry = PluginRegistry()
        registry.register_class(MockAgentPlugin)

        # Plugin not instantiated yet
        stats = registry.get_stats()
        assert stats["instantiated"] == 0
        assert stats["lazy_loaded"] == 1

        # First access triggers instantiation
        plugin = registry.get("mock-agent")
        assert plugin is not None
        assert plugin.is_enabled

        # Now plugin is instantiated
        stats = registry.get_stats()
        assert stats["instantiated"] == 1
        assert stats["lazy_loaded"] == 0

    def test_unregister_plugin(self):
        """Test unregistering a plugin."""
        registry = PluginRegistry()
        plugin = MockAgentPlugin()
        plugin.enable()

        registry.register(plugin)
        assert "mock-agent" in registry.get_plugin_names()

        registry.unregister("mock-agent")
        assert "mock-agent" not in registry.get_plugin_names()
        assert not plugin.is_enabled  # Cleanup called

    def test_get_nonexistent_plugin(self):
        """Test getting plugin that doesn't exist."""
        registry = PluginRegistry()
        plugin = registry.get("nonexistent")
        assert plugin is None

    def test_get_all_plugins(self):
        """Test getting all registered plugins."""
        registry = PluginRegistry()

        plugin1 = MockAgentPlugin()
        plugin2 = MockToolPlugin()
        plugin1.enable()
        plugin2.enable()

        registry.register(plugin1)
        registry.register(plugin2)

        all_plugins = registry.get_all()
        assert len(all_plugins) == 2

    def test_get_all_by_type(self):
        """Test getting plugins filtered by type."""
        registry = PluginRegistry()

        plugin1 = MockAgentPlugin()
        plugin2 = MockToolPlugin()
        plugin1.enable()
        plugin2.enable()

        registry.register(plugin1)
        registry.register(plugin2)

        agents = registry.get_all(plugin_type=PluginType.AGENT)
        assert len(agents) == 1
        assert agents[0].metadata.plugin_type == PluginType.AGENT

        tools = registry.get_all(plugin_type=PluginType.TOOL)
        assert len(tools) == 1
        assert tools[0].metadata.plugin_type == PluginType.TOOL

    def test_get_all_enabled_only(self):
        """Test getting only enabled plugins."""
        registry = PluginRegistry()

        plugin1 = MockAgentPlugin()
        plugin2 = MockToolPlugin()
        plugin1.enable()
        plugin2.enable()
        plugin2.disable()  # Disable second plugin

        registry.register(plugin1)
        registry.register(plugin2)

        enabled = registry.get_all(enabled_only=True)
        assert len(enabled) == 1
        assert enabled[0].is_enabled

    def test_enable_plugin(self):
        """Test enabling a plugin."""
        registry = PluginRegistry()
        registry.register_class(MockAgentPlugin)

        # Plugin not enabled yet (lazy loaded)
        plugin = registry.get("mock-agent")
        assert plugin.is_enabled

        # Disable and re-enable
        plugin.disable()
        assert not plugin.is_enabled

        success = registry.enable_plugin("mock-agent")
        assert success
        assert plugin.is_enabled

    def test_enable_nonexistent_plugin(self):
        """Test enabling plugin that doesn't exist."""
        registry = PluginRegistry()
        success = registry.enable_plugin("nonexistent")
        assert not success

    def test_disable_plugin(self):
        """Test disabling a plugin."""
        registry = PluginRegistry()
        plugin = MockAgentPlugin()
        plugin.enable()
        registry.register(plugin)

        success = registry.disable_plugin("mock-agent")
        assert success
        assert not plugin.is_enabled

    def test_disable_nonexistent_plugin(self):
        """Test disabling plugin that doesn't exist."""
        registry = PluginRegistry()
        success = registry.disable_plugin("nonexistent")
        assert not success

    def test_cleanup_all(self):
        """Test cleaning up all plugins."""
        registry = PluginRegistry()

        plugin1 = MockAgentPlugin()
        plugin2 = MockToolPlugin()
        plugin1.enable()
        plugin2.enable()

        registry.register(plugin1)
        registry.register(plugin2)

        registry.cleanup_all()

        assert len(registry.get_plugin_names()) == 0
        assert not plugin1.is_enabled
        assert not plugin2.is_enabled

    def test_get_stats(self):
        """Test getting registry statistics."""
        registry = PluginRegistry()

        # Register instance
        plugin1 = MockAgentPlugin()
        plugin1.enable()
        registry.register(plugin1)

        # Register class (lazy load)
        registry.register_class(MockToolPlugin)

        stats = registry.get_stats()

        assert stats["total"] == 2
        assert stats["instantiated"] == 1
        assert stats["enabled"] == 1
        assert stats["disabled"] == 0
        assert stats["lazy_loaded"] == 1

    @pytest.fixture
    def temp_plugin_dir(self):
        """Create temporary directory for test plugins."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_load_from_directory(self, temp_plugin_dir):
        """Test loading plugins from directory."""
        # Create test plugin file
        plugin_code = '''
from src.plugins.base import BasePlugin, PluginMetadata, PluginType

class DirectoryPlugin(BasePlugin):
    @property
    def metadata(self):
        return PluginMetadata(
            name="directory-plugin",
            version="1.0.0",
            author="Test",
            description="Plugin loaded from directory",
            plugin_type=PluginType.AGENT,
            dependencies=[],
        )

    def initialize(self):
        pass

    def validate(self):
        return True
'''
        (temp_plugin_dir / "directory_plugin.py").write_text(plugin_code)

        registry = PluginRegistry()
        count = registry.load_from_directory(temp_plugin_dir)

        assert count == 1
        assert "directory-plugin" in registry.get_plugin_names()

    def test_load_from_directory_by_type(self, temp_plugin_dir):
        """Test loading plugins from directory filtered by type."""
        # Create agent plugin
        agent_code = '''
from src.plugins.base import BasePlugin, PluginMetadata, PluginType

class AgentPlugin(BasePlugin):
    @property
    def metadata(self):
        return PluginMetadata(
            name="agent-plugin",
            version="1.0.0",
            author="Test",
            description="Agent plugin",
            plugin_type=PluginType.AGENT,
            dependencies=[],
        )

    def initialize(self):
        pass

    def validate(self):
        return True
'''
        (temp_plugin_dir / "agent.py").write_text(agent_code)

        # Create tool plugin
        tool_code = '''
from src.plugins.base import BasePlugin, PluginMetadata, PluginType

class ToolPlugin(BasePlugin):
    @property
    def metadata(self):
        return PluginMetadata(
            name="tool-plugin",
            version="1.0.0",
            author="Test",
            description="Tool plugin",
            plugin_type=PluginType.TOOL,
            dependencies=[],
        )

    def initialize(self):
        pass

    def validate(self):
        return True
'''
        (temp_plugin_dir / "tool.py").write_text(tool_code)

        registry = PluginRegistry()

        # Load only agent plugins
        count = registry.load_from_directory(temp_plugin_dir, PluginType.AGENT)
        assert count == 1

        names = registry.get_plugin_names()
        assert "agent-plugin" in names
        assert "tool-plugin" not in names
