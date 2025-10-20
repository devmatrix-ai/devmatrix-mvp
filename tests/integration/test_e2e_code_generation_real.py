"""
End-to-End Tests with REAL Services (No Mocks)

IMPORTANT:
- Uses real Anthropic API (costs money, ~$0.01-0.10 per test)
- Uses real PostgreSQL, Redis, ChromaDB
- Uses real Git operations
- Slower than mocked tests (~30-60 seconds per test)

Run with: pytest -v -m real_api tests/integration/test_e2e_code_generation_real.py
"""

import pytest
import time
from pathlib import Path


@pytest.mark.real_api
@pytest.mark.real_services
@pytest.mark.e2e
class TestE2ERealServices:
    """E2E tests using REAL services (no mocks)."""

    def test_e2e_simple_function_real_api(self, real_anthropic_client, real_workspace):
        """
        E2E: Generate simple function with REAL Anthropic API.

        This test:
        1. Calls real Claude API for code generation
        2. Writes to real filesystem
        3. Verifies file exists and contains expected code

        Expected cost: ~$0.01-0.02
        Expected time: 5-15 seconds
        """
        start_time = time.time()

        # Call real API for code generation
        response = real_anthropic_client.send_message(
            messages=[{
                "role": "user",
                "content": "Write a Python function called 'add' that takes two numbers and returns their sum. Just the function code, no explanation."
            }],
            max_tokens=500
        )

        elapsed = time.time() - start_time

        # Verify response
        assert response is not None
        assert "content" in response
        content = response["content"][0]["text"] if isinstance(response["content"], list) else response["content"]

        # Verify code contains expected elements
        assert "def add" in content, f"Expected 'def add' in code, got: {content[:200]}"
        assert "return" in content

        # Write to workspace
        code_file = real_workspace / "add_function.py"
        code_file.write_text(content)

        # Verify file exists
        assert code_file.exists()
        assert code_file.read_text() == content

        # Performance check
        assert elapsed < 30.0, f"Test took {elapsed:.2f}s, expected <30s"

        print(f"\n✅ Real API test passed in {elapsed:.2f}s")
        if "usage" in response:
            input_tokens = response["usage"].get("input_tokens", 0)
            output_tokens = response["usage"].get("output_tokens", 0)
            cost = input_tokens * 0.000003 + output_tokens * 0.000015
            print(f"   Cost: ~${cost:.4f} (Input: {input_tokens}, Output: {output_tokens})")


    def test_e2e_git_operations_real(self, real_workspace):
        """E2E: Test real git operations in workspace."""
        import subprocess

        # Create a file
        test_file = real_workspace / "test.py"
        test_file.write_text("def test(): pass")

        # Add to git
        subprocess.run(
            ["git", "add", "test.py"],
            cwd=real_workspace,
            check=True,
            capture_output=True
        )

        # Commit
        result = subprocess.run(
            ["git", "commit", "-m", "test: add test function"],
            cwd=real_workspace,
            check=True,
            capture_output=True,
            text=True
        )

        assert result.returncode == 0

        # Verify commit exists
        log_result = subprocess.run(
            ["git", "log", "--oneline"],
            cwd=real_workspace,
            check=True,
            capture_output=True,
            text=True
        )

        assert "test: add test function" in log_result.stdout
        # Should have 2 commits: initial .gitkeep + this test commit
        assert log_result.stdout.count('\n') == 2


    def test_e2e_postgres_logging_real(self, real_postgres_manager):
        """E2E: Test real PostgreSQL logging."""

        # Insert test log
        real_postgres_manager.execute(
            """
            INSERT INTO code_generation_logs
            (workspace_id, user_request, generated_code, approval_status, quality_score, metadata)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            ("test_workspace", "test request", "test code", "approved", 8.5, '{"test": true}')
        )

        # Query back
        result = real_postgres_manager.query(
            "SELECT * FROM code_generation_logs WHERE workspace_id = %s",
            ("test_workspace",)
        )

        assert len(result) == 1
        assert result[0]["user_request"] == "test request"
        assert result[0]["quality_score"] == 8.5
        assert result[0]["approval_status"] == "approved"


    def test_e2e_redis_state_real(self, real_redis_manager):
        """E2E: Test real Redis state management."""

        # Set test state
        real_redis_manager.set("test:workflow:123", {"status": "running", "progress": 0.5})

        # Get state back
        state = real_redis_manager.get("test:workflow:123")

        assert state is not None
        assert state["status"] == "running"
        assert state["progress"] == 0.5

        # Update state
        real_redis_manager.set("test:workflow:123", {"status": "completed", "progress": 1.0})

        # Verify update
        updated_state = real_redis_manager.get("test:workflow:123")
        assert updated_state["status"] == "completed"
        assert updated_state["progress"] == 1.0


    def test_e2e_rag_indexing_and_retrieval_real(self, real_rag_system):
        """E2E: Test RAG system with real ChromaDB."""
        vector_store = real_rag_system["vector_store"]
        retriever = real_rag_system["retriever"]

        # Index example code
        example_code = """
def fibonacci(n: int) -> int:
    '''Calculate fibonacci number with memoization.'''
    cache = {}
    def fib(x):
        if x in cache:
            return cache[x]
        if x <= 1:
            return x
        cache[x] = fib(x-1) + fib(x-2)
        return cache[x]
    return fib(n)
"""

        vector_store.add_example(
            example_code,
            {"language": "python", "pattern": "fibonacci", "uses_memoization": True}
        )

        # Verify indexed
        count = vector_store.count()
        assert count == 1

        # Retrieve similar code
        results = retriever.retrieve("fibonacci function with caching", top_k=1)

        assert len(results) == 1
        assert "fibonacci" in results[0].code
        assert "cache" in results[0].code
        assert results[0].similarity > 0.5


    @pytest.mark.slow
    def test_e2e_full_workflow_real_api(
        self,
        real_anthropic_client,
        real_postgres_manager,
        real_redis_manager,
        real_workspace
    ):
        """
        E2E: Full workflow with all real services.

        Tests complete flow:
        1. API call to Claude
        2. Write to filesystem
        3. Git commit
        4. Log to PostgreSQL
        5. State in Redis

        Expected cost: ~$0.02-0.05
        Expected time: 15-30 seconds
        """
        import subprocess
        start_time = time.time()

        workflow_id = "test_workflow_full"

        # 1. Generate code with real API
        response = real_anthropic_client.send_message(
            messages=[{
                "role": "user",
                "content": "Write a Python function called 'multiply' that takes two numbers and returns their product."
            }],
            max_tokens=300
        )

        code = response["content"][0]["text"] if isinstance(response["content"], list) else response["content"]
        assert "def multiply" in code

        # 2. Write to workspace
        code_file = real_workspace / "multiply.py"
        code_file.write_text(code)
        assert code_file.exists()

        # 3. Git commit
        subprocess.run(["git", "add", "multiply.py"], cwd=real_workspace, check=True, capture_output=True)
        commit_result = subprocess.run(
            ["git", "commit", "-m", "feat: add multiply function"],
            cwd=real_workspace,
            check=True,
            capture_output=True,
            text=True
        )
        assert commit_result.returncode == 0

        # Get commit hash
        hash_result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=real_workspace,
            check=True,
            capture_output=True,
            text=True
        )
        commit_hash = hash_result.stdout.strip()
        assert len(commit_hash) == 40  # SHA-1

        # 4. Log to PostgreSQL
        real_postgres_manager.execute(
            """
            INSERT INTO code_generation_logs
            (workspace_id, user_request, generated_code, approval_status, quality_score, git_committed, git_commit_hash, metadata)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                workflow_id,
                "generate multiply function",
                code,
                "approved",
                9.0,
                True,
                commit_hash,
                '{"test": true}'
            )
        )

        # 5. Set state in Redis
        real_redis_manager.set(f"test:{workflow_id}", {
            "status": "completed",
            "file_path": str(code_file),
            "commit_hash": commit_hash
        })

        # Verify everything
        db_result = real_postgres_manager.query(
            "SELECT * FROM code_generation_logs WHERE workspace_id = %s",
            (workflow_id,)
        )
        assert len(db_result) == 1
        assert db_result[0]["git_commit_hash"] == commit_hash

        redis_state = real_redis_manager.get(f"test:{workflow_id}")
        assert redis_state["status"] == "completed"
        assert redis_state["commit_hash"] == commit_hash

        elapsed = time.time() - start_time
        assert elapsed < 60.0, f"Full workflow took {elapsed:.2f}s, expected <60s"

        print(f"\n✅ Full E2E workflow passed in {elapsed:.2f}s")
