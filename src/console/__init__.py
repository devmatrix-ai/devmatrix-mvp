"""DevMatrix Console Tool - Interactive terminal UI for pipeline management."""

__version__ = "0.1.0"
__author__ = "DevMatrix Team"

from src.console.cli import main as cli_main
from src.console.session_manager import SessionManager
from src.console.config import load_config, Config

__all__ = ["cli_main", "SessionManager", "load_config", "Config"]
