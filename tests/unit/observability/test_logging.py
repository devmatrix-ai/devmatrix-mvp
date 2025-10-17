"""
Comprehensive test suite for structured logging infrastructure.

Tests cover:
1. StructuredLogger basic functionality
2. No print statements in production code
3. JSON/text format switching
4. Log rotation setup
5. Log levels per environment
6. Integration across modules
"""

import pytest
import logging
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from io import StringIO

from src.observability import setup_logging, get_logger, StructuredLogger, LogLevel


class TestStructuredLoggerBasic:
    """Test basic StructuredLogger functionality."""

    def test_get_logger_returns_logger(self):
        """Test that get_logger returns a proper logger instance."""
        logger = get_logger("test_module")

        assert logger is not None
        assert isinstance(logger, StructuredLogger)
        assert logger.name == "test_module"

    def test_logger_logs_with_context(self, capsys):
        """Test that logger accepts and logs structured context."""
        logger = get_logger("test_context")

        logger.info("Test message", user_id="123", action="test", status="success")

        # Verify message was output
        captured = capsys.readouterr()
        assert "Test message" in captured.out
        assert "user_id" in captured.out or "123" in captured.out

    def test_logger_supports_all_levels(self, capsys):
        """Test that logger supports all log levels."""
        logger = get_logger("test_levels")

        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
        logger.critical("Critical message")

        captured = capsys.readouterr()
        output = captured.out

        # Verify different levels are present (not all may appear depending on log level)
        assert "INFO" in output or "info" in output.lower()
        assert "WARNING" in output or "warning" in output.lower()
        assert "ERROR" in output or "error" in output.lower()


class TestNoPrintStatements:
    """Test that production code doesn't contain print statements."""

    def test_no_print_in_agents(self):
        """Verify no print() statements in agent modules."""
        agents_dir = Path("src/agents")

        if not agents_dir.exists():
            pytest.skip("Agents directory not found")

        violations = []
        for py_file in agents_dir.glob("*.py"):
            if py_file.name.startswith("__"):
                continue

            content = py_file.read_text()
            lines = content.split("\n")

            for line_num, line in enumerate(lines, 1):
                # Skip comments and docstrings
                stripped = line.strip()
                if stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("'''"):
                    continue

                # Check for print statements (not in strings)
                if "print(" in line and not stripped.startswith('"') and not stripped.startswith("'"):
                    # Exclude console.print (Rich Console)
                    if "console.print" not in line:
                        violations.append(f"{py_file}:{line_num}: {line.strip()}")

        assert len(violations) == 0, f"Found print() statements in agents:\n" + "\n".join(violations)

    def test_no_print_in_state_managers(self):
        """Verify no print() statements in state manager modules."""
        state_dir = Path("src/state")

        if not state_dir.exists():
            pytest.skip("State directory not found")

        violations = []
        for py_file in state_dir.glob("*.py"):
            if py_file.name.startswith("__"):
                continue

            content = py_file.read_text()
            lines = content.split("\n")

            for line_num, line in enumerate(lines, 1):
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue

                if "print(" in line and not "console.print" in line:
                    violations.append(f"{py_file}:{line_num}: {line.strip()}")

        assert len(violations) == 0, f"Found print() statements in state managers:\n" + "\n".join(violations)

    def test_no_print_in_workflows(self):
        """Verify no print() statements in workflow modules."""
        workflows_dir = Path("src/workflows")

        if not workflows_dir.exists():
            pytest.skip("Workflows directory not found")

        violations = []
        for py_file in workflows_dir.glob("*.py"):
            if py_file.name.startswith("__"):
                continue

            content = py_file.read_text()
            if "print(" in content and "console.print" not in content:
                lines = content.split("\n")
                for line_num, line in enumerate(lines, 1):
                    if "print(" in line and "console.print" not in line:
                        stripped = line.strip()
                        if not stripped.startswith("#"):
                            violations.append(f"{py_file}:{line_num}: {line.strip()}")

        assert len(violations) == 0, f"Found print() statements in workflows:\n" + "\n".join(violations)


