"""
Unit tests for RedisManager.
"""

import pytest
from uuid import uuid4
from src.state.redis_manager import RedisManager


class TestRedisManager:
    """Test RedisManager functionality."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup Redis manager for each test."""
        self.redis = RedisManager()
        yield
        # Cleanup after each test
        self.redis.close()

    def test_connection(self):
        """Test Redis connection."""
        stats = self.redis.get_stats()
        assert stats["connected"] is True
        assert "used_memory" in stats
        assert "total_keys" in stats

    def test_save_and_get_workflow_state(self, test_workflow_id, sample_workflow_state):
        """Test saving and retrieving workflow state."""
        # Save state
        success = self.redis.save_workflow_state(test_workflow_id, sample_workflow_state)
        assert success is True

        # Retrieve state
        retrieved_state = self.redis.get_workflow_state(test_workflow_id)
        assert retrieved_state is not None
        assert retrieved_state["user_request"] == sample_workflow_state["user_request"]
        assert retrieved_state["workflow_id"] == sample_workflow_state["workflow_id"]
        assert retrieved_state["current_task"] == sample_workflow_state["current_task"]

    def test_get_nonexistent_workflow(self):
        """Test retrieving non-existent workflow state."""
        nonexistent_id = str(uuid4())
        state = self.redis.get_workflow_state(nonexistent_id)
        assert state is None

    def test_delete_workflow_state(self, test_workflow_id, sample_workflow_state):
        """Test deleting workflow state."""
        # Save state
        self.redis.save_workflow_state(test_workflow_id, sample_workflow_state)

        # Verify it exists
        state = self.redis.get_workflow_state(test_workflow_id)
        assert state is not None

        # Delete it
        deleted = self.redis.delete_workflow_state(test_workflow_id)
        assert deleted is True

        # Verify it's gone
        state = self.redis.get_workflow_state(test_workflow_id)
        assert state is None

    def test_extend_workflow_ttl(self, test_workflow_id, sample_workflow_state):
        """Test extending workflow TTL."""
        # Save state with default TTL
        self.redis.save_workflow_state(test_workflow_id, sample_workflow_state)

        # Extend TTL
        extended = self.redis.extend_workflow_ttl(test_workflow_id, 3600)
        assert extended is True

    def test_cache_llm_response(self):
        """Test LLM response caching."""
        prompt_hash = "test_prompt_hash_123"
        response = "This is a cached LLM response"

        # Cache response
        cached = self.redis.cache_llm_response(prompt_hash, response)
        assert cached is True

        # Retrieve cached response
        retrieved = self.redis.get_cached_llm_response(prompt_hash)
        assert retrieved == response

    def test_get_nonexistent_cache(self):
        """Test retrieving non-existent cached response."""
        response = self.redis.get_cached_llm_response("nonexistent_hash")
        assert response is None
