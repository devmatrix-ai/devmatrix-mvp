"""
Observability Module

Provides structured logging, metrics collection, and health monitoring
for production-ready system observability.
"""

import os
import logging
import logging.handlers
from pathlib import Path
from typing import Optional

from .structured_logger import StructuredLogger, LogContext, LogLevel
from .metrics_collector import MetricsCollector, MetricType, Metric
from .health_check import HealthCheck, HealthStatus, ComponentHealth
from .middleware import MetricsMiddleware

__all__ = [
    "StructuredLogger",
    "LogContext",
    "LogLevel",
    "MetricsCollector",
    "MetricType",
    "Metric",
    "HealthCheck",
    "HealthStatus",
    "ComponentHealth",
    "MetricsMiddleware",
    "setup_logging",
    "get_logger",
]


def setup_logging(
    environment: str = None,
    log_level: str = None,
    log_file: str = None,
    json_format: bool = None,
):
    """
    Setup global logging configuration.

    Args:
        environment: "development" | "production" | "test" (from env or param)
        log_level: "DEBUG" | "INFO" | "WARNING" | "ERROR" (from env or param)
        log_file: Optional path to log file (from env or param)
        json_format: Use JSON format for logs (from env or param)

    Environment Variables:
        ENVIRONMENT: development, production, test
        LOG_LEVEL: DEBUG, INFO, WARNING, ERROR
        LOG_FILE: /path/to/logfile.log
        LOG_FORMAT: json, text
    """
    # Get configuration from environment if not provided
    if environment is None:
        environment = os.getenv("ENVIRONMENT", "development")

    if log_level is None:
        log_level = os.getenv("LOG_LEVEL", "INFO")

    if log_file is None:
        log_file = os.getenv("LOG_FILE")

    if json_format is None:
        log_format = os.getenv("LOG_FORMAT", "json" if environment == "production" else "text")
        json_format = log_format == "json"

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Console handler (stdout)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, log_level.upper()))

    if json_format:
        console_formatter = logging.Formatter('%(message)s')  # JSON messages format themselves
    else:
        console_formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # File handler with rotation (if specified)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(getattr(logging, log_level.upper()))

        # Always use JSON for file logs (easier to parse)
        file_formatter = logging.Formatter('%(message)s')
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)

    # Log configuration
    logger = StructuredLogger("setup", output_json=json_format)
    logger.info(
        "Logging configured",
        environment=environment,
        log_level=log_level,
        log_file=log_file,
        json_format=json_format
    )


def get_logger(
    name: str,
    json_format: bool = None
) -> StructuredLogger:
    """
    Get a structured logger instance.

    Args:
        name: Logger name (typically module name)
        json_format: Use JSON format (default: from environment)

    Returns:
        StructuredLogger instance

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Operation completed", user_id="123")
    """
    if json_format is None:
        environment = os.getenv("ENVIRONMENT", "development")
        log_format = os.getenv("LOG_FORMAT", "json" if environment == "production" else "text")
        json_format = log_format == "json"

    log_level_str = os.getenv("LOG_LEVEL", "INFO")
    log_level = getattr(LogLevel, log_level_str.upper(), LogLevel.INFO)

    return StructuredLogger(
        name=name,
        level=log_level,
        output_json=json_format
    )
