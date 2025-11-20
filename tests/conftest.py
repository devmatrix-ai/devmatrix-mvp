"""
Pytest configuration and shared fixtures for real service testing.
"""

import pytest
import os
from pathlib import Path
from dotenv import load_dotenv
import tempfile
import shutil

# Set test environment variables BEFORE loading dotenv
# These ensure Settings validation passes during test collection
os.environ.setdefault('JWT_SECRET', 'test-secret-key-for-testing-only-minimum-32-characters-required')
os.environ.setdefault('DATABASE_URL', 'postgresql://test:test@localhost:5432/test')
os.environ.setdefault('CORS_ALLOWED_ORIGINS', 'http://localhost:3000,http://localhost:5173')

# Load test environment (override=True ensures .env.test takes precedence)
load_dotenv('.env.test', override=True)

from src.llm.anthropic_client import AnthropicClient
from src.state.postgres_manager import PostgresManager
from src.state.redis_manager import RedisManager
from src.rag import create_embedding_model, create_vector_store, create_retriever
from src.tools.workspace_manager import WorkspaceManager
from src.config.database import DatabaseConfig, TEST_DATABASE_URL


@pytest.fixture(scope="function")
def db_session():
    """
    Create a test database session with SQLite in-memory.
    All tables are created fresh for each test and dropped after.
    """
    # Use SQLite in-memory for tests
    engine = DatabaseConfig.get_engine(url=TEST_DATABASE_URL, echo=False)
    SessionLocal = DatabaseConfig.get_session_factory()

    # Import all models to register them
    import src.models.user  # noqa
    import src.models.user_quota  # noqa
    import src.models.user_usage  # noqa
    import src.models.conversation  # noqa
    import src.models.message  # noqa
    import src.models.masterplan  # noqa

    # Create all tables
    Base = DatabaseConfig.get_base()
    Base.metadata.create_all(bind=engine)

    # Create session
    session = SessionLocal()

    try:
        yield session
    finally:
        session.close()
        # Drop all tables after test
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="session")
def anthropic_api_key():
    """Get real Anthropic API key from environment."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key or not api_key.startswith("sk-ant-"):
        pytest.skip("ANTHROPIC_API_KEY not configured - skipping real API tests")
    return api_key


@pytest.fixture(scope="session")
def real_anthropic_client(anthropic_api_key):
    """Create real Anthropic client (no mocks)."""
    return AnthropicClient(
        api_key=anthropic_api_key,
        model="claude-3-5-sonnet-20241022",
        enable_cache=False,  # Disable cache for tests to get fresh responses
        enable_retry=True,
        enable_circuit_breaker=False  # Disable for faster test failures
    )


@pytest.fixture(scope="function")
def real_postgres_manager():
    """Create real PostgreSQL manager connected to test database."""
    manager = PostgresManager(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", 5432)),
        database=os.getenv("POSTGRES_DB", "devmatrix_test"),
        user=os.getenv("POSTGRES_USER", "devmatrix"),
        password=os.getenv("POSTGRES_PASSWORD", "devmatrix")
    )

    # Add convenience methods for testing
    def query(sql, params=None):
        return manager._execute(sql, params, fetch=True)

    def execute(sql, params=None):
        return manager._execute(sql, params, fetch=False)

    manager.query = query
    manager.execute = execute

    yield manager

    # Cleanup: truncate test tables after each test
    try:
        manager._execute("TRUNCATE TABLE code_generation_logs CASCADE")
        manager._execute("TRUNCATE TABLE agent_execution_logs CASCADE")
        manager._execute("TRUNCATE TABLE workflow_logs CASCADE")
        manager._execute("TRUNCATE TABLE rag_feedback CASCADE")
    except Exception as e:
        print(f"Warning: Cleanup failed: {e}")


@pytest.fixture(scope="function")
def real_redis_manager():
    """Create real Redis manager."""
    manager = RedisManager(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", 6379)),
        db=0
    )

    # Add convenience methods for testing that wrap workflow methods
    def set(key, value):
        """Convenience method for tests - wraps save_workflow_state."""
        return manager.save_workflow_state(key.replace("test:", ""), value)

    def get(key):
        """Convenience method for tests - wraps get_workflow_state."""
        return manager.get_workflow_state(key.replace("test:", ""))

    manager.set = set
    manager.get = get

    yield manager

    # Cleanup: flush test keys
    try:
        if manager._ensure_connected():
            # Only delete keys with test prefix
            for key in manager.client.scan_iter(match="workflow:*"):
                manager.client.delete(key)
        # Also clean fallback storage
        manager._fallback_store.clear()
        manager._fallback_ttl.clear()
    except Exception as e:
        print(f"Warning: Redis cleanup failed: {e}")


@pytest.fixture(scope="function")
def real_rag_system():
    """Create real RAG system with ChromaDB."""
    from src.rag.vector_store import VectorStore

    embedding_model = create_embedding_model()

    # Use unique collection for each test
    import time
    test_collection = f"test_{int(time.time() * 1000)}"

    # Create VectorStore directly with collection_name parameter
    vector_store = VectorStore(
        embedding_model=embedding_model,
        host=os.getenv("CHROMADB_HOST", "localhost"),
        port=int(os.getenv("CHROMADB_PORT", 8001)),
        collection_name=test_collection
    )
    retriever = create_retriever(vector_store)

    yield {
        "embedding_model": embedding_model,
        "vector_store": vector_store,
        "retriever": retriever
    }

    # Cleanup: delete test collection
    try:
        vector_store.clear_collection()
    except Exception as e:
        print(f"Warning: ChromaDB cleanup failed: {e}")


@pytest.fixture(scope="function")
def real_workspace():
    """Create real temporary workspace with git."""
    # Create temporary directory
    temp_dir = tempfile.mkdtemp(prefix="devmatrix_test_")
    workspace_path = Path(temp_dir)

    # Initialize git
    import subprocess
    subprocess.run(
        ["git", "init"],
        cwd=workspace_path,
        check=True,
        capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.name", "DevMatrix Test"],
        cwd=workspace_path,
        check=True,
        capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.email", "test@devmatrix.local"],
        cwd=workspace_path,
        check=True,
        capture_output=True
    )

    # Create initial commit
    gitkeep = workspace_path / ".gitkeep"
    gitkeep.touch()
    subprocess.run(
        ["git", "add", ".gitkeep"],
        cwd=workspace_path,
        check=True,
        capture_output=True
    )
    subprocess.run(
        ["git", "commit", "-m", "chore: init test workspace"],
        cwd=workspace_path,
        check=True,
        capture_output=True
    )

    yield workspace_path

    # Cleanup: remove temporary directory
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture(scope="function")
def real_workspace_manager(real_workspace):
    """Create WorkspaceManager with real git-enabled workspace."""
    # WorkspaceManager doesn't support custom base_path
    # Instead, we create a manager and manually set its base_path
    # This is only for testing purposes
    import tempfile
    workspace_id = Path(tempfile.gettempdir()).name + "_" + real_workspace.name

    manager = WorkspaceManager(
        workspace_id=workspace_id,
        auto_cleanup=False  # We handle cleanup in fixture
    )

    # Override base_path to use our git-initialized workspace
    manager.base_path = real_workspace
    manager._created = True  # Mark as already created

    return manager


# Legacy fixtures for backward compatibility
@pytest.fixture
def test_project_id():
    """Generate a unique project ID for testing."""
    from uuid import uuid4
    return uuid4()


@pytest.fixture
def test_task_id():
    """Generate a unique task ID for testing."""
    from uuid import uuid4
    return uuid4()


@pytest.fixture
def test_workflow_id():
    """Generate a unique workflow ID for testing."""
    from uuid import uuid4
    return str(uuid4())


@pytest.fixture
def sample_workflow_state():
    """Sample workflow state for testing."""
    from uuid import uuid4
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


# Session-scoped markers
def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "real_api: marks tests that use real Anthropic API (may be slow and cost money)"
    )
    config.addinivalue_line(
        "markers", "real_services: marks tests that require real PostgreSQL, Redis, ChromaDB"
    )
    config.addinivalue_line(
        "markers", "e2e: marks end-to-end tests with full workflow"
    )
    config.addinivalue_line(
        "markers", "unit: marks unit tests (fast, no external dependencies)"
    )
    config.addinivalue_line(
        "markers", "integration: marks integration tests (require services)"
    )
    config.addinivalue_line(
        "markers", "security: marks security penetration tests"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests that take >30 seconds"
    )
    config.addinivalue_line(
        "markers", "smoke: marks quick smoke tests"
    )
