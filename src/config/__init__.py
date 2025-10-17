"""
Configuration module for DevMatrix.

This module provides centralized configuration management with environment
variable overrides and validation.
"""

from src.config.constants import (
    # LLM Configuration
    DEFAULT_MAX_TOKENS,
    STREAMING_MAX_TOKENS,
    CHAT_MAX_TOKENS,
    DEFAULT_MODEL,
    DEFAULT_TEMPERATURE,
    # Network Configuration
    API_HOST,
    API_PORT,
    UI_PORT,
    POSTGRES_HOST,
    POSTGRES_PORT,
    REDIS_HOST,
    REDIS_PORT,
    CHROMADB_HOST,
    CHROMADB_PORT,
    # RAG Configuration
    EMBEDDING_MODEL,
    RAG_TOP_K,
    RAG_SIMILARITY_THRESHOLD,
    RAG_ENABLE_FEEDBACK,
    CHROMADB_COLLECTION_NAME,
    CHROMADB_DISTANCE_METRIC,
    RAG_BATCH_SIZE,
    RAG_MAX_CONTEXT_LENGTH,
    RAG_CACHE_ENABLED,
    # Cache Configuration
    DEFAULT_CACHE_TTL,
    LLM_CACHE_TTL,
    AGENT_CACHE_TTL,
    # Timeout Configuration
    DEFAULT_REQUEST_TIMEOUT,
    LLM_API_TIMEOUT,
    TASK_TIMEOUT_SHORT,
    TASK_TIMEOUT_MEDIUM,
    TASK_TIMEOUT_LONG,
    # Retry Configuration
    DEFAULT_MAX_RETRIES,
    RETRY_INITIAL_DELAY,
    RETRY_MAX_DELAY,
    # Helper Functions
    get_config_summary,
    validate_config,
    get_task_timeout,
)

__all__ = [
    # LLM Configuration
    "DEFAULT_MAX_TOKENS",
    "STREAMING_MAX_TOKENS",
    "CHAT_MAX_TOKENS",
    "DEFAULT_MODEL",
    "DEFAULT_TEMPERATURE",
    # Network Configuration
    "API_HOST",
    "API_PORT",
    "UI_PORT",
    "POSTGRES_HOST",
    "POSTGRES_PORT",
    "REDIS_HOST",
    "REDIS_PORT",
    "CHROMADB_HOST",
    "CHROMADB_PORT",
    # RAG Configuration
    "EMBEDDING_MODEL",
    "RAG_TOP_K",
    "RAG_SIMILARITY_THRESHOLD",
    "RAG_ENABLE_FEEDBACK",
    "CHROMADB_COLLECTION_NAME",
    "CHROMADB_DISTANCE_METRIC",
    "RAG_BATCH_SIZE",
    "RAG_MAX_CONTEXT_LENGTH",
    "RAG_CACHE_ENABLED",
    # Cache Configuration
    "DEFAULT_CACHE_TTL",
    "LLM_CACHE_TTL",
    "AGENT_CACHE_TTL",
    # Timeout Configuration
    "DEFAULT_REQUEST_TIMEOUT",
    "LLM_API_TIMEOUT",
    "TASK_TIMEOUT_SHORT",
    "TASK_TIMEOUT_MEDIUM",
    "TASK_TIMEOUT_LONG",
    # Retry Configuration
    "DEFAULT_MAX_RETRIES",
    "RETRY_INITIAL_DELAY",
    "RETRY_MAX_DELAY",
    # Helper Functions
    "get_config_summary",
    "validate_config",
    "get_task_timeout",
]
