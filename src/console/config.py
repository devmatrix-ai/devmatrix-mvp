"""Configuration management for DevMatrix Console Tool."""

import os
import yaml
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from src.observability import get_logger

logger = get_logger(__name__)


@dataclass
class Config:
    """Console configuration with defaults."""

    # UI Settings
    theme: str = "auto"  # auto, dark, light, high-contrast
    verbosity: str = "info"  # debug, info, warn, error
    show_tips: bool = True
    auto_save_interval: int = 30  # seconds

    # Terminal Settings
    terminal_width: Optional[int] = None
    enable_animations: bool = True
    color_enabled: bool = True

    # Backend Settings
    api_base_url: str = "http://localhost:8000"
    websocket_url: str = "ws://localhost:8000/ws"
    default_model: str = "claude-opus-4"
    timeout: int = 30

    # Session Settings
    session_retention_days: int = 30
    session_auto_save: bool = True
    session_auto_load: bool = True

    # Feature Flags
    enable_token_tracking: bool = False
    enable_cost_tracking: bool = False
    token_budget: Optional[float] = None
    cost_limit: Optional[float] = None

    # Advanced
    debug_mode: bool = False
    log_file: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return {
            k: v for k, v in self.__dict__.items() if not k.startswith("_")
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Config":
        """Create config from dictionary."""
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered)


def get_config_paths() -> tuple[Path, Optional[Path]]:
    """Get global and project config paths."""
    global_config = Path.home() / ".devmatrix" / "config.yaml"
    project_config = Path.cwd() / ".devmatrix.yaml"

    return global_config, project_config if project_config.exists() else None


def load_config() -> Config:
    """Load configuration from global and project files.

    Precedence: project config > global config > defaults
    """
    config = Config()

    global_path, project_path = get_config_paths()

    # Load global config if exists
    if global_path.exists():
        try:
            with open(global_path) as f:
                global_data = yaml.safe_load(f) or {}
                logger.debug(f"Loaded global config from {global_path}")
                config = Config.from_dict({**config.to_dict(), **global_data})
        except Exception as e:
            logger.warning(f"Failed to load global config: {e}")

    # Load project config if exists (overrides global)
    if project_path:
        try:
            with open(project_path) as f:
                project_data = yaml.safe_load(f) or {}
                logger.debug(f"Loaded project config from {project_path}")
                config = Config.from_dict({**config.to_dict(), **project_data})
        except Exception as e:
            logger.warning(f"Failed to load project config: {e}")

    # Override with environment variables
    if os.getenv("DEVMATRIX_THEME"):
        config.theme = os.getenv("DEVMATRIX_THEME", "auto")
    if os.getenv("DEVMATRIX_VERBOSITY"):
        config.verbosity = os.getenv("DEVMATRIX_VERBOSITY", "info")
    if os.getenv("DEVMATRIX_API_URL"):
        config.api_base_url = os.getenv("DEVMATRIX_API_URL")
    if os.getenv("DEVMATRIX_DEBUG"):
        config.debug_mode = os.getenv("DEVMATRIX_DEBUG", "").lower() == "true"

    logger.info(f"Configuration loaded: theme={config.theme}, verbosity={config.verbosity}")
    return config


def save_config(config: Config, target: str = "global") -> None:
    """Save configuration to file.

    Args:
        config: Configuration to save
        target: "global" or "project"
    """
    if target == "global":
        config_path = Path.home() / ".devmatrix" / "config.yaml"
        config_path.parent.mkdir(parents=True, exist_ok=True)
    elif target == "project":
        config_path = Path.cwd() / ".devmatrix.yaml"
    else:
        raise ValueError(f"Invalid target: {target}")

    try:
        with open(config_path, "w") as f:
            yaml.dump(config.to_dict(), f, default_flow_style=False)
        logger.info(f"Configuration saved to {config_path}")
    except Exception as e:
        logger.error(f"Failed to save config: {e}")
        raise
