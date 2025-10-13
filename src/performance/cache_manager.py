"""
Cache Manager for Performance Optimization

Provides intelligent caching for LLM responses, agent results, and task outputs.
Features:
- Content-addressable caching (hash-based)
- Configurable TTL policies
- Cache statistics and monitoring
- Decorator for easy integration
- Multi-level cache strategy (memory + Redis)
"""

import hashlib
import json
import time
from typing import Any, Callable, Dict, Optional
from functools import wraps
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta

from src.state.redis_manager import RedisManager


@dataclass
class CacheStats:
    """Statistics for cache performance monitoring."""

    hits: int = 0
    misses: int = 0
    writes: int = 0
    evictions: int = 0
    total_time_saved: float = 0.0  # Seconds saved by cache hits

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            **asdict(self),
            "hit_rate": self.hit_rate
        }


class CacheManager:
    """
    Manages multi-level caching for performance optimization.

    Cache Levels:
    1. Memory cache (L1): Fastest, limited size, in-process
    2. Redis cache (L2): Shared across processes, persistent

    Usage:
        cache = CacheManager()

        # Manual caching
        result = cache.get("key")
        if result is None:
            result = expensive_operation()
            cache.set("key", result, ttl=3600)

        # Decorator caching
        @cache.cached(ttl=3600)
        def expensive_function(arg1, arg2):
            return compute_result(arg1, arg2)
    """

    def __init__(
        self,
        redis_manager: Optional[RedisManager] = None,
        memory_cache_size: int = 1000,
        default_ttl: int = 3600,
        enable_stats: bool = True
    ):
        """
        Initialize cache manager.

        Args:
            redis_manager: Redis manager instance (creates new if None)
            memory_cache_size: Maximum items in memory cache
            default_ttl: Default TTL in seconds (1 hour)
            enable_stats: Enable statistics tracking
        """
        self.redis = redis_manager or RedisManager()
        self.memory_cache: Dict[str, tuple[Any, float]] = {}  # (value, expiry_timestamp)
        self.memory_cache_size = memory_cache_size
        self.default_ttl = default_ttl
        self.enable_stats = enable_stats

        # Statistics tracking
        self.stats = CacheStats()

        # Cache key prefixes
        self.prefixes = {
            "llm": "cache:llm:",
            "agent": "cache:agent:",
            "task": "cache:task:",
            "general": "cache:general:"
        }

    def _make_hash(self, data: Any) -> str:
        """
        Create deterministic hash from data.

        Args:
            data: Data to hash (dict, str, or JSON-serializable)

        Returns:
            Hexadecimal hash string
        """
        if isinstance(data, str):
            content = data
        elif isinstance(data, dict):
            # Sort keys for deterministic hashing
            content = json.dumps(data, sort_keys=True)
        else:
            content = str(data)

        return hashlib.sha256(content.encode()).hexdigest()

    def _make_key(self, prefix: str, identifier: str) -> str:
        """Create cache key with prefix."""
        return f"{prefix}{identifier}"

    def _get_from_memory(self, key: str) -> Optional[Any]:
        """Get value from memory cache."""
        if key in self.memory_cache:
            value, expiry = self.memory_cache[key]

            # Check if expired
            if time.time() < expiry:
                return value
            else:
                # Expired, remove from cache
                del self.memory_cache[key]
                if self.enable_stats:
                    self.stats.evictions += 1

        return None

    def _set_in_memory(self, key: str, value: Any, ttl: int):
        """Set value in memory cache with TTL."""
        # Evict oldest entry if cache is full
        if len(self.memory_cache) >= self.memory_cache_size:
            oldest_key = min(self.memory_cache.keys(),
                           key=lambda k: self.memory_cache[k][1])
            del self.memory_cache[oldest_key]
            if self.enable_stats:
                self.stats.evictions += 1

        expiry = time.time() + ttl
        self.memory_cache[key] = (value, expiry)

    def get(
        self,
        key: str,
        prefix: str = "general",
        use_memory: bool = True
    ) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key
            prefix: Key prefix (llm, agent, task, general)
            use_memory: Check memory cache first

        Returns:
            Cached value if found, None otherwise
        """
        full_key = self._make_key(self.prefixes.get(prefix, self.prefixes["general"]), key)

        # Try memory cache first (L1)
        if use_memory:
            value = self._get_from_memory(full_key)
            if value is not None:
                if self.enable_stats:
                    self.stats.hits += 1
                return value

        # Try Redis cache (L2)
        try:
            redis_value = self.redis.client.get(full_key)
            if redis_value:
                # Deserialize
                value = json.loads(redis_value)

                # Populate memory cache
                if use_memory:
                    # Get TTL from Redis
                    ttl = self.redis.client.ttl(full_key)
                    if ttl > 0:
                        self._set_in_memory(full_key, value, ttl)

                if self.enable_stats:
                    self.stats.hits += 1
                return value
        except Exception as e:
            print(f"Cache get error: {e}")

        if self.enable_stats:
            self.stats.misses += 1
        return None

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        prefix: str = "general",
        use_memory: bool = True
    ) -> bool:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache (must be JSON-serializable)
            ttl: Time-to-live in seconds (uses default if None)
            prefix: Key prefix (llm, agent, task, general)
            use_memory: Also cache in memory

        Returns:
            True if successful, False otherwise
        """
        ttl = ttl or self.default_ttl
        full_key = self._make_key(self.prefixes.get(prefix, self.prefixes["general"]), key)

        try:
            # Store in Redis (L2)
            value_json = json.dumps(value)
            self.redis.client.setex(full_key, ttl, value_json)

            # Store in memory (L1)
            if use_memory:
                self._set_in_memory(full_key, value, ttl)

            if self.enable_stats:
                self.stats.writes += 1

            return True

        except Exception as e:
            print(f"Cache set error: {e}")
            return False

    def delete(self, key: str, prefix: str = "general") -> bool:
        """
        Delete value from cache.

        Args:
            key: Cache key
            prefix: Key prefix

        Returns:
            True if deleted, False otherwise
        """
        full_key = self._make_key(self.prefixes.get(prefix, self.prefixes["general"]), key)

        # Remove from memory
        if full_key in self.memory_cache:
            del self.memory_cache[full_key]

        # Remove from Redis
        try:
            deleted = self.redis.client.delete(full_key) > 0
            return deleted
        except Exception as e:
            print(f"Cache delete error: {e}")
            return False

    def cache_llm_response(
        self,
        prompt: str,
        system: Optional[str],
        response: Dict[str, Any],
        ttl: int = 3600
    ) -> bool:
        """
        Cache LLM response based on prompt hash.

        Args:
            prompt: User prompt
            system: System prompt
            response: LLM response dictionary
            ttl: Cache TTL in seconds (default 1 hour)

        Returns:
            True if cached successfully
        """
        # Create hash from prompt + system
        cache_key = self._make_hash({
            "prompt": prompt,
            "system": system or ""
        })

        return self.set(cache_key, response, ttl=ttl, prefix="llm")

    def get_cached_llm_response(
        self,
        prompt: str,
        system: Optional[str]
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached LLM response.

        Args:
            prompt: User prompt
            system: System prompt

        Returns:
            Cached response if found, None otherwise
        """
        cache_key = self._make_hash({
            "prompt": prompt,
            "system": system or ""
        })

        return self.get(cache_key, prefix="llm")

    def cache_agent_result(
        self,
        agent_name: str,
        task_description: str,
        context: Dict[str, Any],
        result: Dict[str, Any],
        ttl: int = 1800
    ) -> bool:
        """
        Cache agent execution result.

        Args:
            agent_name: Name of the agent
            task_description: Task description
            context: Task context (excluding non-deterministic fields)
            result: Agent result
            ttl: Cache TTL in seconds (default 30 minutes)

        Returns:
            True if cached successfully
        """
        # Create deterministic cache key
        cache_data = {
            "agent": agent_name,
            "task": task_description,
            "context": {k: v for k, v in context.items()
                       if k not in ["timestamp", "execution_id"]}
        }
        cache_key = self._make_hash(cache_data)

        return self.set(cache_key, result, ttl=ttl, prefix="agent")

    def get_cached_agent_result(
        self,
        agent_name: str,
        task_description: str,
        context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached agent result.

        Args:
            agent_name: Name of the agent
            task_description: Task description
            context: Task context

        Returns:
            Cached result if found, None otherwise
        """
        cache_data = {
            "agent": agent_name,
            "task": task_description,
            "context": {k: v for k, v in context.items()
                       if k not in ["timestamp", "execution_id"]}
        }
        cache_key = self._make_hash(cache_data)

        return self.get(cache_key, prefix="agent")

    def cached(
        self,
        ttl: Optional[int] = None,
        prefix: str = "general",
        key_func: Optional[Callable] = None
    ):
        """
        Decorator for caching function results.

        Args:
            ttl: Cache TTL in seconds
            prefix: Cache key prefix
            key_func: Custom function to generate cache key from args

        Usage:
            @cache.cached(ttl=3600)
            def expensive_function(arg1, arg2):
                return compute_result(arg1, arg2)
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Generate cache key
                if key_func:
                    cache_key = key_func(*args, **kwargs)
                else:
                    # Default: hash function name + args + kwargs
                    cache_data = {
                        "func": func.__name__,
                        "args": args,
                        "kwargs": kwargs
                    }
                    cache_key = self._make_hash(cache_data)

                # Try to get from cache
                start_time = time.time()
                cached_result = self.get(cache_key, prefix=prefix)

                if cached_result is not None:
                    elapsed = time.time() - start_time
                    if self.enable_stats:
                        self.stats.total_time_saved += elapsed
                    return cached_result

                # Execute function
                result = func(*args, **kwargs)

                # Cache result
                self.set(cache_key, result, ttl=ttl, prefix=prefix)

                return result

            return wrapper
        return decorator

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache performance stats
        """
        return {
            **self.stats.to_dict(),
            "memory_cache_size": len(self.memory_cache),
            "memory_cache_limit": self.memory_cache_size,
            "redis_stats": self.redis.get_stats()
        }

    def reset_stats(self):
        """Reset cache statistics."""
        self.stats = CacheStats()

    def clear_all(self, prefix: Optional[str] = None):
        """
        Clear all cache entries (use with caution).

        Args:
            prefix: If specified, only clear entries with this prefix
        """
        # Clear memory cache
        if prefix:
            full_prefix = self.prefixes.get(prefix, prefix)
            keys_to_delete = [k for k in self.memory_cache.keys()
                            if k.startswith(full_prefix)]
            for key in keys_to_delete:
                del self.memory_cache[key]
        else:
            self.memory_cache.clear()

        # Clear Redis cache
        try:
            if prefix:
                full_prefix = self.prefixes.get(prefix, prefix)
                pattern = f"{full_prefix}*"
                keys = self.redis.client.keys(pattern)
                if keys:
                    self.redis.client.delete(*keys)
            else:
                # WARNING: This clears ALL Redis keys
                self.redis.client.flushdb()
        except Exception as e:
            print(f"Cache clear error: {e}")
