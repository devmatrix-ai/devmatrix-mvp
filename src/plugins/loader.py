"""
Plugin Loader

Handles plugin discovery, loading, and validation from filesystem.
"""

import importlib.util
import inspect
import sys
from pathlib import Path
from typing import Dict, List, Optional, Type

from .base import BasePlugin, PluginMetadata, PluginType


class PluginLoadError(Exception):
    """Raised when plugin loading fails."""

    pass


class PluginLoader:
    """
    Plugin loader with discovery and validation.

    Scans directories for plugin modules, validates them, and loads
    plugin classes dynamically.
    """

    def __init__(self, plugin_dirs: Optional[List[Path]] = None):
        """
        Initialize plugin loader.

        Args:
            plugin_dirs: List of directories to scan for plugins
        """
        self.plugin_dirs = plugin_dirs or []
        self._loaded_modules: Dict[str, any] = {}

    def discover_plugins(
        self, plugin_type: Optional[PluginType] = None
    ) -> List[Type[BasePlugin]]:
        """
        Discover all plugins in configured directories.

        Args:
            plugin_type: Filter by specific plugin type (optional)

        Returns:
            List of discovered plugin classes
        """
        discovered = []

        for plugin_dir in self.plugin_dirs:
            if not plugin_dir.exists():
                continue

            for python_file in plugin_dir.glob("*.py"):
                if python_file.name.startswith("_"):
                    continue

                try:
                    plugin_classes = self._load_module_plugins(python_file)
                    for plugin_cls in plugin_classes:
                        # Filter by type if specified
                        if plugin_type is not None:
                            try:
                                instance = plugin_cls()
                                if instance.metadata.plugin_type != plugin_type:
                                    continue
                            except Exception:
                                continue

                        discovered.append(plugin_cls)
                except PluginLoadError:
                    continue

        return discovered

    def _load_module_plugins(self, module_path: Path) -> List[Type[BasePlugin]]:
        """
        Load all plugin classes from a module file.

        Args:
            module_path: Path to Python module file

        Returns:
            List of plugin classes found in module

        Raises:
            PluginLoadError: If module loading fails
        """
        module_name = f"devmatrix_plugin_{module_path.stem}"

        try:
            # Load module from file
            spec = importlib.util.spec_from_file_location(module_name, module_path)
            if spec is None or spec.loader is None:
                raise PluginLoadError(f"Cannot load module spec: {module_path}")

            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            self._loaded_modules[module_name] = module

            # Find all BasePlugin subclasses
            plugin_classes = []
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if (
                    issubclass(obj, BasePlugin)
                    and obj is not BasePlugin
                    and obj.__module__ == module_name
                ):
                    plugin_classes.append(obj)

            return plugin_classes

        except Exception as e:
            raise PluginLoadError(f"Failed to load module {module_path}: {e}")

    def load_plugin(
        self, plugin_class: Type[BasePlugin], config: Optional[Dict] = None
    ) -> BasePlugin:
        """
        Instantiate and initialize a plugin.

        Args:
            plugin_class: Plugin class to instantiate
            config: Optional configuration dictionary

        Returns:
            Initialized plugin instance

        Raises:
            PluginLoadError: If plugin loading or validation fails
        """
        try:
            # Instantiate plugin
            plugin = plugin_class(config)

            # Validate plugin
            if not plugin.validate():
                raise PluginLoadError(
                    f"Plugin validation failed: {plugin.metadata.name}"
                )

            # Initialize plugin
            plugin.enable()

            return plugin

        except Exception as e:
            raise PluginLoadError(f"Failed to load plugin {plugin_class.__name__}: {e}")

    def unload_all(self) -> None:
        """Unload all loaded plugin modules."""
        for module_name in list(self._loaded_modules.keys()):
            if module_name in sys.modules:
                del sys.modules[module_name]
            del self._loaded_modules[module_name]

    def get_loaded_modules(self) -> List[str]:
        """Get list of loaded plugin module names."""
        return list(self._loaded_modules.keys())
