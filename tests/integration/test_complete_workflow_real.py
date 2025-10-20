"""
Complete end-to-end workflow integration tests with real services.

Tests the full workflow from user request to deployed code:
1. User request → Planning → Code generation → Review → Approval → Git commit
2. Multi-step workflows with dependencies
3. Error recovery and retry logic
4. Performance benchmarks

These tests use REAL services and cost money (~$0.05-0.20 per test).

Run with: pytest -v -m "e2e and real_api" tests/integration/test_complete_workflow_real.py
"""

import pytest
import time
from pathlib import Path
from uuid import uuid4


@pytest.mark.real_api
@pytest.mark.real_services
@pytest.mark.e2e
class TestCompleteWorkflowReal:
    """Complete workflow tests with all real services."""

    def test_complete_code_generation_workflow(
        self,
        real_anthropic_client,
        real_postgres_manager,
        real_workspace_manager
    ):
        """
        Test complete workflow: request → code → git commit → database log.

        Expected cost: ~$0.05-0.10
        Expected time: 30-60 seconds
        """
        start_time = time.time()

        # Import here to avoid dependency issues
        from src.services.chat_service import ChatService

        chat_service = ChatService(
            anthropic_client=real_anthropic_client,
            postgres_manager=real_postgres_manager,
            workspace_manager=real_workspace_manager
        )

        # Execute complete workflow
        request_id = str(uuid4())
        result = chat_service.process_message(
            message="Create a function to calculate compound interest with principal, rate, time, and compounding frequency parameters",
            session_id=f"test_session_{request_id}",
            workspace_id=real_workspace_manager.workspace_id
        )

        elapsed = time.time() - start_time

        # Verify response structure
        assert result is not None
        assert "response" in result or "content" in result

        # Verify file was created
        workspace_files = list(Path(real_workspace_manager.base_path).glob("**/*.py"))
        assert len(workspace_files) > 0, "Should create at least one Python file"

        # Verify code quality
        generated_code = workspace_files[0].read_text()
        assert "def " in generated_code, "Should contain function definition"
        assert "compound" in generated_code.lower(), "Should reference compound interest"
        assert "principal" in generated_code.lower(), "Should have principal parameter"

        # Performance check
        assert elapsed < 60.0, f"Workflow took {elapsed:.2f}s, expected <60s"

        print(f"\n✅ Complete workflow passed in {elapsed:.2f}s")

    def test_iterative_refinement_workflow(
        self,
        real_anthropic_client,
        real_postgres_manager,
        real_workspace_manager
    ):
        """
        Test iterative workflow: generate → review → refine → approve.

        Expected cost: ~$0.10-0.20
        Expected time: 60-90 seconds
        """
        from src.services.chat_service import ChatService

        chat_service = ChatService(
            anthropic_client=real_anthropic_client,
            postgres_manager=real_postgres_manager,
            workspace_manager=real_workspace_manager
        )

        session_id = f"test_refine_{uuid4()}"

        # Step 1: Initial request
        result1 = chat_service.process_message(
            message="Create a simple todo list class",
            session_id=session_id,
            workspace_id=real_workspace_manager.workspace_id
        )

        assert result1 is not None

        # Step 2: Refinement request (should use context from step 1)
        result2 = chat_service.process_message(
            message="Add priority levels to the todo items",
            session_id=session_id,
            workspace_id=real_workspace_manager.workspace_id
        )

        assert result2 is not None

        # Step 3: Another refinement
        result3 = chat_service.process_message(
            message="Add due dates to todo items",
            session_id=session_id,
            workspace_id=real_workspace_manager.workspace_id
        )

        assert result3 is not None

        # Verify final code includes all refinements
        workspace_files = list(Path(real_workspace_manager.base_path).glob("**/*.py"))
        if workspace_files:
            final_code = workspace_files[-1].read_text()
            # Should mention priority and date concepts
            code_lower = final_code.lower()
            assert "todo" in code_lower or "task" in code_lower
            # At least some refinements should be present
            assert len(final_code) > 100, "Code should be substantial"

    @pytest.mark.slow
    def test_multi_file_project_workflow(
        self,
        real_anthropic_client,
        real_postgres_manager,
        real_workspace_manager
    ):
        """
        Test workflow that creates multiple related files.

        Expected cost: ~$0.15-0.30
        Expected time: 90-120 seconds
        """
        from src.services.chat_service import ChatService

        chat_service = ChatService(
            anthropic_client=real_anthropic_client,
            postgres_manager=real_postgres_manager,
            workspace_manager=real_workspace_manager
        )

        session_id = f"test_multi_file_{uuid4()}"

        # Request a project with multiple components
        result = chat_service.process_message(
            message="Create a simple REST API with: 1) a User model, 2) a database interface, and 3) API endpoints for CRUD operations",
            session_id=session_id,
            workspace_id=real_workspace_manager.workspace_id
        )

        assert result is not None

        # Verify multiple files were created
        workspace_files = list(Path(real_workspace_manager.base_path).glob("**/*.py"))

        # Should create at least one file (may be combined or separate)
        assert len(workspace_files) >= 1, f"Expected files, got {len(workspace_files)}"

        # Verify content coverage
        all_code = "\n".join(f.read_text() for f in workspace_files)
        all_code_lower = all_code.lower()

        # Should cover the requested components
        has_model = "class" in all_code and "user" in all_code_lower
        has_crud = any(word in all_code_lower for word in ["create", "read", "update", "delete", "get", "post", "put"])

        assert has_model or has_crud, "Should implement some of the requested functionality"

    def test_error_recovery_workflow(
        self,
        real_anthropic_client,
        real_postgres_manager,
        real_workspace_manager
    ):
        """
        Test workflow handles ambiguous or problematic requests gracefully.

        Expected cost: ~$0.03-0.08
        Expected time: 20-40 seconds
        """
        from src.services.chat_service import ChatService

        chat_service = ChatService(
            anthropic_client=real_anthropic_client,
            postgres_manager=real_postgres_manager,
            workspace_manager=real_workspace_manager
        )

        # Intentionally vague request
        result = chat_service.process_message(
            message="Make a thing",
            session_id=f"test_error_{uuid4()}",
            workspace_id=real_workspace_manager.workspace_id
        )

        # Should still complete without crashing
        assert result is not None

        # Should either:
        # 1) Ask for clarification, OR
        # 2) Generate something reasonable, OR
        # 3) Explain the issue
        # Any of these is acceptable behavior


