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

# Load environment variables
load_dotenv()


class RedisManager:
    """
    Manages workflow state in Redis.

    Usage:
        manager = RedisManager()
        manager.save_workflow_state(workflow_id, state_dict)
        state = manager.get_workflow_state(workflow_id)
    """

    def __init__(
        self,
        host: str = None,
        port: int = None,
        db: int = 0,
        default_ttl: int = 1800,  # 30 minutes
    ):
        """
        Initialize Redis connection.

        Args:
            host: Redis host (defaults to env REDIS_HOST or localhost)
            port: Redis port (defaults to env REDIS_PORT or 6379)
            db: Redis database number
            default_ttl: Default TTL in seconds (30 min)
        """
        self.host = host or os.getenv("REDIS_HOST", "localhost")
        self.port = int(port or os.getenv("REDIS_PORT", 6379))
        self.db = db
        self.default_ttl = default_ttl

        # Create Redis client
        self.client = redis.Redis(
            host=self.host,
            port=self.port,
            db=self.db,
            decode_responses=True,  # Auto-decode bytes to strings
        )

        # Test connection
        try:
            self.client.ping()
        except redis.ConnectionError as e:
            raise ConnectionError(
                f"Failed to connect to Redis at {self.host}:{self.port}"
            ) from e

    def save_workflow_state(
        self, workflow_id: str, state: dict[str, Any], ttl: int = None
    ) -> bool:
        """
        Save workflow state to Redis.

        Args:
            workflow_id: Unique workflow identifier
            state: State dictionary to save
            ttl: Time-to-live in seconds (uses default if not provided)

        Returns:
            True if successful, False otherwise
        """
        key = f"workflow:{workflow_id}"
        ttl = ttl or self.default_ttl

        try:
            # Serialize state to JSON
            state_json = json.dumps(state)

            # Save with TTL
            self.client.setex(key, ttl, state_json)
            return True

        except Exception as e:
            print(f"Error saving workflow state: {e}")
            return False

    def get_workflow_state(self, workflow_id: str) -> Optional[dict[str, Any]]:
        """
        Retrieve workflow state from Redis.

        Args:
            workflow_id: Unique workflow identifier

        Returns:
            State dictionary if found, None otherwise
        """
        key = f"workflow:{workflow_id}"

        try:
            state_json = self.client.get(key)

            if state_json is None:
                return None

            # Deserialize from JSON
            return json.loads(state_json)

        except Exception as e:
            print(f"Error retrieving workflow state: {e}")
            return None

    def extend_workflow_ttl(self, workflow_id: str, additional_seconds: int) -> bool:
        """
        Extend the TTL of a workflow state.

        Useful for long-running workflows.

        Args:
            workflow_id: Unique workflow identifier
            additional_seconds: Seconds to add to current TTL

        Returns:
            True if successful, False otherwise
        """
        key = f"workflow:{workflow_id}"

        try:
            # Get current TTL
            current_ttl = self.client.ttl(key)

            if current_ttl == -2:  # Key doesn't exist
                return False

            # Extend TTL
            new_ttl = max(current_ttl, 0) + additional_seconds
            self.client.expire(key, new_ttl)
            return True

        except Exception as e:
            print(f"Error extending workflow TTL: {e}")
            return False

    def delete_workflow_state(self, workflow_id: str) -> bool:
        """
        Delete workflow state from Redis.

        Args:
            workflow_id: Unique workflow identifier

        Returns:
            True if deleted, False if not found or error
        """
        key = f"workflow:{workflow_id}"

        try:
            deleted = self.client.delete(key)
            return deleted > 0

        except Exception as e:
            print(f"Error deleting workflow state: {e}")
            return False

    def cache_llm_response(
        self, prompt_hash: str, response: str, ttl: int = 3600
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
        key = f"llm_cache:{prompt_hash}"

        try:
            self.client.setex(key, ttl, response)
            return True

        except Exception as e:
            print(f"Error caching LLM response: {e}")
            return False

    def get_cached_llm_response(self, prompt_hash: str) -> Optional[str]:
        """
        Retrieve cached LLM response.

        Args:
            prompt_hash: Hash of the prompt

        Returns:
            Cached response if found, None otherwise
        """
        key = f"llm_cache:{prompt_hash}"

        try:
            return self.client.get(key)

        except Exception as e:
            print(f"Error retrieving cached LLM response: {e}")
            return None

    def get_stats(self) -> dict[str, Any]:
        """
        Get Redis connection statistics.

        Returns:
            Dictionary with connection and memory stats
        """
        try:
            info = self.client.info()
            return {
                "connected": True,
                "used_memory": info.get("used_memory_human", "unknown"),
                "total_keys": self.client.dbsize(),
                "uptime_days": info.get("uptime_in_days", 0),
            }

        except Exception as e:
            return {"connected": False, "error": str(e)}

    def close(self):
        """Close Redis connection."""
        if self.client:
            self.client.close()
