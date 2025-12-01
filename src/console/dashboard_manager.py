"""
Dashboard Manager - Public API for DevMatrix Pro Dashboard.

Wraps Rich Live and provides simple API for pipeline phases.
Reference: DOCS/mvp/exit/anti/PRO_DASHBOARD_IMPLEMENTATION_PLAN.md Task 3
"""
import threading
import time
from datetime import datetime
from typing import Optional

from rich.console import Console
from rich.live import Live

from src.console.dashboard_state import (
    DashboardState, PhaseState, PhaseStatus, LogLevel
)
from src.console.dashboard_renderer import DashboardRenderer


class DashboardManager:
    """
    Public API for the DevMatrix Pro Dashboard.
    
    Usage:
        with DashboardManager() as dash:
            dash.start_phase("Spec Ingestion", total_steps=4)
            dash.log("Loading spec...")
            dash.update_progress(1, "Parsing...")
            dash.complete_phase()
    """
    
    def __init__(
        self,
        pipeline_name: str = "DevMatrix Pipeline",
        total_phases: int = 13,
        refresh_rate: float = 4.0,
        enabled: bool = True,
    ):
        self.enabled = enabled
        self.state = DashboardState(
            pipeline_name=pipeline_name,
            total_phases=total_phases,
        )
        self.renderer = DashboardRenderer(self.state)
        self.console = Console()
        self.live: Optional[Live] = None
        self._refresh_rate = refresh_rate
        self._spinner_thread: Optional[threading.Thread] = None
        self._stop_spinner = threading.Event()
        
    def __enter__(self) -> "DashboardManager":
        """Start the dashboard."""
        if not self.enabled:
            return self
            
        self.live = Live(
            self.renderer.render(),
            console=self.console,
            refresh_per_second=self._refresh_rate,
            redirect_stdout=True,
            redirect_stderr=True,
        )
        self.live.__enter__()
        
        # Start spinner animation thread
        self._stop_spinner.clear()
        self._spinner_thread = threading.Thread(target=self._animate_spinner, daemon=True)
        self._spinner_thread.start()
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop the dashboard."""
        self._stop_spinner.set()
        if self._spinner_thread:
            self._spinner_thread.join(timeout=1.0)
            
        if self.live:
            self.live.__exit__(exc_type, exc_val, exc_tb)
    
    def _animate_spinner(self):
        """Background thread for spinner animation."""
        while not self._stop_spinner.is_set():
            self.renderer.tick()
            if self.live:
                self.live.update(self.renderer.render())
            time.sleep(0.1)
    
    def _update(self):
        """Refresh the dashboard display."""
        if self.live and self.enabled:
            self.live.update(self.renderer.render())
    
    # === Phase Management ===
    
    def start_phase(self, name: str, total_steps: int = 1):
        """Start a new phase."""
        phase = PhaseState(
            name=name,
            status=PhaseStatus.RUNNING,
            total_steps=total_steps,
            start_time=datetime.now(),
        )
        self.state.phases.append(phase)
        self.state.current_phase_index = len(self.state.phases) - 1
        self._update()
    
    def update_progress(self, current: int, message: str = ""):
        """Update current phase progress."""
        phase = self.state.current_phase
        if phase:
            phase.current_step = current
            phase.message = message
            self._update()
    
    def complete_phase(self):
        """Mark current phase as completed."""
        phase = self.state.current_phase
        if phase:
            phase.status = PhaseStatus.COMPLETED
            phase.current_step = phase.total_steps
            phase.end_time = datetime.now()
            self._update()
    
    def fail_phase(self, error: str):
        """Mark current phase as failed."""
        phase = self.state.current_phase
        if phase:
            phase.status = PhaseStatus.FAILED
            phase.error = error
            phase.end_time = datetime.now()
            self.state.final_status = "FAILED"
            self._update()
    
    def skip_phase(self, name: str, reason: str = ""):
        """Mark a phase as skipped."""
        phase = PhaseState(
            name=name,
            status=PhaseStatus.SKIPPED,
            message=reason,
        )
        self.state.phases.append(phase)
        self._update()
    
    # === Metrics ===
    
    def update_tests(self, passed: int, total: int):
        """Update tests metric card."""
        self.state.metrics.tests_passed = passed
        self.state.metrics.tests_total = total
        self._update()
    
    def update_compliance(self, percentage: float):
        """Update compliance metric card."""
        self.state.metrics.compliance_percent = percentage
        self._update()
    
    def update_llm(self, cost: float, tokens: int):
        """Update LLM metric card."""
        self.state.metrics.llm_cost = cost
        self.state.metrics.llm_tokens = tokens
        self._update()

    def update_repair(self, iteration: int, max_iter: int = 3, status: str = "running"):
        """Update repair loop metric card."""
        self.state.metrics.repair_iteration = iteration
        self.state.metrics.repair_max = max_iter
        self.state.metrics.repair_status = status
        self._update()

    # === Logging ===

    def log(self, message: str, level: str = "info"):
        """Add a log entry (appears above dashboard)."""
        log_level = LogLevel.INFO
        if level == "success":
            log_level = LogLevel.SUCCESS
        elif level == "warning":
            log_level = LogLevel.WARNING
        elif level == "error":
            log_level = LogLevel.ERROR

        self.state.add_log(message, log_level)

        # Also print to console (appears above dashboard via Rich Live)
        if self.live and self.enabled:
            icon = {"info": " ", "success": "✓", "warning": "⚠", "error": "✗"}.get(level, " ")
            color = {"info": "white", "success": "green", "warning": "yellow", "error": "red"}.get(level, "white")
            self.live.console.print(f"[{color}]{icon}[/] {message}")

        self._update()

    def success(self, message: str):
        """Log success message."""
        self.log(message, level="success")

    def warning(self, message: str):
        """Log warning message."""
        self.log(message, level="warning")

    def error(self, message: str):
        """Log error message."""
        self.log(message, level="error")

    # === Pipeline Status ===

    def finish(self, status: str = "SUCCESS"):
        """Mark pipeline as finished."""
        self.state.final_status = status
        self._update()