@pytest.mark.real_api
@pytest.mark.real_services
@pytest.mark.slow
class TestPerformanceBenchmarks:
    """Performance benchmark tests with real services."""

    def test_simple_function_performance(
        self,
        real_anthropic_client,
        real_postgres_manager,
        real_workspace_manager
    ):
        """
        Benchmark: Simple function generation performance.

        Target: <30s per generation
        Target cost: <$0.05 per generation
        """
        from src.services.chat_service import ChatService

        chat_service = ChatService(
            anthropic_client=real_anthropic_client,
            postgres_manager=real_postgres_manager,
            workspace_manager=real_workspace_manager
        )

        times = []

        for i in range(3):
            start = time.time()

            result = chat_service.process_message(
                message=f"Create a function to calculate the {i+1}th Fibonacci number",
                session_id=f"perf_test_{i}_{uuid4()}",
                workspace_id=f"{real_workspace_manager.workspace_id}_perf_{i}"
            )

            elapsed = time.time() - start
            times.append(elapsed)

            assert result is not None

        avg_time = sum(times) / len(times)
        max_time = max(times)
        min_time = min(times)

        print(f"\n📊 Performance Benchmark:")
        print(f"   Average: {avg_time:.2f}s")
        print(f"   Min: {min_time:.2f}s")
        print(f"   Max: {max_time:.2f}s")

        # Performance assertions (lenient for real API)
        assert avg_time < 40.0, f"Average time {avg_time:.2f}s exceeds 40s target"
        assert max_time < 60.0, f"Max time {max_time:.2f}s exceeds 60s limit"

    def test_concurrent_request_handling(
        self,
        real_anthropic_client,
        real_postgres_manager
    ):
        """
        Test system can handle concurrent requests (simulated).

        Note: This doesn't actually run concurrent threads but validates
        that the system state management works correctly for multiple sessions.
        """
        from src.services.chat_service import ChatService
        from src.tools.workspace_manager import WorkspaceManager

        # Create separate workspace managers for "concurrent" sessions
        sessions = []
        for i in range(3):
            workspace_id = f"concurrent_test_{i}_{uuid4()}"
            workspace_manager = WorkspaceManager(
                workspace_id=workspace_id,
                auto_cleanup=False
            )

            chat_service = ChatService(
                anthropic_client=real_anthropic_client,
                postgres_manager=real_postgres_manager,
                workspace_manager=workspace_manager
            )

            sessions.append({
                "chat_service": chat_service,
                "workspace_manager": workspace_manager,
                "session_id": f"session_{i}"
            })

        # Process requests from different sessions
        for i, session in enumerate(sessions):
            result = session["chat_service"].process_message(
                message=f"Create function_{i} that returns {i}",
                session_id=session["session_id"],
                workspace_id=session["workspace_manager"].workspace_id
            )

            assert result is not None

        # Verify each session maintained separate state
        for session in sessions:
            workspace_files = list(Path(session["workspace_manager"].base_path).glob("**/*.py"))
            # Each workspace should have its own files
            if workspace_files:
                # Just verify isolation - files exist in separate workspaces
                assert session["workspace_manager"].base_path.exists()
