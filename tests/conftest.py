"""
Pytest configuration and fixtures for Devmatrix tests.
"""

import os
import pytest
from uuid import uuid4

# Set test environment variables
os.environ["POSTGRES_HOST"] = "localhost"
os.environ["POSTGRES_PORT"] = "5432"
os.environ["POSTGRES_DB"] = "devmatrix"
os.environ["POSTGRES_USER"] = "devmatrix"
os.environ["POSTGRES_PASSWORD"] = "devmatrix"
os.environ["REDIS_HOST"] = "localhost"
os.environ["REDIS_PORT"] = "6379"


@pytest.fixture
def test_project_id():
    """Generate a unique project ID for testing."""
    return uuid4()


@pytest.fixture
def test_task_id():
    """Generate a unique task ID for testing."""
    return uuid4()


@pytest.fixture
def test_workflow_id():
    """Generate a unique workflow ID for testing."""
    return str(uuid4())


@pytest.fixture
def sample_workflow_state():
    """Sample workflow state for testing."""
    return {
        "user_request": "Test request",
        "messages": [],
        "current_task": "testing",
        "generated_code": "",
        "workflow_id": str(uuid4()),
        "project_id": str(uuid4()),
        "agent_name": "test_agent",
        "error": None,
        "retry_count": 0,
        "task_id": "",
    }


@pytest.fixture
def sample_task_input():
    """Sample task input data for testing."""
    return {
        "user_request": "Create a test function",
        "context": "Unit testing",
    }


@pytest.fixture
def sample_task_output():
    """Sample task output data for testing."""
    return {
        "message": {"role": "assistant", "content": "Task completed"},
        "generated_code": "def test(): pass",
    }
