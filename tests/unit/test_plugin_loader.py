"""
Tests for Plugin Loader

Tests plugin discovery and loading from filesystem.
"""

import tempfile
from pathlib import Path

import pytest

from src.plugins.base import BasePlugin, PluginMetadata, PluginType
from src.plugins.loader import PluginLoadError, PluginLoader


class TestPluginLoader:
    """Test PluginLoader functionality."""

    def test_loader_creation(self):
        """Test creating a plugin loader."""
        loader = PluginLoader()
        assert loader.plugin_dirs == []

    def test_loader_with_directories(self):
        """Test loader with configured directories."""
        dirs = [Path("/path/1"), Path("/path/2")]
        loader = PluginLoader(dirs)
        assert len(loader.plugin_dirs) == 2

    @pytest.fixture
    def temp_plugin_dir(self):
        """Create temporary directory for test plugins."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def sample_plugin_file(self, temp_plugin_dir):
        """Create a sample plugin file."""
        plugin_code = '''
from src.plugins.base import BasePlugin, PluginMetadata, PluginType

class TestPlugin(BasePlugin):
    @property
    def metadata(self):
        return PluginMetadata(
            name="test-plugin",
            version="1.0.0",
            author="Test",
            description="Test plugin",
            plugin_type=PluginType.AGENT,
            dependencies=[],
        )

    def initialize(self):
        pass

    def validate(self):
        return True
'''
        plugin_file = temp_plugin_dir / "test_plugin.py"
        plugin_file.write_text(plugin_code)
        return plugin_file

    def test_discover_plugins_empty_directory(self, temp_plugin_dir):
        """Test discovering plugins in empty directory."""
        loader = PluginLoader([temp_plugin_dir])
        plugins = loader.discover_plugins()
        assert len(plugins) == 0

    def test_discover_plugins(self, temp_plugin_dir, sample_plugin_file):
        """Test discovering plugins from directory."""
        loader = PluginLoader([temp_plugin_dir])
        plugins = loader.discover_plugins()

        assert len(plugins) == 1
        assert issubclass(plugins[0], BasePlugin)

    def test_discover_plugins_by_type(self, temp_plugin_dir):
        """Test discovering plugins filtered by type."""
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
        (temp_plugin_dir / "agent_plugin.py").write_text(agent_code)

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
        (temp_plugin_dir / "tool_plugin.py").write_text(tool_code)

        loader = PluginLoader([temp_plugin_dir])

        # Discover all plugins
        all_plugins = loader.discover_plugins()
        assert len(all_plugins) == 2

        # Discover only agent plugins
        agent_plugins = loader.discover_plugins(PluginType.AGENT)
        assert len(agent_plugins) == 1

        # Discover only tool plugins
        tool_plugins = loader.discover_plugins(PluginType.TOOL)
        assert len(tool_plugins) == 1

    def test_discover_plugins_skips_private(self, temp_plugin_dir):
        """Test that loader skips files starting with underscore."""
        private_code = '''
from src.plugins.base import BasePlugin, PluginMetadata, PluginType

class PrivatePlugin(BasePlugin):
    @property
    def metadata(self):
        return PluginMetadata(
            name="private-plugin",
            version="1.0.0",
            author="Test",
            description="Private plugin",
            plugin_type=PluginType.AGENT,
            dependencies=[],
        )

    def initialize(self):
        pass

    def validate(self):
        return True
'''
        (temp_plugin_dir / "_private_plugin.py").write_text(private_code)

        loader = PluginLoader([temp_plugin_dir])
        plugins = loader.discover_plugins()
        assert len(plugins) == 0

    def test_load_plugin(self, temp_plugin_dir, sample_plugin_file):
        """Test loading a plugin instance."""
        loader = PluginLoader([temp_plugin_dir])
        plugin_classes = loader.discover_plugins()

        assert len(plugin_classes) == 1

        plugin = loader.load_plugin(plugin_classes[0])

        assert plugin is not None
        assert plugin.is_enabled
        assert plugin.is_initialized

    def test_load_plugin_with_config(self, temp_plugin_dir, sample_plugin_file):
        """Test loading plugin with configuration."""
        loader = PluginLoader([temp_plugin_dir])
        plugin_classes = loader.discover_plugins()

        config = {"test_key": "test_value"}
        plugin = loader.load_plugin(plugin_classes[0], config)

        assert plugin.config == config

    def test_load_invalid_plugin(self, temp_plugin_dir):
        """Test loading plugin that fails validation."""
        invalid_code = '''
from src.plugins.base import BasePlugin, PluginMetadata, PluginType

class InvalidPlugin(BasePlugin):
    @property
    def metadata(self):
        return PluginMetadata(
            name="invalid-plugin",
            version="1.0.0",
            author="Test",
            description="Invalid plugin",
            plugin_type=PluginType.AGENT,
            dependencies=[],
        )

    def initialize(self):
        pass

    def validate(self):
        return False  # Always fails validation
'''
        (temp_plugin_dir / "invalid_plugin.py").write_text(invalid_code)

        loader = PluginLoader([temp_plugin_dir])
        plugin_classes = loader.discover_plugins()

        with pytest.raises(PluginLoadError, match="validation failed"):
            loader.load_plugin(plugin_classes[0])

    def test_unload_all(self, temp_plugin_dir, sample_plugin_file):
        """Test unloading all plugin modules."""
        loader = PluginLoader([temp_plugin_dir])
        loader.discover_plugins()

        assert len(loader.get_loaded_modules()) > 0

        loader.unload_all()
        assert len(loader.get_loaded_modules()) == 0

    def test_get_loaded_modules(self, temp_plugin_dir, sample_plugin_file):
        """Test getting list of loaded modules."""
        loader = PluginLoader([temp_plugin_dir])
        loader.discover_plugins()

        modules = loader.get_loaded_modules()
        assert len(modules) > 0
        assert all("devmatrix_plugin_" in module for module in modules)

    def test_load_malformed_plugin(self, temp_plugin_dir):
        """Test loading plugin with syntax errors."""
        malformed_code = '''
This is not valid Python code!
'''
        (temp_plugin_dir / "malformed.py").write_text(malformed_code)

        loader = PluginLoader([temp_plugin_dir])

        # Should not raise, just skip malformed files
        plugins = loader.discover_plugins()
        assert len(plugins) == 0

    def test_nonexistent_directory(self):
        """Test discovering plugins in non-existent directory."""
        loader = PluginLoader([Path("/nonexistent/path")])
        plugins = loader.discover_plugins()
        assert len(plugins) == 0
