"""
Redis State Manager

Manages temporary workflow state in Redis for fast access during agent execution.
State TTL: 30 minutes (can be extended for long-running workflows)
"""

import json
import os
from typing import Any, Optional
from datetime import timedelta

import redis
from dotenv import load_dotenv

from src.observability import get_logger
from src.config.constants import (
    REDIS_HOST,
    REDIS_PORT,
    CACHE_TTL_SHORT,
    LLM_CACHE_TTL,
    IR_CACHE_TTL,
    SOCKET_CONNECT_TIMEOUT,
    SOCKET_TIMEOUT,
)

# Load environment variables
load_dotenv()


class RedisManager:
    """
    Manages workflow state in Redis with fallback mode.

    Features:
    - Automatic fallback to in-memory storage if Redis unavailable
    - Automatic reconnection attempts
    - Graceful degradation for non-critical operations

    Usage:
        manager = RedisManager()  # Auto-fallback if Redis down
        manager.save_workflow_state(workflow_id, state_dict)
        state = manager.get_workflow_state(workflow_id)
    """

    def __init__(
        self,
        host: str = None,
        port: int = None,
        db: int = 0,
        default_ttl: int = CACHE_TTL_SHORT,  # 30 minutes
        enable_fallback: bool = True,
    ):
        """
        Initialize Redis connection with fallback support.

        Args:
            host: Redis host (defaults to env REDIS_HOST or localhost)
            port: Redis port (defaults to env REDIS_PORT or 6379)
            db: Redis database number
            default_ttl: Default TTL in seconds (30 min)
            enable_fallback: Enable in-memory fallback if Redis unavailable
        """
        self.host = host or REDIS_HOST
        self.port = int(port or REDIS_PORT)
        self.db = db
        self.default_ttl = default_ttl
        self.enable_fallback = enable_fallback
        self.logger = get_logger("redis_manager")

        # Connection state
        self.connected = False
        self.client = None

        # Fallback in-memory storage
        self._fallback_store = {}
        self._fallback_ttl = {}  # Track expiry times

        # Bug #35 fix: Skip auto-connection in E2E tests where Redis is not needed
        # Set SKIP_REDIS=1 to avoid unnecessary Redis connections during E2E testing
        skip_redis = os.getenv("SKIP_REDIS", "").lower() in ("1", "true", "yes")
        if skip_redis and enable_fallback:
            # E2E test mode - use fallback silently without attempting connection
            self.logger.debug("SKIP_REDIS set - using in-memory fallback mode")
        else:
            # Default behavior - attempt connection (maintains backward compatibility)
            self._connect()

    def _connect(self) -> bool:
        """
        Establish Redis connection.

        Returns:
            True if connected, False if fallback mode
        """
        try:
            self.client = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                decode_responses=True,
                socket_connect_timeout=SOCKET_CONNECT_TIMEOUT,
                socket_timeout=SOCKET_TIMEOUT,
                retry_on_timeout=True,
                health_check_interval=30
            )
            self.client.ping()
            self.connected = True
            self.logger.info("Redis connection established",
                           host=self.host,
                           port=self.port,
                           db=self.db)
            return True

        except redis.ConnectionError as e:
            self.connected = False
            self.client = None

            if self.enable_fallback:
                self.logger.warning("Redis unavailable - operating in FALLBACK mode (in-memory storage)",
                                  host=self.host,
                                  port=self.port,
                                  error=str(e),
                                  fallback_enabled=True)
                return False
            else:
                self.logger.error("Failed to connect to Redis and fallback disabled",
                                host=self.host,
                                port=self.port,
                                error=str(e))
                raise ConnectionError(
                    f"Failed to connect to Redis at {self.host}:{self.port}"
                ) from e

    def _ensure_connected(self) -> bool:
        """
        Verify connection and attempt reconnection if needed.

        Returns:
            True if connected to Redis, False if in fallback mode
        """
        if self.connected:
            try:
                self.client.ping()
                return True
            except redis.ConnectionError:
                self.logger.warning("Redis connection lost, attempting reconnection")
                self.connected = False

        # Try to reconnect
        if not self.connected:
            try:
                return self._connect()
            except:
                return False

        return False

    def save_workflow_state(
        self, workflow_id: str, state: dict[str, Any], ttl: int = None
    ) -> bool:
        """
        Save workflow state to Redis or fallback storage.

        Args:
            workflow_id: Unique workflow identifier
            state: State dictionary to save
            ttl: Time-to-live in seconds (uses default if not provided)

        Returns:
            True if successful, False otherwise
        """
        import time

        key = f"workflow:{workflow_id}"
        ttl = ttl or self.default_ttl

        # Try Redis first
        if self._ensure_connected():
            try:
                state_json = json.dumps(state)
                self.client.setex(key, ttl, state_json)
                return True
            except Exception as e:
                self.logger.error("Failed to save workflow state to Redis",
                                workflow_id=workflow_id,
                                error=str(e),
                                error_type=type(e).__name__)
                # Fall through to fallback

        # Use fallback storage
        if self.enable_fallback:
            try:
                self._fallback_store[key] = state
                self._fallback_ttl[key] = time.time() + ttl
                self.logger.debug("Saved workflow state to fallback storage",
                                workflow_id=workflow_id)
                return True
            except Exception as e:
                self.logger.error("Failed to save workflow state to fallback",
                                workflow_id=workflow_id,
                                error=str(e))
                return False

        return False

    def get_workflow_state(self, workflow_id: str) -> Optional[dict[str, Any]]:
        """
        Retrieve workflow state from Redis or fallback storage.

        Args:
            workflow_id: Unique workflow identifier

        Returns:
            State dictionary if found, None otherwise
        """
        import time

        key = f"workflow:{workflow_id}"

        # Try Redis first
        if self._ensure_connected():
            try:
                state_json = self.client.get(key)
                if state_json is not None:
                    return json.loads(state_json)
            except Exception as e:
                self.logger.error("Failed to retrieve workflow state from Redis",
                                workflow_id=workflow_id,
                                error=str(e),
                                error_type=type(e).__name__)
                # Fall through to fallback

        # Check fallback storage
        if self.enable_fallback and key in self._fallback_store:
            # Check if expired
            if key in self._fallback_ttl:
                if time.time() < self._fallback_ttl[key]:
                    return self._fallback_store[key]
                else:
                    # Expired, clean up
                    del self._fallback_store[key]
                    del self._fallback_ttl[key]
            else:
                # No TTL set, return anyway
                return self._fallback_store[key]

        return None

    def extend_workflow_ttl(self, workflow_id: str, additional_seconds: int) -> bool:
        """
        Extend the TTL of a workflow state.

        Args:
            workflow_id: Unique workflow identifier
            additional_seconds: Seconds to add to current TTL

        Returns:
            True if successful, False otherwise
        """
        key = f"workflow:{workflow_id}"

        # Try Redis first
        if self._ensure_connected():
            try:
                current_ttl = self.client.ttl(key)
                if current_ttl == -2:  # Key doesn't exist
                    return False
                new_ttl = max(current_ttl, 0) + additional_seconds
                self.client.expire(key, new_ttl)
                return True
            except Exception as e:
                self.logger.error("Failed to extend workflow TTL in Redis",
                                workflow_id=workflow_id,
                                error=str(e))

        # Fallback storage
        if self.enable_fallback and key in self._fallback_ttl:
            self._fallback_ttl[key] += additional_seconds
            return True

        return False

    def delete_workflow_state(self, workflow_id: str) -> bool:
        """
        Delete workflow state from Redis or fallback.

        Args:
            workflow_id: Unique workflow identifier

        Returns:
            True if deleted, False if not found or error
        """
        key = f"workflow:{workflow_id}"
        deleted = False

        # Try Redis first
        if self._ensure_connected():
            try:
                deleted = self.client.delete(key) > 0
            except Exception as e:
                self.logger.error("Failed to delete workflow state from Redis",
                                workflow_id=workflow_id,
                                error=str(e))

        # Fallback storage
        if self.enable_fallback:
            if key in self._fallback_store:
                del self._fallback_store[key]
                if key in self._fallback_ttl:
                    del self._fallback_ttl[key]
                deleted = True

        return deleted

    def cache_llm_response(
        self, prompt_hash: str, response: str, ttl: int = LLM_CACHE_TTL
    ) -> bool:
        """
        Cache LLM response for reuse.

        Args:
            prompt_hash: Hash of the prompt (for lookup)
            response: LLM response to cache
            ttl: Cache TTL in seconds (default 1 hour)

        Returns:
            True if successful, False otherwise
        """
        import time

        key = f"llm_cache:{prompt_hash}"

        # Try Redis first
        if self._ensure_connected():
            try:
                self.client.setex(key, ttl, response)
                return True
            except Exception as e:
                self.logger.warning("Failed to cache LLM response in Redis",
                                  prompt_hash=prompt_hash[:16],
                                  error=str(e))

        # Fallback storage
        if self.enable_fallback:
            self._fallback_store[key] = response
            self._fallback_ttl[key] = time.time() + ttl
            return True

        return False

    def get_cached_llm_response(self, prompt_hash: str) -> Optional[str]:
        """
        Retrieve cached LLM response.

        Args:
            prompt_hash: Hash of the prompt

        Returns:
            Cached response if found, None otherwise
        """
        import time

        key = f"llm_cache:{prompt_hash}"

        # Try Redis first
        if self._ensure_connected():
            try:
                result = self.client.get(key)
                if result:
                    return result
            except Exception as e:
                self.logger.warning("Failed to retrieve cached LLM response from Redis",
                                  prompt_hash=prompt_hash[:16],
                                  error=str(e))

        # Check fallback
        if self.enable_fallback and key in self._fallback_store:
            if key in self._fallback_ttl and time.time() < self._fallback_ttl[key]:
                return self._fallback_store[key]
            elif key not in self._fallback_ttl:
                return self._fallback_store[key]

        return None

    def get_stats(self) -> dict[str, Any]:
        """
        Get Redis connection statistics or fallback stats.

        Returns:
            Dictionary with connection and memory stats
        """
        import time

        if self._ensure_connected():
            try:
                info = self.client.info()
                return {
                    "mode": "redis",
                    "connected": True,
                    "used_memory": info.get("used_memory_human", "unknown"),
                    "total_keys": self.client.dbsize(),
                    "uptime_days": info.get("uptime_in_days", 0),
                }
            except Exception as e:
                pass

        # Fallback stats
        if self.enable_fallback:
            active_keys = sum(1 for k, ttl_time in self._fallback_ttl.items()
                             if time.time() < ttl_time)
            return {
                "mode": "fallback",
                "connected": False,
                "fallback_active": True,
                "fallback_keys": len(self._fallback_store),
                "fallback_active_keys": active_keys
            }

        return {"mode": "disconnected", "connected": False}

    # =========================================================================
    # IR Cache Methods - ApplicationIR caching with long TTL
    # =========================================================================

    def cache_ir(
        self,
        cache_key: str,
        ir_data: dict[str, Any],
        ttl: int = IR_CACHE_TTL
    ) -> bool:
        """
        Cache ApplicationIR data for a spec.

        Uses SCAN-safe key pattern: ir_cache:{cache_key}

        Args:
            cache_key: Unique cache key (e.g., "spec_name_hash8")
            ir_data: Serialized ApplicationIR dict
            ttl: TTL in seconds (default 7 days)

        Returns:
            True if successful
        """
        import time

        key = f"ir_cache:{cache_key}"

        # Try Redis first
        if self._ensure_connected():
            try:
                data_json = json.dumps(ir_data, default=str)
                self.client.setex(key, ttl, data_json)
                self.logger.info("Cached IR to Redis",
                               cache_key=cache_key,
                               ttl_days=ttl // 86400)
                return True
            except Exception as e:
                self.logger.warning("Failed to cache IR in Redis",
                                  cache_key=cache_key,
                                  error=str(e))

        # Fallback storage
        if self.enable_fallback:
            self._fallback_store[key] = ir_data
            self._fallback_ttl[key] = time.time() + ttl
            self.logger.debug("Cached IR to fallback storage", cache_key=cache_key)
            return True

        return False

    def get_cached_ir(self, cache_key: str) -> Optional[dict[str, Any]]:
        """
        Retrieve cached ApplicationIR data.

        Args:
            cache_key: Cache key used when storing

        Returns:
            IR data dict if found, None otherwise
        """
        import time

        key = f"ir_cache:{cache_key}"

        # Try Redis first
        if self._ensure_connected():
            try:
                data_json = self.client.get(key)
                if data_json:
                    self.logger.debug("IR cache hit from Redis", cache_key=cache_key)
                    return json.loads(data_json)
            except Exception as e:
                self.logger.warning("Failed to retrieve IR from Redis",
                                  cache_key=cache_key,
                                  error=str(e))

        # Check fallback
        if self.enable_fallback and key in self._fallback_store:
            if key in self._fallback_ttl and time.time() < self._fallback_ttl[key]:
                self.logger.debug("IR cache hit from fallback", cache_key=cache_key)
                return self._fallback_store[key]
            elif key not in self._fallback_ttl:
                return self._fallback_store[key]
            else:
                # Expired, clean up
                del self._fallback_store[key]
                if key in self._fallback_ttl:
                    del self._fallback_ttl[key]

        return None

    def clear_ir_cache(self, spec_name: Optional[str] = None) -> int:
        """
        Clear IR cache entries using SCAN (non-blocking).

        FLUSH STRATEGY:
        - Uses SCAN instead of KEYS to avoid blocking Redis in production
        - Iterates in batches of 100 keys
        - Safe for large datasets

        Args:
            spec_name: If provided, only clear cache for this spec.
                      If None, clear ALL IR cache entries.

        Returns:
            Number of keys deleted
        """
        import time

        pattern = f"ir_cache:{spec_name}_*" if spec_name else "ir_cache:*"
        deleted_count = 0

        # Clear from Redis using SCAN (non-blocking)
        if self._ensure_connected():
            try:
                cursor = 0
                while True:
                    cursor, keys = self.client.scan(cursor=cursor, match=pattern, count=100)
                    if keys:
                        deleted_count += self.client.delete(*keys)
                    if cursor == 0:
                        break
                self.logger.info("Cleared IR cache from Redis",
                               pattern=pattern,
                               deleted=deleted_count)
            except Exception as e:
                self.logger.warning("Failed to clear IR cache from Redis",
                                  error=str(e))

        # Clear from fallback storage
        if self.enable_fallback:
            fallback_pattern = f"ir_cache:{spec_name}_" if spec_name else "ir_cache:"
            keys_to_delete = [k for k in self._fallback_store.keys()
                            if k.startswith(fallback_pattern)]
            for key in keys_to_delete:
                del self._fallback_store[key]
                if key in self._fallback_ttl:
                    del self._fallback_ttl[key]
                deleted_count += 1
            if keys_to_delete:
                self.logger.debug("Cleared IR cache from fallback",
                                pattern=pattern,
                                deleted=len(keys_to_delete))

        return deleted_count

    def get_ir_cache_stats(self) -> dict[str, Any]:
        """
        Get statistics about IR cache usage.

        Returns:
            Dict with cache stats (count, keys, memory estimate)
        """
        stats = {
            "source": "unknown",
            "ir_cache_keys": 0,
            "keys": [],
            "total_size_estimate_kb": 0
        }

        # Try Redis first
        if self._ensure_connected():
            try:
                cursor = 0
                keys = []
                total_size = 0
                while True:
                    cursor, batch = self.client.scan(cursor=cursor, match="ir_cache:*", count=100)
                    keys.extend(batch)
                    if cursor == 0:
                        break

                # Get memory usage for each key (approximate)
                for key in keys:
                    try:
                        size = self.client.memory_usage(key) or 0
                        total_size += size
                    except:
                        pass

                stats["source"] = "redis"
                stats["ir_cache_keys"] = len(keys)
                stats["keys"] = keys
                stats["total_size_estimate_kb"] = total_size / 1024
                return stats
            except Exception as e:
                self.logger.warning("Failed to get IR cache stats from Redis", error=str(e))

        # Fallback stats
        if self.enable_fallback:
            ir_keys = [k for k in self._fallback_store.keys() if k.startswith("ir_cache:")]
            stats["source"] = "fallback"
            stats["ir_cache_keys"] = len(ir_keys)
            stats["keys"] = ir_keys
            # Rough estimate
            stats["total_size_estimate_kb"] = len(ir_keys) * 50  # ~50KB per IR

        return stats

    def close(self):
        """Close Redis connection and clear fallback storage."""
        if self.client:
            try:
                self.client.close()
            except:
                pass
        self._fallback_store.clear()
        self._fallback_ttl.clear()