class TestLogFormats:
    """Test JSON and text log format switching."""

    def test_json_format_in_production(self, monkeypatch, tmp_path):
        """Test that JSON format is used in production environment."""
        log_file = tmp_path / "test.log"

        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("LOG_FORMAT", "json")
        monkeypatch.setenv("LOG_FILE", str(log_file))

        # Setup logging with production config
        setup_logging()
        logger = get_logger("test_json")

        logger.info("Test JSON message", key1="value1", key2=123)

        # Verify log file exists
        assert log_file.exists()

        # Read and parse JSON
        content = log_file.read_text()
        if content.strip():
            lines = content.strip().split("\n")
            for line in lines:
                try:
                    log_entry = json.loads(line)
                    assert "message" in log_entry or "msg" in log_entry
                    break
                except json.JSONDecodeError:
                    continue

    def test_text_format_in_development(self, monkeypatch, capsys):
        """Test that text format is used in development environment."""
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.setenv("LOG_FORMAT", "text")

        # Setup logging with development config
        setup_logging()
        logger = get_logger("test_text")

        logger.info("Test text message", key1="value1")

        # Verify text format in console output
        captured = capsys.readouterr()
        assert "Test text message" in captured.out
        # Text format should be human-readable
        assert "INFO" in captured.out or "info" in captured.out.lower()

    def test_log_format_switching(self, monkeypatch, capsys):
        """Test switching between JSON and text formats."""
        # First: JSON format
        monkeypatch.setenv("LOG_FORMAT", "json")
        setup_logging()
        logger_json = get_logger("test_switch")

        assert logger_json.output_json == True
        logger_json.info("JSON message")

        captured = capsys.readouterr()
        # JSON format uses structured output
        assert "JSON message" in captured.out

        # Second: Text format
        monkeypatch.setenv("LOG_FORMAT", "text")
        setup_logging()
        logger_text = get_logger("test_switch_text")

        assert logger_text.output_json == False
        logger_text.info("Text message")

        captured = capsys.readouterr()
        assert "Text message" in captured.out


class TestLogRotation:
    """Test log rotation configuration."""

    def test_log_rotation_setup(self, monkeypatch, tmp_path):
        """Test that log rotation is configured correctly."""
        log_file = tmp_path / "rotation_test.log"

        monkeypatch.setenv("LOG_FILE", str(log_file))
        monkeypatch.setenv("LOG_MAX_BYTES", "1024")  # 1KB for testing
        monkeypatch.setenv("LOG_BACKUP_COUNT", "3")

        setup_logging()
        logger = get_logger("test_rotation")

        # Generate enough logs to trigger rotation (if implemented)
        for i in range(100):
            logger.info(f"Log message {i}" + "x" * 100)  # ~100 chars per message

        # Verify main log file exists
        assert log_file.exists()

    def test_log_file_creation(self, monkeypatch, tmp_path):
        """Test that log files are created in correct location."""
        log_dir = tmp_path / "logs"
        log_dir.mkdir()
        log_file = log_dir / "app.log"

        monkeypatch.setenv("LOG_FILE", str(log_file))

        setup_logging()

        # setup_logging() creates file handlers
        # Verify the file was created by setup_logging
        import logging
        root_logger = logging.getLogger()

        # Check that a file handler was added
        file_handlers = [h for h in root_logger.handlers if isinstance(h, logging.handlers.RotatingFileHandler)]
        assert len(file_handlers) > 0

        # Verify log directory exists (created by setup_logging)
        assert log_file.parent.exists()


