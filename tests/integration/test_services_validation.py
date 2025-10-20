"""
Validation tests for real services (no Anthropic API required).

These tests validate that PostgreSQL, Redis, ChromaDB, and Git are working
without calling the Anthropic API.

Run with: pytest -v -m real_services tests/integration/test_services_validation.py
"""

import pytest


@pytest.mark.real_services
@pytest.mark.smoke
class TestServicesValidation:
    """Validate real services without API calls."""

    def test_postgres_connection(self, real_postgres_manager):
        """Test PostgreSQL connection and basic operations."""
        # Test connection
        result = real_postgres_manager.query("SELECT version()")
        assert len(result) == 1
        assert "PostgreSQL" in result[0]["version"]

        # Test pgvector extension
        result = real_postgres_manager.query(
            "SELECT * FROM pg_extension WHERE extname='vector'"
        )
        assert len(result) == 1, "pgvector extension should be installed"


    def test_postgres_tables_exist(self, real_postgres_manager):
        """Test that all required tables exist."""
        tables = [
            "code_generation_logs",
            "agent_execution_logs",
            "workflow_logs",
            "rag_feedback"
        ]

        for table in tables:
            result = real_postgres_manager.query(
                f"SELECT to_regclass('public.{table}')"
            )
            assert result[0]["to_regclass"] is not None, f"Table {table} should exist"


    def test_postgres_insert_and_query(self, real_postgres_manager):
        """Test PostgreSQL insert and query operations."""
        # Insert test data
        real_postgres_manager.execute(
            """
            INSERT INTO code_generation_logs
            (workspace_id, user_request, generated_code, approval_status, quality_score, metadata)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            ("test_ws", "test req", "test code", "pending", 7.5, '{"test": true}')
        )

        # Query back
        result = real_postgres_manager.query(
            "SELECT * FROM code_generation_logs WHERE workspace_id = %s",
            ("test_ws",)
        )

        assert len(result) == 1
        assert result[0]["workspace_id"] == "test_ws"
        assert result[0]["quality_score"] == 7.5


    def test_redis_connection(self, real_redis_manager):
        """Test Redis connection."""
        # Test ping
        pong = real_redis_manager.client.ping()
        assert pong is True


    def test_redis_set_get(self, real_redis_manager):
        """Test Redis SET and GET operations."""
        # Set value
        real_redis_manager.set("test:key1", {"data": "value", "count": 42})

        # Get value
        result = real_redis_manager.get("test:key1")

        assert result is not None
        assert result["data"] == "value"
        assert result["count"] == 42


    def test_redis_expiry(self, real_redis_manager):
        """Test Redis key expiration."""
        import time

        # Set with 1 second TTL
        real_redis_manager.client.setex("test:expire", 1, "temporary")

        # Should exist immediately (decode_responses=True means we get str not bytes)
        assert real_redis_manager.client.get("test:expire") == "temporary"

        # Wait for expiration
        time.sleep(1.1)

        # Should be gone
        assert real_redis_manager.client.get("test:expire") is None


    def test_chromadb_connection(self, real_rag_system):
        """Test ChromaDB connection and collection."""
        vector_store = real_rag_system["vector_store"]

        # Verify empty collection
        count = vector_store.collection.count()
        assert count == 0


    def test_chromadb_indexing(self, real_rag_system):
        """Test ChromaDB indexing and counting."""
        vector_store = real_rag_system["vector_store"]

        # Add examples
        vector_store.add_example("def test1(): pass", {"id": 1})
        vector_store.add_example("def test2(): pass", {"id": 2})
        vector_store.add_example("def test3(): pass", {"id": 3})

        # Verify count
        count = vector_store.collection.count()
        assert count == 3


    def test_chromadb_retrieval(self, real_rag_system):
        """Test ChromaDB similarity search."""
        vector_store = real_rag_system["vector_store"]

        # Index example
        vector_store.add_example(
            "def calculate_sum(a, b): return a + b",
            {"operation": "addition"}
        )

        # Search directly on vector_store (no min_similarity filter)
        results = vector_store.search("sum function", top_k=1)

        assert len(results) == 1
        assert "calculate_sum" in results[0]["code"]
        assert results[0]["similarity"] > 0.3  # Should have some similarity


    def test_git_workspace_initialized(self, real_workspace):
        """Test that git workspace is properly initialized."""
        import subprocess

        # Check git status
        result = subprocess.run(
            ["git", "status"],
            cwd=real_workspace,
            check=True,
            capture_output=True,
            text=True
        )

        assert result.returncode == 0
        assert "On branch" in result.stdout


    def test_git_user_configured(self, real_workspace):
        """Test that git user is configured."""
        import subprocess

        # Check user name
        result = subprocess.run(
            ["git", "config", "user.name"],
            cwd=real_workspace,
            check=True,
            capture_output=True,
            text=True
        )

        assert result.stdout.strip() == "DevMatrix Test"

        # Check user email
        result = subprocess.run(
            ["git", "config", "user.email"],
            cwd=real_workspace,
            check=True,
            capture_output=True,
            text=True
        )

        assert result.stdout.strip() == "test@devmatrix.local"


    def test_git_commit_works(self, real_workspace):
        """Test that git commits work."""
        import subprocess

        # Create file
        test_file = real_workspace / "validation.txt"
        test_file.write_text("validation test")

        # Add and commit
        subprocess.run(
            ["git", "add", "validation.txt"],
            cwd=real_workspace,
            check=True,
            capture_output=True
        )

        result = subprocess.run(
            ["git", "commit", "-m", "test: validation commit"],
            cwd=real_workspace,
            check=True,
            capture_output=True,
            text=True
        )

        assert result.returncode == 0

        # Verify commit exists
        log_result = subprocess.run(
            ["git", "log", "--oneline", "-1"],
            cwd=real_workspace,
            check=True,
            capture_output=True,
            text=True
        )

        assert "test: validation commit" in log_result.stdout


    def test_workspace_manager_creates_files(self, real_workspace_manager):
        """Test WorkspaceManager file creation."""
        # Create file
        file_path = real_workspace_manager.write_file(
            "test.py",
            "def test(): return True"
        )

        # Verify file exists
        from pathlib import Path
        assert Path(file_path).exists()
        assert Path(file_path).read_text() == "def test(): return True"
