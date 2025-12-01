"""DevMatrix Console Tool - Interactive terminal UI for pipeline management."""

__version__ = "0.1.0"
__author__ = "DevMatrix Team"

# Legacy console components (may have broken deps)
try:
    from src.console.cli import main as cli_main
    from src.console.session_manager import SessionManager
    from src.console.config import load_config, Config
    LEGACY_CONSOLE_AVAILABLE = True
except ImportError:
    LEGACY_CONSOLE_AVAILABLE = False
    cli_main = None
    SessionManager = None
    load_config = None
    Config = None

# Pro Dashboard (Rich Live based)
try:
    from src.console.dashboard_manager import DashboardManager
    from src.console.dashboard_state import DashboardState, PhaseStatus
    from src.console.dashboard_renderer import DashboardRenderer
    DASHBOARD_AVAILABLE = True
except ImportError:
    DASHBOARD_AVAILABLE = False
    DashboardManager = None
    DashboardState = None
    PhaseStatus = None
    DashboardRenderer = None

__all__ = [
    "cli_main", "SessionManager", "load_config", "Config",
    "DashboardManager", "DashboardState", "PhaseStatus", "DashboardRenderer",
    "DASHBOARD_AVAILABLE", "LEGACY_CONSOLE_AVAILABLE",
]
