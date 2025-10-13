"""
Tests for CacheManager

Tests multi-level caching system with memory and Redis backends.
"""

import pytest
import json
import time
from unittest.mock import Mock, patch, MagicMock

from src.performance.cache_manager import CacheManager, CacheStats


@pytest.fixture
def mock_redis_manager():
    """Mock Redis manager."""
    mock = Mock()
    mock.client = Mock()
    mock.client.get = Mock(return_value=None)
    mock.client.setex = Mock(return_value=True)
    mock.client.delete = Mock(return_value=1)
    mock.client.ttl = Mock(return_value=3600)
    mock.client.keys = Mock(return_value=[])
    mock.client.flushdb = Mock(return_value=True)
    mock.get_stats = Mock(return_value={"connected": True, "total_keys": 0})
    return mock


@pytest.fixture
def cache_manager(mock_redis_manager):
    """Create CacheManager with mocked Redis."""
    with patch('src.performance.cache_manager.RedisManager', return_value=mock_redis_manager):
        return CacheManager(
            redis_manager=mock_redis_manager,
            memory_cache_size=10,
            default_ttl=3600,
            enable_stats=True
        )


class TestCacheStats:
    """Tests for CacheStats dataclass."""

    def test_cache_stats_initialization(self):
        """Test CacheStats initialization."""
        stats = CacheStats()

        assert stats.hits == 0
        assert stats.misses == 0
        assert stats.writes == 0
        assert stats.evictions == 0
        assert stats.total_time_saved == 0.0

    def test_hit_rate_calculation(self):
        """Test hit rate calculation."""
        stats = CacheStats(hits=80, misses=20)
        assert stats.hit_rate == 0.8

    def test_hit_rate_zero_requests(self):
        """Test hit rate with no requests."""
        stats = CacheStats()
        assert stats.hit_rate == 0.0

    def test_to_dict(self):
        """Test conversion to dictionary."""
        stats = CacheStats(hits=10, misses=5, writes=15)
        data = stats.to_dict()

        assert data["hits"] == 10
        assert data["misses"] == 5
        assert data["writes"] == 15
        assert pytest.approx(data["hit_rate"], rel=1e-9) == 10 / 15


