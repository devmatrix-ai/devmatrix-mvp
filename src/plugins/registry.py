"""
Plugin Registry

Central registry for managing loaded plugins and their lifecycle.
"""

from pathlib import Path
from typing import Dict, List, Optional, Type

from .base import BasePlugin, PluginType
from .loader import PluginLoadError, PluginLoader


class PluginRegistry:
    """
    Central registry for plugin management.

    Maintains loaded plugins, handles lifecycle, and provides
    lookup functionality.
    """

    def __init__(self):
        """Initialize empty plugin registry."""
        self._plugins: Dict[str, BasePlugin] = {}
        self._plugin_classes: Dict[str, Type[BasePlugin]] = {}
        self.loader = PluginLoader()

    def register(
        self, plugin: BasePlugin, name: Optional[str] = None
    ) -> None:
        """
        Register a plugin instance.

        Args:
            plugin: Plugin instance to register
            name: Optional custom name (defaults to plugin.metadata.name)

        Raises:
            ValueError: If plugin with same name already registered
        """
        plugin_name = name or plugin.metadata.name

        if plugin_name in self._plugins:
            raise ValueError(f"Plugin already registered: {plugin_name}")

        self._plugins[plugin_name] = plugin

    def register_class(
        self, plugin_class: Type[BasePlugin], name: Optional[str] = None
    ) -> None:
        """
        Register a plugin class for lazy loading.

        Args:
            plugin_class: Plugin class to register
            name: Optional custom name

        Raises:
            ValueError: If plugin class with same name already registered
        """
        # Instantiate temporarily to get metadata
        temp_instance = plugin_class()
        plugin_name = name or temp_instance.metadata.name

        if plugin_name in self._plugin_classes:
            raise ValueError(f"Plugin class already registered: {plugin_name}")

        self._plugin_classes[plugin_name] = plugin_class

    def unregister(self, name: str) -> None:
        """
        Unregister and cleanup a plugin.

        Args:
            name: Name of plugin to unregister
        """
        if name in self._plugins:
            plugin = self._plugins[name]
            plugin.cleanup()
            del self._plugins[name]

        if name in self._plugin_classes:
            del self._plugin_classes[name]

    def get(self, name: str) -> Optional[BasePlugin]:
        """
        Get plugin by name.

        If plugin class is registered but not instantiated, will
        instantiate it on first access (lazy loading).

        Args:
            name: Plugin name

        Returns:
            Plugin instance or None if not found
        """
        # Check if already instantiated
        if name in self._plugins:
            return self._plugins[name]

        # Try to instantiate from registered class
        if name in self._plugin_classes:
            try:
                plugin = self.loader.load_plugin(self._plugin_classes[name])
                self._plugins[name] = plugin
                # Remove from lazy-loaded classes after successful instantiation
                del self._plugin_classes[name]
                return plugin
            except PluginLoadError:
                return None

        return None

    def get_all(
        self, plugin_type: Optional[PluginType] = None, enabled_only: bool = False
    ) -> List[BasePlugin]:
        """
        Get all registered plugins.

        Args:
            plugin_type: Filter by plugin type (optional)
            enabled_only: Only return enabled plugins

        Returns:
            List of plugin instances
        """
        plugins = list(self._plugins.values())

        # Filter by type
        if plugin_type is not None:
            plugins = [p for p in plugins if p.metadata.plugin_type == plugin_type]

        # Filter by enabled status
        if enabled_only:
            plugins = [p for p in plugins if p.is_enabled]

        return plugins

    def load_from_directory(
        self, directory: Path, plugin_type: Optional[PluginType] = None
    ) -> int:
        """
        Discover and load plugins from a directory.

        Args:
            directory: Directory to scan for plugins
            plugin_type: Filter by plugin type (optional)

        Returns:
            Number of plugins loaded
        """
        self.loader.plugin_dirs = [directory]
        discovered = self.loader.discover_plugins(plugin_type)

        loaded_count = 0
        for plugin_class in discovered:
            try:
                # Register class for lazy loading
                self.register_class(plugin_class)
                loaded_count += 1
            except ValueError:
                # Already registered, skip
                continue

        return loaded_count

    def enable_plugin(self, name: str) -> bool:
        """
        Enable a plugin.

        Args:
            name: Plugin name

        Returns:
            True if successful, False otherwise
        """
        plugin = self.get(name)
        if plugin:
            plugin.enable()
            return True
        return False

    def disable_plugin(self, name: str) -> bool:
        """
        Disable a plugin.

        Args:
            name: Plugin name

        Returns:
            True if successful, False otherwise
        """
        plugin = self.get(name)
        if plugin:
            plugin.disable()
            return True
        return False

    def cleanup_all(self) -> None:
        """Cleanup all registered plugins."""
        for plugin in self._plugins.values():
            plugin.cleanup()

        self._plugins.clear()
        self._plugin_classes.clear()

    def get_plugin_names(self) -> List[str]:
        """Get list of all registered plugin names."""
        all_names = set(self._plugins.keys()) | set(self._plugin_classes.keys())
        return sorted(all_names)

    def get_stats(self) -> Dict[str, int]:
        """
        Get registry statistics.

        Returns:
            Dictionary with counts of plugins by type and status
        """
        all_plugins = list(self._plugins.values())

        return {
            "total": len(all_plugins) + len(self._plugin_classes),
            "instantiated": len(all_plugins),
            "enabled": len([p for p in all_plugins if p.is_enabled]),
            "disabled": len([p for p in all_plugins if not p.is_enabled]),
            "lazy_loaded": len(self._plugin_classes),
        }