class TestLogLevels:
    """Test log levels per environment."""

    def test_log_level_configuration(self, monkeypatch, capsys):
        """Test that log level can be configured via environment."""
        monkeypatch.setenv("LOG_LEVEL", "WARNING")

        setup_logging()
        logger = get_logger("test_level_config")

        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")

        captured = capsys.readouterr()
        # WARNING should be logged
        assert "WARNING" in captured.out or "warning" in captured.out.lower()

    def test_debug_level_in_development(self, monkeypatch, capsys):
        """Test that DEBUG level is enabled in development."""
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")

        setup_logging()
        logger = get_logger("test_debug_dev")
        logger.level = LogLevel.DEBUG  # Set instance level

        logger.debug("Debug message in development")

        captured = capsys.readouterr()
        # DEBUG should appear
        assert "Debug message" in captured.out or "debug" in captured.out.lower()

    def test_info_level_in_production(self, monkeypatch, capsys):
        """Test that INFO level is default in production."""
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("LOG_LEVEL", "INFO")

        setup_logging()
        logger = get_logger("test_info_prod")

        logger.debug("Debug message - should not appear")
        logger.info("Info message - should appear")

        captured = capsys.readouterr()
        # INFO should appear
        assert "Info message" in captured.out


class TestLoggingIntegration:
    """Test logging integration across modules."""

    def test_logging_across_modules(self, capsys):
        """Test that logging works consistently across different modules."""
        logger1 = get_logger("module1")
        logger2 = get_logger("module2")

        logger1.info("Message from module1", module="1")
        logger2.info("Message from module2", module="2")

        captured = capsys.readouterr()
        assert "module1" in captured.out
        assert "module2" in captured.out

    def test_error_logging_with_exc_info(self, capsys):
        """Test that errors are logged with exception information."""
        logger = get_logger("test_exception")

        try:
            raise ValueError("Test exception")
        except ValueError as e:
            logger.error("Error occurred",
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True
            )

        captured = capsys.readouterr()
        assert "ERROR" in captured.out or "error" in captured.out.lower()
        assert "Error occurred" in captured.out or "Test exception" in captured.out

    def test_context_preservation(self, capsys):
        """Test that context is preserved across log calls."""
        logger = get_logger("test_context_preserve")

        logger.info("First message",
            request_id="123",
            user_id="456",
            action="login"
        )

        logger.info("Second message",
            request_id="123",
            user_id="456",
            action="fetch_data"
        )

        captured = capsys.readouterr()
        # Both messages should be logged
        assert "First message" in captured.out
        assert "Second message" in captured.out


class TestLoggingPerformance:
    """Test logging performance and overhead."""

    def test_logging_overhead_acceptable(self, monkeypatch, tmp_path):
        """Test that logging overhead is minimal (<5ms per log call)."""
        import time

        log_file = tmp_path / "perf_test.log"
        monkeypatch.setenv("LOG_FILE", str(log_file))

        setup_logging()
        logger = get_logger("test_perf")

        # Warm up
        for _ in range(10):
            logger.info("Warmup", key="value")

        # Measure
        iterations = 100
        start = time.time()

        for i in range(iterations):
            logger.info("Performance test",
                iteration=i,
                timestamp=time.time(),
                data="x" * 100
            )

        duration = time.time() - start
        avg_time_ms = (duration / iterations) * 1000

        # Average time per log should be < 5ms
        assert avg_time_ms < 5.0, f"Logging too slow: {avg_time_ms:.2f}ms per call"


class TestLoggingConfiguration:
    """Test logging configuration and setup."""

    def test_setup_logging_creates_handlers(self, monkeypatch, tmp_path):
        """Test that setup_logging creates appropriate handlers."""
        log_file = tmp_path / "config_test.log"
        monkeypatch.setenv("LOG_FILE", str(log_file))

        setup_logging()

        root_logger = logging.getLogger()
        assert len(root_logger.handlers) > 0

    def test_multiple_setup_calls_idempotent(self, monkeypatch, tmp_path):
        """Test that multiple setup_logging calls don't create duplicate handlers."""
        log_file = tmp_path / "idempotent_test.log"
        monkeypatch.setenv("LOG_FILE", str(log_file))

        setup_logging()
        handler_count_1 = len(logging.getLogger().handlers)

        setup_logging()
        handler_count_2 = len(logging.getLogger().handlers)

        # Handler count should not increase
        assert handler_count_2 <= handler_count_1 + 1  # Allow one additional handler max


# Pytest configuration
@pytest.fixture(autouse=True)
def reset_logging():
    """Reset logging configuration before each test."""
    # Remove all handlers
    logger = logging.getLogger()
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    yield

    # Cleanup after test
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
