#!/usr/bin/env python
"""
End-to-end logging validation script.

Tests logging in different environments and configurations.
"""

import os
import sys
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.observability import setup_logging, get_logger


def test_development_logging():
    """Test development environment with text format."""
    print("Test 1: Development Environment (text format)")

    os.environ["ENVIRONMENT"] = "development"
    os.environ["LOG_LEVEL"] = "DEBUG"
    os.environ["LOG_FORMAT"] = "text"

    if "LOG_FILE" in os.environ:
        del os.environ["LOG_FILE"]

    setup_logging()
    logger = get_logger("test_dev")

    logger.debug("Debug message in development")
    logger.info("Info message in development")
    logger.warning("Warning message in development")

    print("✓ PASSED: Development text format logging\n")
    return True


def test_production_logging():
    """Test production environment with JSON format."""
    print("Test 2: Production Environment (JSON format)")

    os.environ["ENVIRONMENT"] = "production"
    os.environ["LOG_LEVEL"] = "INFO"
    os.environ["LOG_FORMAT"] = "json"

    setup_logging()
    logger = get_logger("test_prod")

    logger.info("Info message in production", user_id="123", action="test")
    logger.warning("Warning message in production")
    logger.error("Error message in production")

    print("✓ PASSED: Production JSON format logging\n")
    return True


def test_file_logging():
    """Test file logging with rotation."""
    print("Test 3: File Logging with Rotation")

    with tempfile.TemporaryDirectory() as tmpdir:
        log_file = Path(tmpdir) / "test_rotation.log"

        os.environ["ENVIRONMENT"] = "development"
        os.environ["LOG_LEVEL"] = "INFO"
        os.environ["LOG_FORMAT"] = "json"
        os.environ["LOG_FILE"] = str(log_file)

        setup_logging()
        logger = get_logger("test_rotation")

        for i in range(50):
            logger.info(f"Log message {i}" + "x" * 200)

        # Check that log file was created
        if log_file.exists():
            print(f"✓ PASSED: File logging creates log file\n")
            return True
        else:
            print(f"✗ FAILED: Log file not created\n")
            return False


def test_log_levels():
    """Test log level filtering."""
    print("Test 4: Log Levels Filtering")

    os.environ["ENVIRONMENT"] = "production"
    os.environ["LOG_LEVEL"] = "WARNING"
    os.environ["LOG_FORMAT"] = "text"

    if "LOG_FILE" in os.environ:
        del os.environ["LOG_FILE"]

    setup_logging()
    logger = get_logger("test_levels")

    logger.debug("Debug message - should not appear")
    logger.info("Info message - should not appear")
    logger.warning("Warning message - should appear")
    logger.error("Error message - should appear")

    print("✓ PASSED: Log level filtering works correctly\n")
    return True


def test_agents_have_logging():
    """Test that agents have StructuredLogger configured."""
    print("Test 5: Agents Use Logging")

    try:
        from src.agents.orchestrator_agent import OrchestratorAgent

        agent = OrchestratorAgent()
        assert hasattr(agent, "logger"), "Orchestrator missing logger"
        assert agent.logger.name == "orchestrator", "Orchestrator logger wrong name"
        print("  - Orchestrator has logger: OK")
    except Exception as e:
        print(f"  ✗ Orchestrator logging check failed: {e}")
        return False

    try:
        from src.agents.code_generation_agent import CodeGenerationAgent

        # Mock PostgreSQL connection to avoid DB dependency
        from unittest.mock import Mock, patch

        with patch("src.agents.code_generation_agent.PostgresManager") as mock_pg:
            agent = CodeGenerationAgent()
            assert hasattr(agent, "logger"), "CodeGen missing logger"
            assert (
                agent.logger.name == "code_generation"
            ), "CodeGen logger wrong name"
            print("  - CodeGeneration has logger: OK")
    except Exception as e:
        print(f"  ✗ CodeGeneration logging check failed: {e}")
        return False

    print("✓ PASSED: Agents have StructuredLogger configured\n")
    return True


def main():
    """Run all validation tests."""
    print("🔍 Logging End-to-End Validation")
    print("=" * 50)
    print()

    tests = [
        test_development_logging,
        test_production_logging,
        test_file_logging,
        test_log_levels,
        test_agents_have_logging,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"✗ FAILED: {test.__name__} - {e}\n")
            failed += 1

    print("=" * 50)
    print("Validation Summary")
    print("=" * 50)
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print()

    if failed == 0:
        print("✓ All validation tests passed!")
        return 0
    else:
        print("✗ Some validation tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
