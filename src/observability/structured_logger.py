"""
Structured Logging System

Provides JSON-formatted structured logging with context propagation
for better observability and log aggregation.
"""

import json
import logging
import sys
from typing import Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field, asdict
from contextvars import ContextVar
from enum import Enum
from uuid import UUID


# Context variable for request/workflow tracking
_log_context: ContextVar[Optional["LogContext"]] = ContextVar("log_context", default=None)


def json_serializable(obj):
    """Helper to serialize non-JSON types like UUID."""
    if isinstance(obj, UUID):
        return str(obj)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


class LogLevel(Enum):
    """Log level enumeration."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class LogContext:
    """
    Log context for request/workflow tracking.

    Provides correlation IDs and metadata that propagate
    through all log messages in a request/workflow.
    """

    request_id: Optional[str] = None
    """Unique request identifier"""

    workflow_id: Optional[str] = None
    """Workflow execution identifier"""

    user_id: Optional[str] = None
    """User identifier"""

    agent_name: Optional[str] = None
    """Current agent name"""

    task_id: Optional[str] = None
    """Current task identifier"""

    metadata: Dict[str, Any] = field(default_factory=dict)
    """Additional context metadata"""

    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary."""
        data = asdict(self)
        # Remove None values
        return {k: v for k, v in data.items() if v is not None}

    @classmethod
    def get_current(cls) -> Optional["LogContext"]:
        """Get current context from context variable."""
        return _log_context.get()

    @classmethod
    def set_current(cls, context: Optional["LogContext"]):
        """Set current context in context variable."""
        _log_context.set(context)


class StructuredLogger:
    """
    Structured logging with JSON output and context propagation.

    Provides structured logging that outputs JSON for easy parsing
    by log aggregation systems (ELK, Splunk, CloudWatch, etc.).

    Example:
        >>> logger = StructuredLogger("my_service")
        >>> with logger.context(request_id="req-123"):
        ...     logger.info("Processing request", user_id="user-456")
    """

    def __init__(
        self,
        name: str,
        level: LogLevel = LogLevel.INFO,
        output_json: bool = True,
    ):
        """
        Initialize structured logger.

        Args:
            name: Logger name (typically module/component name)
            level: Minimum log level
            output_json: Output as JSON (True) or text (False)
        """
        self.name = name
        self.level = level
        self.output_json = output_json

        # Setup Python logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level.value))

        # Remove existing handlers to avoid duplicates
        self.logger.handlers.clear()

        # Add handler with auto-flush for real-time logging
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(message)s"))

        # Force unbuffered output for real-time logs
        class FlushingStreamHandler(logging.StreamHandler):
            def emit(self, record):
                super().emit(record)
                self.flush()

        handler = FlushingStreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(message)s"))
        self.logger.addHandler(handler)

        # Prevent propagation to root logger
        self.logger.propagate = False

    def _format_message(
        self,
        level: LogLevel,
        message: str,
        **kwargs
    ) -> str:
        """
        Format log message as JSON or text.

        Args:
            level: Log level
            message: Log message
            **kwargs: Additional fields

        Returns:
            Formatted log message
        """
        if self.output_json:
            log_entry = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "level": level.value,
                "logger": self.name,
                "message": message,
            }

            # Add context if available
            context = LogContext.get_current()
            if context:
                log_entry["context"] = context.to_dict()

            # Add additional fields
            if kwargs:
                log_entry.update(kwargs)

            return json.dumps(log_entry, default=json_serializable)
        else:
            # Text format
            parts = [
                f"[{level.value}]",
                f"[{self.name}]",
                message,
            ]

            if kwargs:
                parts.append(str(kwargs))

            return " ".join(parts)

    def debug(self, message: str, **kwargs):
        """Log debug message."""
        if self._should_log(LogLevel.DEBUG):
            formatted = self._format_message(LogLevel.DEBUG, message, **kwargs)
            self.logger.debug(formatted)

    def info(self, message: str, **kwargs):
        """Log info message."""
        if self._should_log(LogLevel.INFO):
            formatted = self._format_message(LogLevel.INFO, message, **kwargs)
            self.logger.info(formatted)

    def warning(self, message: str, **kwargs):
        """Log warning message."""
        if self._should_log(LogLevel.WARNING):
            formatted = self._format_message(LogLevel.WARNING, message, **kwargs)
            self.logger.warning(formatted)

    def error(self, message: str, **kwargs):
        """Log error message."""
        if self._should_log(LogLevel.ERROR):
            formatted = self._format_message(LogLevel.ERROR, message, **kwargs)
            self.logger.error(formatted)

    def critical(self, message: str, **kwargs):
        """Log critical message."""
        if self._should_log(LogLevel.CRITICAL):
            formatted = self._format_message(LogLevel.CRITICAL, message, **kwargs)
            self.logger.critical(formatted)

    def exception(self, message: str, exc_info: bool = True, **kwargs):
        """
        Log exception with traceback.

        Args:
            message: Log message
            exc_info: Include exception info
            **kwargs: Additional fields
        """
        if self._should_log(LogLevel.ERROR):
            formatted = self._format_message(LogLevel.ERROR, message, **kwargs)
            self.logger.error(formatted, exc_info=exc_info)

    def _should_log(self, level: LogLevel) -> bool:
        """Check if message should be logged based on level."""
        level_order = {
            LogLevel.DEBUG: 0,
            LogLevel.INFO: 1,
            LogLevel.WARNING: 2,
            LogLevel.ERROR: 3,
            LogLevel.CRITICAL: 4,
        }
        return level_order[level] >= level_order[self.level]

    def context(
        self,
        request_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        user_id: Optional[str] = None,
        agent_name: Optional[str] = None,
        task_id: Optional[str] = None,
        **metadata
    ):
        """
        Create context manager for log context.

        Args:
            request_id: Request identifier
            workflow_id: Workflow identifier
            user_id: User identifier
            agent_name: Agent name
            task_id: Task identifier
            **metadata: Additional metadata

        Returns:
            Context manager

        Example:
            >>> with logger.context(request_id="req-123"):
            ...     logger.info("Processing")
        """
        return LogContextManager(
            request_id=request_id,
            workflow_id=workflow_id,
            user_id=user_id,
            agent_name=agent_name,
            task_id=task_id,
            metadata=metadata,
        )


class LogContextManager:
    """Context manager for log context."""

    def __init__(self, **kwargs):
        """Initialize context manager."""
        self.context = LogContext(**kwargs)
        self.previous_context = None

    def __enter__(self):
        """Enter context."""
        self.previous_context = LogContext.get_current()
        LogContext.set_current(self.context)
        return self.context

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context."""
        LogContext.set_current(self.previous_context)
        return False
