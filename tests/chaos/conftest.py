"""
Pytest configuration and fixtures for chaos testing.
"""

import pytest
from unittest.mock import Mock, patch
import asyncio


@pytest.fixture
def mock_redis_failure():
    """Mock Redis connection failures."""
    with patch('redis.Redis.ping') as mock_ping:
        mock_ping.side_effect = ConnectionError("Redis connection failed")
        yield mock_ping


@pytest.fixture
def mock_postgres_failure():
    """Mock PostgreSQL connection failures."""
    with patch('sqlalchemy.engine.Engine.connect') as mock_connect:
        mock_connect.side_effect = Exception("PostgreSQL connection failed")
        yield mock_connect


@pytest.fixture
def mock_anthropic_timeout():
    """Mock Anthropic API timeout."""
    with patch('anthropic.Anthropic.messages.create') as mock_create:
        mock_create.side_effect = asyncio.TimeoutError("API request timed out")
        yield mock_create


@pytest.fixture
def mock_chromadb_unavailable():
    """Mock ChromaDB unavailability."""
    with patch('chromadb.Client') as mock_client:
        mock_client.side_effect = ConnectionError("ChromaDB not available")
        yield mock_client


@pytest.fixture
def mock_network_error():
    """Mock generic network errors."""
    def create_network_error(*args, **kwargs):
        raise ConnectionError("Network unreachable")
    return create_network_error

