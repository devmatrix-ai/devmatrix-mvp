"""
Application Constants

Centralized configuration constants with environment variable overrides.
All magic numbers should reference these constants instead of hardcoding values.
"""

import os
from typing import Dict, Any


# ============================================================================
# LLM Configuration
# ============================================================================

# Token limits
DEFAULT_MAX_TOKENS = int(os.getenv("MAX_TOKENS", "4096"))
STREAMING_MAX_TOKENS = int(os.getenv("STREAMING_MAX_TOKENS", "8192"))
CHAT_MAX_TOKENS = int(os.getenv("CHAT_MAX_TOKENS", "400"))

# Model selection
DEFAULT_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")

# Temperature settings
DEFAULT_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.7"))


# ============================================================================
# Timeout Configuration (seconds)
# ============================================================================

# API request timeouts
DEFAULT_REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "300"))  # 5 minutes
HEALTH_CHECK_TIMEOUT = int(os.getenv("HEALTH_CHECK_TIMEOUT", "5"))
LLM_API_TIMEOUT = int(os.getenv("LLM_API_TIMEOUT", "60"))

# Task execution timeouts
TASK_TIMEOUT_SHORT = int(os.getenv("TASK_TIMEOUT_SHORT", "180"))      # 3 min
TASK_TIMEOUT_MEDIUM = int(os.getenv("TASK_TIMEOUT_MEDIUM", "300"))    # 5 min
TASK_TIMEOUT_LONG = int(os.getenv("TASK_TIMEOUT_LONG", "600"))        # 10 min
TASK_TIMEOUT_MAX = int(os.getenv("TASK_TIMEOUT_MAX", "3600"))         # 1 hour

# Test execution timeout
TEST_EXECUTION_TIMEOUT = int(os.getenv("TEST_EXECUTION_TIMEOUT", "30"))


# ============================================================================
# Cache TTL Configuration (seconds)
# ============================================================================

# Cache time-to-live values
CACHE_TTL_SHORT = int(os.getenv("CACHE_TTL_SHORT", "1800"))     # 30 minutes
CACHE_TTL_MEDIUM = int(os.getenv("CACHE_TTL_MEDIUM", "3600"))   # 1 hour
CACHE_TTL_LONG = int(os.getenv("CACHE_TTL_LONG", "7200"))       # 2 hours

# Default TTL for various cache types
DEFAULT_CACHE_TTL = CACHE_TTL_MEDIUM
LLM_CACHE_TTL = int(os.getenv("LLM_CACHE_TTL", str(CACHE_TTL_MEDIUM)))
AGENT_CACHE_TTL = int(os.getenv("AGENT_CACHE_TTL", str(CACHE_TTL_SHORT)))
ARTIFACT_TTL = int(os.getenv("ARTIFACT_TTL", str(CACHE_TTL_LONG)))
CHECKPOINT_TTL = int(os.getenv("CHECKPOINT_TTL", str(CACHE_TTL_MEDIUM)))


# ============================================================================
# Network Configuration
# ============================================================================

# Service ports
API_PORT = int(os.getenv("API_PORT", "8000"))
UI_PORT = int(os.getenv("UI_PORT", "5173"))
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

# Service hosts
API_HOST = os.getenv("API_HOST", "0.0.0.0")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")

# Network timeouts
SOCKET_CONNECT_TIMEOUT = int(os.getenv("SOCKET_CONNECT_TIMEOUT", "5"))
SOCKET_TIMEOUT = int(os.getenv("SOCKET_TIMEOUT", "5"))


# ============================================================================
# Retry Configuration
# ============================================================================

# Retry attempts
DEFAULT_MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
HEALTH_CHECK_MAX_RETRIES = int(os.getenv("HEALTH_CHECK_MAX_RETRIES", "2"))

# Retry delays (seconds)
RETRY_INITIAL_DELAY = float(os.getenv("RETRY_INITIAL_DELAY", "1.0"))
RETRY_MAX_DELAY = float(os.getenv("RETRY_MAX_DELAY", "30.0"))
RETRY_EXPONENTIAL_BASE = float(os.getenv("RETRY_EXPONENTIAL_BASE", "2.0"))


# ============================================================================
# Circuit Breaker Configuration
# ============================================================================

CIRCUIT_BREAKER_FAILURE_THRESHOLD = int(os.getenv("CIRCUIT_BREAKER_FAILURE_THRESHOLD", "5"))
CIRCUIT_BREAKER_SUCCESS_THRESHOLD = int(os.getenv("CIRCUIT_BREAKER_SUCCESS_THRESHOLD", "2"))
CIRCUIT_BREAKER_TIMEOUT = float(os.getenv("CIRCUIT_BREAKER_TIMEOUT", "60.0"))


# ============================================================================
# Memory and Cache Configuration
# ============================================================================

# Memory cache size limits
MEMORY_CACHE_SIZE = int(os.getenv("MEMORY_CACHE_SIZE", "1000"))
MEMORY_CACHE_MAX_ITEM_SIZE = int(os.getenv("MEMORY_CACHE_MAX_ITEM_SIZE", "10485760"))  # 10MB


# ============================================================================
# Validation and Limits
# ============================================================================

# Priority ranges
MIN_PRIORITY = 1
MAX_PRIORITY = 10
DEFAULT_PRIORITY = 5

# Task configuration limits
MIN_TIMEOUT = 1
MAX_TIMEOUT = 3600

# Pagination defaults
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


# ============================================================================
# Cost Calculation (EUR)
# ============================================================================

