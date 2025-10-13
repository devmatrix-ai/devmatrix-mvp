"""
Tests for Plugin Base Classes

Tests BasePlugin abstract class and PluginMetadata.
"""

import pytest

from src.plugins.base import (
    BasePlugin,
    PluginInitializationError,
    PluginMetadata,
    PluginType,
    PluginValidationError,
)


class TestPluginMetadata:
    """Test PluginMetadata dataclass."""

    def test_metadata_creation(self):
        """Test creating plugin metadata."""
        metadata = PluginMetadata(
            name="test-plugin",
            version="1.0.0",
            author="Test Author",
            description="Test plugin description",
            plugin_type=PluginType.AGENT,
            dependencies=["dep1", "dep2"],
            tags=["tag1", "tag2"],
        )

        assert metadata.name == "test-plugin"
        assert metadata.version == "1.0.0"
        assert metadata.author == "Test Author"
        assert metadata.plugin_type == PluginType.AGENT
        assert len(metadata.dependencies) == 2
        assert len(metadata.tags) == 2

    def test_metadata_defaults(self):
        """Test metadata with default values."""
        metadata = PluginMetadata(
            name="test",
            version="1.0.0",
            author="Author",
            description="Description",
            plugin_type=PluginType.TOOL,
            dependencies=[],
        )

        assert metadata.tags == []
        assert metadata.config_schema is None


class TestPluginType:
    """Test PluginType enum."""

    def test_plugin_types(self):
        """Test all plugin type values."""
        assert PluginType.AGENT.value == "agent"
        assert PluginType.TOOL.value == "tool"
        assert PluginType.WORKFLOW.value == "workflow"
        assert PluginType.MIDDLEWARE.value == "middleware"


class MockPlugin(BasePlugin):
    """Mock plugin for testing."""

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="mock-plugin",
            version="1.0.0",
            author="Test",
            description="Mock plugin for testing",
            plugin_type=PluginType.AGENT,
            dependencies=[],
        )

    def initialize(self) -> None:
        pass

    def validate(self) -> bool:
        return True


class FailingPlugin(BasePlugin):
    """Plugin that fails validation."""

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="failing-plugin",
            version="1.0.0",
            author="Test",
            description="Failing plugin",
            plugin_type=PluginType.TOOL,
            dependencies=[],
        )

    def initialize(self) -> None:
        raise PluginInitializationError("Initialization failed")

    def validate(self) -> bool:
        return False


class TestBasePlugin:
    """Test BasePlugin functionality."""

    def test_plugin_creation(self):
        """Test creating a plugin instance."""
        plugin = MockPlugin()

        assert not plugin.is_initialized
        assert not plugin.is_enabled
        assert plugin.config == {}

    def test_plugin_with_config(self):
        """Test plugin with configuration."""
        config = {"key1": "value1", "key2": 42}
        plugin = MockPlugin(config)

        assert plugin.config == config
        assert plugin.get_config("key1") == "value1"
        assert plugin.get_config("key2") == 42
        assert plugin.get_config("key3", "default") == "default"

    def test_plugin_enable(self):
        """Test enabling a plugin."""
        plugin = MockPlugin()

        assert not plugin.is_enabled
        plugin.enable()
        assert plugin.is_enabled
        assert plugin.is_initialized

    def test_plugin_disable(self):
        """Test disabling a plugin."""
        plugin = MockPlugin()
        plugin.enable()

        assert plugin.is_enabled
        plugin.disable()
        assert not plugin.is_enabled
        assert plugin.is_initialized  # Still initialized

    def test_plugin_cleanup(self):
        """Test cleaning up a plugin."""
        plugin = MockPlugin()
        plugin.enable()

        plugin.cleanup()
        assert not plugin.is_enabled
        assert not plugin.is_initialized

    def test_plugin_repr(self):
        """Test plugin string representation."""
        plugin = MockPlugin()
        repr_str = repr(plugin)

        assert "MockPlugin" in repr_str
        assert "mock-plugin" in repr_str
        assert "1.0.0" in repr_str

    def test_failing_plugin_validation(self):
        """Test plugin that fails validation."""
        plugin = FailingPlugin()

        assert not plugin.validate()

    def test_failing_plugin_initialization(self):
        """Test plugin that fails initialization."""
        plugin = FailingPlugin()

        with pytest.raises(PluginInitializationError):
            plugin.enable()

        assert not plugin.is_enabled


class ConfigurablePlugin(BasePlugin):
    """Plugin with configuration validation."""

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="configurable-plugin",
            version="1.0.0",
            author="Test",
            description="Configurable plugin",
            plugin_type=PluginType.MIDDLEWARE,
            dependencies=[],
            config_schema={
                "required": ["api_key", "endpoint"],
                "optional": ["timeout"],
            },
        )

    def initialize(self) -> None:
        self.api_key = self.get_config("api_key")
        self.endpoint = self.get_config("endpoint")
        self.timeout = self.get_config("timeout", 30)

    def validate(self) -> bool:
        required = ["api_key", "endpoint"]
        return all(self.get_config(key) is not None for key in required)


class TestConfigurablePlugin:
    """Test plugin with configuration requirements."""

    def test_valid_configuration(self):
        """Test plugin with valid configuration."""
        config = {"api_key": "test-key", "endpoint": "https://api.example.com"}
        plugin = ConfigurablePlugin(config)

        assert plugin.validate()
        plugin.enable()
        assert plugin.is_enabled

    def test_invalid_configuration(self):
        """Test plugin with invalid configuration."""
        config = {"api_key": "test-key"}  # Missing endpoint
        plugin = ConfigurablePlugin(config)

        assert not plugin.validate()

    def test_configuration_with_defaults(self):
        """Test plugin using default values."""
        config = {"api_key": "test-key", "endpoint": "https://api.example.com"}
        plugin = ConfigurablePlugin(config)
        plugin.enable()

        assert plugin.timeout == 30  # Default value
