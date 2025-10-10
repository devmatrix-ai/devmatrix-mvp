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

    def test_save_workflow_state_with_custom_ttl(self, test_workflow_id, sample_workflow_state):
        """Test saving workflow state with custom TTL."""
        custom_ttl = 60  # 1 minute
        success = self.redis.save_workflow_state(
            test_workflow_id,
            sample_workflow_state,
            ttl=custom_ttl
        )
        assert success is True

        # Verify state exists
        state = self.redis.get_workflow_state(test_workflow_id)
        assert state is not None

    def test_save_workflow_state_with_complex_data(self, test_workflow_id):
        """Test saving workflow state with complex nested data."""
        complex_state = {
            "user_request": "Complex test",
            "messages": [
                {"role": "user", "content": "Hello", "metadata": {"timestamp": "2025-10-10"}},
                {"role": "assistant", "content": "Hi", "nested": {"deep": {"value": 123}}}
            ],
            "metadata": {
                "tags": ["test", "complex"],
                "config": {"setting1": True, "setting2": 3.14}
            },
            "workflow_id": test_workflow_id,
            "project_id": str(uuid4()),
            "current_task": "testing",
            "generated_code": "",
            "agent_name": "test",
            "error": None,
            "retry_count": 0,
            "task_id": ""
        }

        # Save complex state
        success = self.redis.save_workflow_state(test_workflow_id, complex_state)
        assert success is True

        # Retrieve and verify
        retrieved = self.redis.get_workflow_state(test_workflow_id)
        assert retrieved is not None
        assert retrieved["messages"][1]["nested"]["deep"]["value"] == 123
        assert retrieved["metadata"]["config"]["setting2"] == 3.14

    def test_delete_nonexistent_workflow(self):
        """Test deleting non-existent workflow returns False."""
        nonexistent_id = str(uuid4())
        deleted = self.redis.delete_workflow_state(nonexistent_id)
        assert deleted is False

    def test_extend_ttl_nonexistent_workflow(self):
        """Test extending TTL for non-existent workflow returns False."""
        nonexistent_id = str(uuid4())
        extended = self.redis.extend_workflow_ttl(nonexistent_id, 3600)
        assert extended is False

    def test_cache_llm_response_with_custom_ttl(self):
        """Test caching LLM response with custom TTL."""
        prompt_hash = "custom_ttl_hash"
        response = "Custom TTL response"
        custom_ttl = 120

        cached = self.redis.cache_llm_response(prompt_hash, response, ttl=custom_ttl)
        assert cached is True

        retrieved = self.redis.get_cached_llm_response(prompt_hash)
        assert retrieved == response

    def test_cache_llm_response_overwrite(self):
        """Test overwriting existing cached response."""
        prompt_hash = "overwrite_test"

        # Cache first response
        self.redis.cache_llm_response(prompt_hash, "First response")
        first = self.redis.get_cached_llm_response(prompt_hash)
        assert first == "First response"

        # Overwrite with second response
        self.redis.cache_llm_response(prompt_hash, "Second response")
        second = self.redis.get_cached_llm_response(prompt_hash)
        assert second == "Second response"

    def test_workflow_state_with_empty_messages(self, test_workflow_id):
        """Test saving workflow state with empty messages list."""
        state = {
            "user_request": "Test",
            "messages": [],  # Empty list
            "current_task": "testing",
            "generated_code": "",
            "workflow_id": test_workflow_id,
            "project_id": str(uuid4()),
            "agent_name": "test",
            "error": None,
            "retry_count": 0,
            "task_id": ""
        }

        success = self.redis.save_workflow_state(test_workflow_id, state)
        assert success is True

        retrieved = self.redis.get_workflow_state(test_workflow_id)
        assert retrieved["messages"] == []

    def test_workflow_state_with_error(self, test_workflow_id):
        """Test saving workflow state with error information."""
        state_with_error = {
            "user_request": "Test",
            "messages": [],
            "current_task": "failed",
            "generated_code": "",
            "workflow_id": test_workflow_id,
            "project_id": str(uuid4()),
            "agent_name": "test",
            "error": "Test error message",
            "retry_count": 3,
            "task_id": ""
        }

        success = self.redis.save_workflow_state(test_workflow_id, state_with_error)
        assert success is True

        retrieved = self.redis.get_workflow_state(test_workflow_id)
        assert retrieved["error"] == "Test error message"
        assert retrieved["retry_count"] == 3

    def test_multiple_workflow_states_isolation(self):
        """Test that multiple workflow states don't interfere with each other."""
        workflow_id_1 = str(uuid4())
        workflow_id_2 = str(uuid4())
        workflow_id_3 = str(uuid4())

        state_1 = {"workflow_id": workflow_id_1, "data": "first", "user_request": "1",
                   "messages": [], "current_task": "1", "generated_code": "",
                   "project_id": str(uuid4()), "agent_name": "1", "error": None,
                   "retry_count": 0, "task_id": ""}
        state_2 = {"workflow_id": workflow_id_2, "data": "second", "user_request": "2",
                   "messages": [], "current_task": "2", "generated_code": "",
                   "project_id": str(uuid4()), "agent_name": "2", "error": None,
                   "retry_count": 0, "task_id": ""}
        state_3 = {"workflow_id": workflow_id_3, "data": "third", "user_request": "3",
                   "messages": [], "current_task": "3", "generated_code": "",
                   "project_id": str(uuid4()), "agent_name": "3", "error": None,
                   "retry_count": 0, "task_id": ""}

        # Save all three
        self.redis.save_workflow_state(workflow_id_1, state_1)
        self.redis.save_workflow_state(workflow_id_2, state_2)
        self.redis.save_workflow_state(workflow_id_3, state_3)

        # Verify isolation
        retrieved_1 = self.redis.get_workflow_state(workflow_id_1)
        retrieved_2 = self.redis.get_workflow_state(workflow_id_2)
        retrieved_3 = self.redis.get_workflow_state(workflow_id_3)

        assert retrieved_1["data"] == "first"
        assert retrieved_2["data"] == "second"
        assert retrieved_3["data"] == "third"

    def test_stats_contain_expected_fields(self):
        """Test that stats contain all expected fields."""
        stats = self.redis.get_stats()

        assert "connected" in stats
        assert stats["connected"] is True
        assert "used_memory" in stats
        assert "total_keys" in stats
        assert "uptime_days" in stats
        assert isinstance(stats["total_keys"], int)
        assert stats["total_keys"] >= 0
