"""
Unit tests for ParallelExecutor
"""

import pytest
import time
from unittest.mock import Mock, patch
from src.agents.parallel_executor import ParallelExecutor


class TestParallelExecutor:
    """Test suite for ParallelExecutor."""

    @pytest.fixture
    def executor(self):
        """Create executor with default settings."""
        return ParallelExecutor(max_workers=4)

    @pytest.fixture
    def mock_executor_func(self):
        """Create mock executor function."""
        def func(task, context):
            # Simulate some work
            time.sleep(0.01)
            return {
                "success": True,
                "output": f"Task {task['id']} completed",
                "error": None
            }
        return func

    def test_init(self, executor):
        """Test executor initialization."""
        assert executor.max_workers == 4
        assert executor.execution_stats["total_tasks"] == 0
        assert executor.execution_stats["successful"] == 0
        assert executor.execution_stats["failed"] == 0
        assert executor.execution_stats["skipped"] == 0
        assert executor.execution_stats["total_time"] == 0.0
        assert executor.execution_stats["parallel_time_saved"] == 0.0

    def test_init_custom_workers(self):
        """Test executor with custom worker count."""
        executor = ParallelExecutor(max_workers=8)
        assert executor.max_workers == 8

    def test_build_dependency_graph_simple(self, executor):
        """Test building simple dependency graph."""
        tasks = [
            {"id": "task_1", "dependencies": []},
            {"id": "task_2", "dependencies": ["task_1"]},
            {"id": "task_3", "dependencies": ["task_2"]}
        ]

        graph = executor._build_dependency_graph(tasks)

        assert graph["task_1"] == set()
        assert graph["task_2"] == {"task_1"}
        assert graph["task_3"] == {"task_2"}

    def test_build_dependency_graph_complex(self, executor):
        """Test building complex dependency graph."""
        tasks = [
            {"id": "task_1", "dependencies": []},
            {"id": "task_2", "dependencies": []},
            {"id": "task_3", "dependencies": ["task_1", "task_2"]},
            {"id": "task_4", "dependencies": ["task_3"]}
        ]

        graph = executor._build_dependency_graph(tasks)

        assert graph["task_1"] == set()
        assert graph["task_2"] == set()
        assert graph["task_3"] == {"task_1", "task_2"}
        assert graph["task_4"] == {"task_3"}

    def test_identify_waves_all_independent(self, executor):
        """Test wave identification with all independent tasks."""
        tasks = [
            {"id": "task_1", "dependencies": []},
            {"id": "task_2", "dependencies": []},
            {"id": "task_3", "dependencies": []}
        ]

        dependency_graph = executor._build_dependency_graph(tasks)
        waves = executor._identify_waves(tasks, dependency_graph)

        # All tasks should be in one wave
        assert len(waves) == 1
        assert len(waves[0]) == 3
        assert {t["id"] for t in waves[0]} == {"task_1", "task_2", "task_3"}

    def test_identify_waves_sequential(self, executor):
        """Test wave identification with sequential tasks."""
        tasks = [
            {"id": "task_1", "dependencies": []},
            {"id": "task_2", "dependencies": ["task_1"]},
            {"id": "task_3", "dependencies": ["task_2"]}
        ]

        dependency_graph = executor._build_dependency_graph(tasks)
        waves = executor._identify_waves(tasks, dependency_graph)

        # Each task should be in separate wave
        assert len(waves) == 3
        assert waves[0][0]["id"] == "task_1"
        assert waves[1][0]["id"] == "task_2"
        assert waves[2][0]["id"] == "task_3"

    def test_identify_waves_mixed(self, executor):
        """Test wave identification with mixed dependencies."""
        tasks = [
            {"id": "task_1", "dependencies": []},
            {"id": "task_2", "dependencies": []},
            {"id": "task_3", "dependencies": ["task_1", "task_2"]},
            {"id": "task_4", "dependencies": ["task_3"]},
            {"id": "task_5", "dependencies": ["task_3"]}
        ]

        dependency_graph = executor._build_dependency_graph(tasks)
        waves = executor._identify_waves(tasks, dependency_graph)

        # Wave 1: task_1, task_2 (independent)
        # Wave 2: task_3 (depends on task_1, task_2)
        # Wave 3: task_4, task_5 (both depend on task_3, independent of each other)
        assert len(waves) == 3
        assert len(waves[0]) == 2  # task_1, task_2
        assert len(waves[1]) == 1  # task_3
        assert len(waves[2]) == 2  # task_4, task_5

    def test_identify_waves_circular_dependency(self, executor):
        """Test wave identification detects circular dependencies."""
        tasks = [
            {"id": "task_1", "dependencies": ["task_2"]},
            {"id": "task_2", "dependencies": ["task_1"]}
        ]

        dependency_graph = executor._build_dependency_graph(tasks)

        with pytest.raises(ValueError, match="Circular dependency detected"):
            executor._identify_waves(tasks, dependency_graph)

    def test_execute_wave_single_task(self, executor, mock_executor_func):
        """Test executing wave with single task."""
        wave_tasks = [
            {"id": "task_1", "dependencies": []}
        ]

        context = {"workspace_id": "test"}
        completed_tasks = set()
        failed_tasks = set()

        results = executor._execute_wave(
            wave_tasks,
            mock_executor_func,
            context,
            completed_tasks,
            failed_tasks
        )

        assert "task_1" in results
        assert results["task_1"]["success"] is True
        assert "execution_time" in results["task_1"]

    def test_execute_wave_multiple_tasks(self, executor, mock_executor_func):
        """Test executing wave with multiple independent tasks."""
        wave_tasks = [
            {"id": "task_1", "dependencies": []},
            {"id": "task_2", "dependencies": []},
            {"id": "task_3", "dependencies": []}
        ]

        context = {"workspace_id": "test"}
        completed_tasks = set()
        failed_tasks = set()

        start_time = time.time()
        results = executor._execute_wave(
            wave_tasks,
            mock_executor_func,
            context,
            completed_tasks,
            failed_tasks
        )
        elapsed_time = time.time() - start_time

        # All tasks should complete
        assert len(results) == 3
        assert all(results[f"task_{i}"]["success"] for i in range(1, 4))

        # Parallel execution should be faster than sequential
        # Sequential would be ~0.03s (3 tasks * 0.01s), parallel should be ~0.01s
        assert elapsed_time < 0.025  # Allow some overhead

    def test_execute_wave_skip_failed_dependency(self, executor, mock_executor_func):
        """Test executing wave skips tasks with failed dependencies."""
        wave_tasks = [
            {"id": "task_2", "dependencies": ["task_1"]},
            {"id": "task_3", "dependencies": ["task_1"]}
        ]

        context = {"workspace_id": "test"}
        completed_tasks = set()
        failed_tasks = {"task_1"}  # task_1 failed

        results = executor._execute_wave(
            wave_tasks,
            mock_executor_func,
            context,
            completed_tasks,
            failed_tasks
        )

        # Both tasks should be skipped
        assert results["task_2"]["success"] is False
        assert "Skipped due to failed dependency" in results["task_2"]["error"]
        assert results["task_3"]["success"] is False
        assert "Skipped due to failed dependency" in results["task_3"]["error"]

    def test_execute_wave_exception_handling(self, executor):
        """Test wave execution handles exceptions."""
        def failing_func(task, context):
            raise RuntimeError("Task execution failed")

        wave_tasks = [{"id": "task_1", "dependencies": []}]
        context = {"workspace_id": "test"}
        completed_tasks = set()
        failed_tasks = set()

        results = executor._execute_wave(
            wave_tasks,
            failing_func,
            context,
            completed_tasks,
            failed_tasks
        )

        assert results["task_1"]["success"] is False
        assert "Execution exception: Task execution failed" in results["task_1"]["error"]
        assert "execution_time" in results["task_1"]

    def test_execute_tasks_all_independent(self, executor, mock_executor_func):
        """Test executing all independent tasks."""
        tasks = [
            {"id": "task_1", "dependencies": []},
            {"id": "task_2", "dependencies": []},
            {"id": "task_3", "dependencies": []}
        ]

        context = {"workspace_id": "test"}

        result = executor.execute_tasks(tasks, mock_executor_func, context)

        assert len(result["results"]) == 3
        assert all(result["results"][f"task_{i}"]["success"] for i in range(1, 4))
        assert result["stats"]["total_tasks"] == 3
        assert result["stats"]["successful"] == 3
        assert result["stats"]["failed"] == 0
        assert result["stats"]["skipped"] == 0
        assert result["stats"]["parallel_time_saved"] > 0  # Should save time
        assert len(result["errors"]) == 0
        # Order is non-deterministic in parallel execution, so check set equality
        assert set(result["completed_tasks"]) == {"task_1", "task_2", "task_3"}
        assert result["failed_tasks"] == []

    def test_execute_tasks_sequential(self, executor, mock_executor_func):
        """Test executing sequential tasks."""
        tasks = [
            {"id": "task_1", "dependencies": []},
            {"id": "task_2", "dependencies": ["task_1"]},
            {"id": "task_3", "dependencies": ["task_2"]}
        ]

        context = {"workspace_id": "test"}

        result = executor.execute_tasks(tasks, mock_executor_func, context)

        assert len(result["results"]) == 3
        assert result["stats"]["total_tasks"] == 3
        assert result["stats"]["successful"] == 3
        assert result["stats"]["failed"] == 0
        assert result["stats"]["parallel_time_saved"] == 0  # No parallel execution

    def test_execute_tasks_mixed(self, executor, mock_executor_func):
        """Test executing mixed dependency tasks."""
        tasks = [
            {"id": "task_1", "dependencies": []},
            {"id": "task_2", "dependencies": []},
            {"id": "task_3", "dependencies": ["task_1", "task_2"]},
            {"id": "task_4", "dependencies": ["task_3"]},
            {"id": "task_5", "dependencies": ["task_3"]}
        ]

        context = {"workspace_id": "test"}

        result = executor.execute_tasks(tasks, mock_executor_func, context)

        assert len(result["results"]) == 5
        assert result["stats"]["total_tasks"] == 5
        assert result["stats"]["successful"] == 5
        assert result["stats"]["failed"] == 0
        assert result["stats"]["parallel_time_saved"] > 0  # Wave 1 and Wave 3 have parallelism

    def test_execute_tasks_with_failure(self, executor):
        """Test executing tasks with failures."""
        def selective_failure_func(task, context):
            if task["id"] == "task_2":
                return {
                    "success": False,
                    "output": None,
                    "error": "Simulated failure"
                }
            return {
                "success": True,
                "output": f"Task {task['id']} completed",
                "error": None
            }

        tasks = [
            {"id": "task_1", "dependencies": []},
            {"id": "task_2", "dependencies": []},
            {"id": "task_3", "dependencies": ["task_1", "task_2"]},
            {"id": "task_4", "dependencies": ["task_2"]}
        ]

        context = {"workspace_id": "test"}

        result = executor.execute_tasks(tasks, selective_failure_func, context)

        assert result["results"]["task_1"]["success"] is True
        assert result["results"]["task_2"]["success"] is False
        assert result["results"]["task_3"]["success"] is False  # Skipped
        assert result["results"]["task_4"]["success"] is False  # Skipped
        assert result["stats"]["successful"] == 1  # Only task_1
        assert result["stats"]["failed"] == 1  # task_2
        assert result["stats"]["skipped"] == 2  # task_3, task_4
        assert len(result["errors"]) == 3  # task_2 failure + 2 skipped

    def test_execute_tasks_empty_list(self, executor, mock_executor_func):
        """Test executing empty task list."""
        tasks = []
        context = {"workspace_id": "test"}

        result = executor.execute_tasks(tasks, mock_executor_func, context)

        assert len(result["results"]) == 0
        assert result["stats"]["total_tasks"] == 0
        assert result["stats"]["successful"] == 0

    def test_get_stats(self, executor):
        """Test getting execution statistics."""
        stats = executor.get_stats()

        assert "total_tasks" in stats
        assert "successful" in stats
        assert "failed" in stats
        assert "skipped" in stats
        assert "total_time" in stats
        assert "parallel_time_saved" in stats

    def test_reset_stats(self, executor):
        """Test resetting execution statistics."""
        # Modify stats
        executor.execution_stats["total_tasks"] = 10
        executor.execution_stats["successful"] = 8

        # Reset
        executor.reset_stats()

        assert executor.execution_stats["total_tasks"] == 0
        assert executor.execution_stats["successful"] == 0
        assert executor.execution_stats["failed"] == 0
        assert executor.execution_stats["skipped"] == 0
        assert executor.execution_stats["total_time"] == 0.0
        assert executor.execution_stats["parallel_time_saved"] == 0.0

    def test_repr(self, executor):
        """Test string representation."""
        repr_str = repr(executor)

        assert "ParallelExecutor" in repr_str
        assert "max_workers=4" in repr_str

    def test_parallel_time_savings_calculation(self, executor, mock_executor_func):
        """Test parallel time savings calculation."""
        # 3 independent tasks that take ~0.01s each
        tasks = [
            {"id": "task_1", "dependencies": []},
            {"id": "task_2", "dependencies": []},
            {"id": "task_3", "dependencies": []}
        ]

        context = {"workspace_id": "test"}

        result = executor.execute_tasks(tasks, mock_executor_func, context)

        # Sequential would be ~0.03s, parallel should be ~0.01s
        # Time saved should be approximately 0.02s (allowing for overhead)
        time_saved = result["stats"]["parallel_time_saved"]
        assert time_saved > 0.01  # At least some savings
        assert time_saved < 0.03  # But not more than total sequential time

    def test_execution_time_tracking(self, executor, mock_executor_func):
        """Test execution time tracking per task."""
        tasks = [
            {"id": "task_1", "dependencies": []},
            {"id": "task_2", "dependencies": ["task_1"]}
        ]

        context = {"workspace_id": "test"}

        result = executor.execute_tasks(tasks, mock_executor_func, context)

        # Each task should have execution_time
        assert "execution_time" in result["results"]["task_1"]
        assert "execution_time" in result["results"]["task_2"]
        assert result["results"]["task_1"]["execution_time"] > 0
        assert result["results"]["task_2"]["execution_time"] > 0

    def test_context_propagation(self, executor):
        """Test context is properly propagated to executor function."""
        received_context = None

        def context_capture_func(task, context):
            nonlocal received_context
            received_context = context
            return {"success": True, "output": "ok", "error": None}

        tasks = [{"id": "task_1", "dependencies": []}]
        context = {"workspace_id": "test", "custom_param": "value"}

        executor.execute_tasks(tasks, context_capture_func, context)

        assert received_context is not None
        assert received_context["workspace_id"] == "test"
        assert received_context["custom_param"] == "value"
