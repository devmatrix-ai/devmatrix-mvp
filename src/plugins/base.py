"""
Base Plugin Classes and Interfaces

Defines the core plugin architecture with lifecycle hooks and metadata.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional


class PluginType(str, Enum):
    """Type of plugin."""

    AGENT = "agent"
    TOOL = "tool"
    WORKFLOW = "workflow"
    MIDDLEWARE = "middleware"


@dataclass
class PluginMetadata:
    """Plugin metadata and configuration."""

    name: str
    version: str
    author: str
    description: str
    plugin_type: PluginType
    dependencies: List[str]
    config_schema: Optional[Dict[str, Any]] = None
    tags: List[str] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []


class BasePlugin(ABC):
    """
    Base class for all plugins.

    Provides lifecycle hooks and standard interface for plugin management.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize plugin with optional configuration.

        Args:
            config: Plugin-specific configuration dictionary
        """
        self.config = config or {}
        self._initialized = False
        self._enabled = False

    @property
    @abstractmethod
    def metadata(self) -> PluginMetadata:
        """
        Return plugin metadata.

        Must be implemented by subclasses to provide plugin information.
        """
        pass

    @abstractmethod
    def initialize(self) -> None:
        """
        Initialize plugin resources.

        Called once when plugin is loaded. Use for expensive setup like
        loading models, establishing connections, etc.

        Raises:
            PluginInitializationError: If initialization fails
        """
        pass

    @abstractmethod
    def validate(self) -> bool:
        """
        Validate plugin configuration and dependencies.

        Returns:
            True if plugin is valid and ready to use, False otherwise
        """
        pass

    def enable(self) -> None:
        """Enable plugin for use."""
        if not self._initialized:
            self.initialize()
            self._initialized = True
        self._enabled = True

    def disable(self) -> None:
        """Disable plugin temporarily."""
        self._enabled = False

    def cleanup(self) -> None:
        """
        Clean up plugin resources.

        Called when plugin is unloaded or system shuts down.
        Override to release resources like connections, file handles, etc.
        """
        self._enabled = False
        self._initialized = False

    @property
    def is_initialized(self) -> bool:
        """Check if plugin is initialized."""
        return self._initialized

    @property
    def is_enabled(self) -> bool:
        """Check if plugin is enabled."""
        return self._enabled and self._initialized

    def get_config(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value.

        Args:
            key: Configuration key
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        return self.config.get(key, default)

    def __repr__(self) -> str:
        meta = self.metadata
        return (
            f"<{self.__class__.__name__} "
            f"name={meta.name} "
            f"version={meta.version} "
            f"enabled={self.is_enabled}>"
        )


class PluginInitializationError(Exception):
    """Raised when plugin initialization fails."""

    pass


class PluginValidationError(Exception):
    """Raised when plugin validation fails."""

    pass