# Token costs for Claude 3.5 Sonnet (as of 2024)
COST_PER_1M_INPUT_TOKENS_USD = 3.0
COST_PER_1M_OUTPUT_TOKENS_USD = 15.0
USD_TO_EUR_RATE = float(os.getenv("USD_TO_EUR_RATE", "0.92"))


# ============================================================================
# Task Type Timeouts (recommended defaults)
# ============================================================================

TASK_TYPE_TIMEOUTS: Dict[str, int] = {
    "fetch_data": TASK_TIMEOUT_MEDIUM,
    "validate_data": TASK_TIMEOUT_SHORT,
    "process_data": TASK_TIMEOUT_LONG,
    "generate_report": TASK_TIMEOUT_MEDIUM,
    "scan_codebase": TASK_TIMEOUT_MEDIUM,
    "analyze_patterns": TASK_TIMEOUT_LONG,
    "security_audit": TASK_TIMEOUT_LONG,
    "generate_recommendations": TASK_TIMEOUT_MEDIUM,
}


# ============================================================================
# Helper Functions
# ============================================================================

def get_task_timeout(task_type: str) -> int:
    """
    Get recommended timeout for a task type.

    Args:
        task_type: Type of task (e.g., "process_data", "security_audit")

    Returns:
        Timeout in seconds (defaults to DEFAULT_REQUEST_TIMEOUT if not found)
    """
    return TASK_TYPE_TIMEOUTS.get(task_type, DEFAULT_REQUEST_TIMEOUT)


def get_config_summary() -> Dict[str, Any]:
    """
    Get summary of all configuration values.

    Returns:
        Dictionary with configuration categories and their values
    """
    return {
        "llm": {
            "default_max_tokens": DEFAULT_MAX_TOKENS,
            "streaming_max_tokens": STREAMING_MAX_TOKENS,
            "chat_max_tokens": CHAT_MAX_TOKENS,
            "default_model": DEFAULT_MODEL,
            "default_temperature": DEFAULT_TEMPERATURE,
        },
        "timeouts": {
            "default_request_timeout": DEFAULT_REQUEST_TIMEOUT,
            "health_check_timeout": HEALTH_CHECK_TIMEOUT,
            "llm_api_timeout": LLM_API_TIMEOUT,
            "task_timeout_short": TASK_TIMEOUT_SHORT,
            "task_timeout_medium": TASK_TIMEOUT_MEDIUM,
            "task_timeout_long": TASK_TIMEOUT_LONG,
            "task_timeout_max": TASK_TIMEOUT_MAX,
            "test_execution_timeout": TEST_EXECUTION_TIMEOUT,
        },
        "cache_ttl": {
            "default": DEFAULT_CACHE_TTL,
            "llm": LLM_CACHE_TTL,
            "agent": AGENT_CACHE_TTL,
            "artifact": ARTIFACT_TTL,
            "checkpoint": CHECKPOINT_TTL,
        },
        "network": {
            "api_port": API_PORT,
            "ui_port": UI_PORT,
            "postgres_port": POSTGRES_PORT,
            "redis_port": REDIS_PORT,
            "api_host": API_HOST,
            "postgres_host": POSTGRES_HOST,
            "redis_host": REDIS_HOST,
        },
        "retry": {
            "default_max_retries": DEFAULT_MAX_RETRIES,
            "initial_delay": RETRY_INITIAL_DELAY,
            "max_delay": RETRY_MAX_DELAY,
            "exponential_base": RETRY_EXPONENTIAL_BASE,
        },
        "circuit_breaker": {
            "failure_threshold": CIRCUIT_BREAKER_FAILURE_THRESHOLD,
            "success_threshold": CIRCUIT_BREAKER_SUCCESS_THRESHOLD,
            "timeout": CIRCUIT_BREAKER_TIMEOUT,
        },
        "limits": {
            "memory_cache_size": MEMORY_CACHE_SIZE,
            "default_page_size": DEFAULT_PAGE_SIZE,
            "max_page_size": MAX_PAGE_SIZE,
            "min_priority": MIN_PRIORITY,
            "max_priority": MAX_PRIORITY,
        },
    }


def validate_config() -> tuple[bool, list[str]]:
    """
    Validate configuration values.

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []

    # Check required environment variables
    if not os.getenv("ANTHROPIC_API_KEY"):
        errors.append("ANTHROPIC_API_KEY is not set")

    # Validate numeric ranges
    if DEFAULT_MAX_TOKENS < 1 or DEFAULT_MAX_TOKENS > 100000:
        errors.append(f"Invalid DEFAULT_MAX_TOKENS: {DEFAULT_MAX_TOKENS}")

    if DEFAULT_TEMPERATURE < 0 or DEFAULT_TEMPERATURE > 1:
        errors.append(f"Invalid DEFAULT_TEMPERATURE: {DEFAULT_TEMPERATURE}")

    if DEFAULT_REQUEST_TIMEOUT < MIN_TIMEOUT or DEFAULT_REQUEST_TIMEOUT > MAX_TIMEOUT:
        errors.append(f"Invalid DEFAULT_REQUEST_TIMEOUT: {DEFAULT_REQUEST_TIMEOUT}")

    # Validate ports
    for port_name, port_value in [
        ("API_PORT", API_PORT),
        ("POSTGRES_PORT", POSTGRES_PORT),
        ("REDIS_PORT", REDIS_PORT),
        ("UI_PORT", UI_PORT),
    ]:
        if port_value < 1 or port_value > 65535:
            errors.append(f"Invalid {port_name}: {port_value}")

    return len(errors) == 0, errors