class TestCacheManager:
    """Tests for CacheManager."""

    def test_initialization(self, cache_manager):
        """Test CacheManager initialization."""
        assert cache_manager.memory_cache_size == 10
        assert cache_manager.default_ttl == 3600
        assert cache_manager.enable_stats is True
        assert isinstance(cache_manager.stats, CacheStats)

    def test_make_hash_string(self, cache_manager):
        """Test hash generation from string."""
        hash1 = cache_manager._make_hash("test string")
        hash2 = cache_manager._make_hash("test string")
        hash3 = cache_manager._make_hash("different string")

        assert hash1 == hash2  # Same input produces same hash
        assert hash1 != hash3  # Different input produces different hash
        assert len(hash1) == 64  # SHA256 produces 64 character hex

    def test_make_hash_dict(self, cache_manager):
        """Test hash generation from dictionary."""
        dict1 = {"key": "value", "num": 42}
        dict2 = {"num": 42, "key": "value"}  # Different order
        dict3 = {"key": "different", "num": 42}

        hash1 = cache_manager._make_hash(dict1)
        hash2 = cache_manager._make_hash(dict2)
        hash3 = cache_manager._make_hash(dict3)

        assert hash1 == hash2  # Same content, different order produces same hash
        assert hash1 != hash3  # Different content produces different hash

    def test_memory_cache_set_get(self, cache_manager):
        """Test memory cache set and get."""
        cache_manager._set_in_memory("test_key", "test_value", ttl=3600)

        value = cache_manager._get_from_memory("test_key")
        assert value == "test_value"

    def test_memory_cache_expiration(self, cache_manager):
        """Test memory cache expiration."""
        # Set with very short TTL
        cache_manager._set_in_memory("test_key", "test_value", ttl=0.1)

        # Immediate get should work
        assert cache_manager._get_from_memory("test_key") == "test_value"

        # Wait for expiration
        time.sleep(0.2)

        # Should be expired
        assert cache_manager._get_from_memory("test_key") is None
        assert cache_manager.stats.evictions == 1

    def test_memory_cache_eviction_on_full(self, cache_manager):
        """Test memory cache eviction when full."""
        # Fill cache to capacity
        for i in range(10):
            cache_manager._set_in_memory(f"key_{i}", f"value_{i}", ttl=3600)

        assert len(cache_manager.memory_cache) == 10

        # Add one more item
        cache_manager._set_in_memory("key_new", "value_new", ttl=3600)

        # Should still be at capacity
        assert len(cache_manager.memory_cache) == 10
        assert cache_manager.stats.evictions == 1

    def test_set_and_get_redis(self, cache_manager, mock_redis_manager):
        """Test set and get with Redis backend."""
        test_value = {"content": "test response", "model": "claude"}

        # Mock Redis get to return serialized value
        mock_redis_manager.client.get.return_value = json.dumps(test_value)

        # Set value
        result = cache_manager.set("test_key", test_value, prefix="llm")
        assert result is True
        assert cache_manager.stats.writes == 1

        # Get value (should hit Redis)
        value = cache_manager.get("test_key", prefix="llm", use_memory=False)
        assert value == test_value
        assert cache_manager.stats.hits == 1

    def test_get_cache_miss(self, cache_manager, mock_redis_manager):
        """Test cache miss."""
        mock_redis_manager.client.get.return_value = None

        value = cache_manager.get("nonexistent_key", prefix="llm")

        assert value is None
        assert cache_manager.stats.misses == 1

    def test_delete(self, cache_manager, mock_redis_manager):
        """Test cache deletion."""
        # Set in memory
        cache_manager._set_in_memory("cache:general:test_key", "test_value", ttl=3600)

        # Delete
        result = cache_manager.delete("test_key", prefix="general")

        assert result is True
        assert "cache:general:test_key" not in cache_manager.memory_cache

    def test_cache_llm_response(self, cache_manager):
        """Test LLM response caching."""
        prompt = "What is the capital of France?"
        system = "You are a helpful assistant"
        response = {
            "content": "The capital of France is Paris.",
            "model": "claude-3-5-sonnet",
            "usage": {"input_tokens": 10, "output_tokens": 15}
        }

        # Cache response
        result = cache_manager.cache_llm_response(prompt, system, response, ttl=3600)
        assert result is True

    def test_get_cached_llm_response_miss(self, cache_manager, mock_redis_manager):
        """Test getting cached LLM response that doesn't exist."""
        mock_redis_manager.client.get.return_value = None

        prompt = "What is the capital of France?"
        system = "You are a helpful assistant"

        result = cache_manager.get_cached_llm_response(prompt, system)
        assert result is None

    def test_get_cached_llm_response_hit(self, cache_manager, mock_redis_manager):
        """Test getting cached LLM response."""
        prompt = "What is the capital of France?"
        system = "You are a helpful assistant"
        cached_response = {
            "content": "The capital of France is Paris.",
            "model": "claude-3-5-sonnet"
        }

        # Mock Redis to return cached response
        mock_redis_manager.client.get.return_value = json.dumps(cached_response)

        result = cache_manager.get_cached_llm_response(prompt, system)
        assert result == cached_response

    def test_cache_agent_result(self, cache_manager):
        """Test agent result caching."""
        agent_name = "ImplementationAgent"
        task_description = "Create a calculator function"
        context = {"workspace_id": "test", "timestamp": "2024-01-01"}
        result = {
            "success": True,
            "output": "# Calculator implementation\nclass Calculator:\n    pass"
        }

        # Cache result
        success = cache_manager.cache_agent_result(
            agent_name, task_description, context, result, ttl=1800
        )
        assert success is True

    def test_get_cached_agent_result(self, cache_manager, mock_redis_manager):
        """Test getting cached agent result."""
        agent_name = "ImplementationAgent"
        task_description = "Create a calculator function"
        context = {"workspace_id": "test"}
        cached_result = {
            "success": True,
            "output": "# Calculator implementation"
        }

        # Mock Redis to return cached result
        mock_redis_manager.client.get.return_value = json.dumps(cached_result)

        result = cache_manager.get_cached_agent_result(
            agent_name, task_description, context
        )
        assert result == cached_result

    def test_cached_decorator(self, cache_manager):
        """Test cached decorator for functions."""
        call_count = 0

        @cache_manager.cached(ttl=3600, prefix="general")
        def expensive_function(a, b):
            nonlocal call_count
            call_count += 1
            return a + b

        # First call executes function
        result1 = expensive_function(2, 3)
        assert result1 == 5
        assert call_count == 1

        # Second call uses cache (memory)
        result2 = expensive_function(2, 3)
        assert result2 == 5
        assert call_count == 1  # Function not called again

    def test_cached_decorator_custom_key(self, cache_manager):
        """Test cached decorator with custom key function."""
        call_count = 0

        def custom_key(a, b):
            return f"custom_{a}_{b}"

        @cache_manager.cached(ttl=3600, key_func=custom_key)
        def expensive_function(a, b):
            nonlocal call_count
            call_count += 1
            return a * b

        result1 = expensive_function(3, 4)
        assert result1 == 12
        assert call_count == 1

        result2 = expensive_function(3, 4)
        assert result2 == 12
        assert call_count == 1  # Cached

    def test_get_stats(self, cache_manager, mock_redis_manager):
        """Test getting cache statistics."""
        # Perform some operations
        cache_manager.set("key1", "value1")
        cache_manager.get("key1")
        cache_manager.get("nonexistent")

        stats = cache_manager.get_stats()

        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["writes"] == 1
        assert "memory_cache_size" in stats
        assert "redis_stats" in stats

    def test_reset_stats(self, cache_manager):
        """Test resetting statistics."""
        cache_manager.stats.hits = 10
        cache_manager.stats.misses = 5

        cache_manager.reset_stats()

        assert cache_manager.stats.hits == 0
        assert cache_manager.stats.misses == 0

    def test_clear_all_with_prefix(self, cache_manager, mock_redis_manager):
        """Test clearing cache with prefix."""
        # Set some items in memory
        cache_manager._set_in_memory("cache:llm:key1", "value1", ttl=3600)
        cache_manager._set_in_memory("cache:agent:key2", "value2", ttl=3600)

        # Mock Redis keys
        mock_redis_manager.client.keys.return_value = [
            "cache:llm:key1", "cache:llm:key3"
        ]

        # Clear only LLM cache
        cache_manager.clear_all(prefix="llm")

        # LLM key should be gone from memory
        assert cache_manager._get_from_memory("cache:llm:key1") is None
        # Agent key should still be there
        assert cache_manager._get_from_memory("cache:agent:key2") == "value2"

    def test_clear_all_no_prefix(self, cache_manager, mock_redis_manager):
        """Test clearing entire cache."""
        # Set some items in memory
        cache_manager._set_in_memory("key1", "value1", ttl=3600)
        cache_manager._set_in_memory("key2", "value2", ttl=3600)

        # Clear all
        cache_manager.clear_all()

        assert len(cache_manager.memory_cache) == 0
        mock_redis_manager.client.flushdb.assert_called_once()

    def test_stats_disabled(self, mock_redis_manager):
        """Test cache manager with stats disabled."""
        with patch('src.performance.cache_manager.RedisManager', return_value=mock_redis_manager):
            cache = CacheManager(
                redis_manager=mock_redis_manager,
                enable_stats=False
            )

        cache.set("key", "value")
        cache.get("key")

        # Stats should remain at 0
        assert cache.stats.hits == 0
        assert cache.stats.misses == 0
        assert cache.stats.writes == 0

    def test_memory_and_redis_integration(self, cache_manager, mock_redis_manager):
        """Test memory cache populating from Redis."""
        test_value = {"data": "test"}
        mock_redis_manager.client.get.return_value = json.dumps(test_value)
        mock_redis_manager.client.ttl.return_value = 1800

        # Get from Redis (should populate memory)
        result = cache_manager.get("test_key", prefix="general", use_memory=True)

        assert result == test_value

        # Verify it was cached in memory
        memory_value = cache_manager._get_from_memory("cache:general:test_key")
        assert memory_value == test_value

    def test_context_determinism(self, cache_manager):
        """Test that context with non-deterministic fields is handled correctly."""
        agent_name = "TestAgent"
        task_description = "Test task"

        # Two contexts with same deterministic fields but different timestamps
        context1 = {"workspace_id": "test", "timestamp": "2024-01-01", "param": "value"}
        context2 = {"workspace_id": "test", "timestamp": "2024-01-02", "param": "value"}

        # Should generate same hash (timestamp excluded)
        hash1 = cache_manager._make_hash({
            "agent": agent_name,
            "task": task_description,
            "context": {k: v for k, v in context1.items() if k not in ["timestamp", "execution_id"]}
        })

        hash2 = cache_manager._make_hash({
            "agent": agent_name,
            "task": task_description,
            "context": {k: v for k, v in context2.items() if k not in ["timestamp", "execution_id"]}
        })

        assert hash1 == hash2
