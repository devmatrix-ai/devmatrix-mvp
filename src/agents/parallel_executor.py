"""
Parallel Task Executor

Executes independent tasks in parallel using ThreadPoolExecutor.
Handles dependency resolution and error propagation.
"""

from typing import Dict, Any, List, Set, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed, Future
import time
from collections import defaultdict


class ParallelExecutor:
    """
    Executor for parallel task execution with dependency management.

    Features:
    - Identifies independent tasks that can run in parallel
    - Executes tasks in dependency order (topological sort)
    - Handles error propagation between dependent tasks
    - Tracks execution progress and timing
    - Thread-safe execution with configurable pool size

    Usage:
        executor = ParallelExecutor(max_workers=4)

        tasks = [
            {"id": "task_1", "dependencies": [], ...},
            {"id": "task_2", "dependencies": ["task_1"], ...},
            {"id": "task_3", "dependencies": [], ...},
        ]

        results = executor.execute_tasks(tasks, agent_executor_func)
    """

    def __init__(self, max_workers: int = 4):
        """
        Initialize parallel executor.

        Args:
            max_workers: Maximum number of concurrent workers
        """
        self.max_workers = max_workers
        self.execution_stats = {
            "total_tasks": 0,
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "total_time": 0.0,
            "parallel_time_saved": 0.0
        }

    def execute_tasks(
        self,
        tasks: List[Dict[str, Any]],
        executor_func: callable,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute tasks in parallel where possible, respecting dependencies.

        Args:
            tasks: List of task dictionaries with 'id', 'dependencies', etc.
            executor_func: Function to execute each task (agent.execute)
            context: Execution context passed to executor_func

        Returns:
            Dictionary with:
                - results: Dict mapping task_id to execution result
                - stats: Execution statistics
                - errors: List of errors encountered
        """
        start_time = time.time()

        # Build dependency graph
        dependency_graph = self._build_dependency_graph(tasks)

        # Identify execution waves (groups of independent tasks)
        waves = self._identify_waves(tasks, dependency_graph)

        # Execute tasks wave by wave
        all_results = {}
        errors = []
        completed_tasks = set()
        failed_tasks = set()

        for wave_num, wave_tasks in enumerate(waves):
            wave_start = time.time()

            # Execute this wave in parallel
            wave_results = self._execute_wave(
                wave_tasks,
                executor_func,
                context,
                completed_tasks,
                failed_tasks
            )

            # Process wave results
            for task_id, result in wave_results.items():
                all_results[task_id] = result

                if result.get("success"):
                    completed_tasks.add(task_id)
                    self.execution_stats["successful"] += 1
                elif result.get("skipped"):
                    # Skipped tasks are not added to failed_tasks (they're not "failed")
                    # But we track them in stats and errors
                    errors.append({
                        "task_id": task_id,
                        "error": result.get("error", "Unknown error")
                    })
                else:
                    # Actually failed (not skipped)
                    failed_tasks.add(task_id)
                    self.execution_stats["failed"] += 1
                    errors.append({
                        "task_id": task_id,
                        "error": result.get("error", "Unknown error")
                    })

            wave_time = time.time() - wave_start

            # Calculate potential parallel time savings
            if len(wave_tasks) > 1:
                # Estimate sequential time as sum of individual times
                estimated_sequential = sum(
                    all_results[t["id"]].get("execution_time", 0)
                    for t in wave_tasks
                    if t["id"] in all_results
                )
                time_saved = max(0, estimated_sequential - wave_time)
                self.execution_stats["parallel_time_saved"] += time_saved

        total_time = time.time() - start_time
        self.execution_stats["total_time"] = total_time
        self.execution_stats["total_tasks"] = len(tasks)

        return {
            "results": all_results,
            "stats": self.execution_stats.copy(),
            "errors": errors,
            "completed_tasks": list(completed_tasks),
            "failed_tasks": list(failed_tasks)
        }

    def _build_dependency_graph(
        self,
        tasks: List[Dict[str, Any]]
    ) -> Dict[str, Set[str]]:
        """
        Build dependency graph from task list.

        Args:
            tasks: List of task dictionaries

        Returns:
            Dictionary mapping task_id to set of task_ids it depends on
        """
        graph = {}
        for task in tasks:
            task_id = task["id"]
            dependencies = set(task.get("dependencies", []))
            graph[task_id] = dependencies

        return graph

    def _identify_waves(
        self,
        tasks: List[Dict[str, Any]],
        dependency_graph: Dict[str, Set[str]]
    ) -> List[List[Dict[str, Any]]]:
        """
        Identify waves of independent tasks that can run in parallel.

        Uses topological sort to group tasks into waves where:
        - All tasks in a wave have no dependencies on each other
        - All dependencies of tasks in wave N are in waves 0..N-1

        Args:
            tasks: List of task dictionaries
            dependency_graph: Dependency relationships

        Returns:
            List of waves, where each wave is a list of tasks
        """
        waves = []
        task_map = {task["id"]: task for task in tasks}
        remaining_tasks = set(task["id"] for task in tasks)
        completed = set()

        while remaining_tasks:
            # Find tasks with all dependencies completed
            ready_tasks = []
            for task_id in remaining_tasks:
                deps = dependency_graph.get(task_id, set())
                if deps.issubset(completed):
                    ready_tasks.append(task_map[task_id])

            if not ready_tasks:
                # Circular dependency detected
                raise ValueError(
                    f"Circular dependency detected. Remaining tasks: {remaining_tasks}"
                )

            # Add ready tasks as a new wave
            waves.append(ready_tasks)

            # Mark tasks as completed
            for task in ready_tasks:
                completed.add(task["id"])
                remaining_tasks.remove(task["id"])

        return waves

    def _execute_wave(
        self,
        wave_tasks: List[Dict[str, Any]],
        executor_func: callable,
        context: Dict[str, Any],
        completed_tasks: Set[str],
        failed_tasks: Set[str]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Execute a wave of independent tasks in parallel.

        Args:
            wave_tasks: Tasks to execute in this wave
            executor_func: Function to execute each task
            context: Execution context
            completed_tasks: Set of already completed task IDs
            failed_tasks: Set of already failed task IDs

        Returns:
            Dictionary mapping task_id to execution result
        """
        wave_results = {}

        # Check if any dependencies failed
        tasks_to_execute = []
        for task in wave_tasks:
            dependencies = set(task.get("dependencies", []))
            if dependencies.intersection(failed_tasks):
                # Skip task because dependency failed
                wave_results[task["id"]] = {
                    "success": False,
                    "error": "Skipped due to failed dependency",
                    "output": None,
                    "skipped": True
                }
                self.execution_stats["skipped"] += 1
            else:
                tasks_to_execute.append(task)

        # Execute tasks in parallel
        if len(tasks_to_execute) == 1:
            # Single task - execute directly (no thread overhead)
            task = tasks_to_execute[0]
            task_start = time.time()
            try:
                result = executor_func(task, context)
                result["execution_time"] = time.time() - task_start
                wave_results[task["id"]] = result
            except Exception as e:
                # Handle execution exception
                wave_results[task["id"]] = {
                    "success": False,
                    "error": f"Execution exception: {str(e)}",
                    "output": None,
                    "execution_time": time.time() - task_start
                }
        elif tasks_to_execute:
            # Multiple tasks - use thread pool
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit all tasks
                future_to_task = {}
                for task in tasks_to_execute:
                    task_start = time.time()
                    future = executor.submit(executor_func, task, context)
                    future_to_task[future] = (task, task_start)

                # Collect results as they complete
                for future in as_completed(future_to_task):
                    task, task_start = future_to_task[future]
                    task_id = task["id"]

                    try:
                        result = future.result()
                        result["execution_time"] = time.time() - task_start
                        wave_results[task_id] = result
                    except Exception as e:
                        # Handle execution exception
                        wave_results[task_id] = {
                            "success": False,
                            "error": f"Execution exception: {str(e)}",
                            "output": None,
                            "execution_time": time.time() - task_start
                        }

        return wave_results

    def get_stats(self) -> Dict[str, Any]:
        """
        Get execution statistics.

        Returns:
            Dictionary with execution metrics
        """
        return self.execution_stats.copy()

    def reset_stats(self):
        """Reset execution statistics."""
        self.execution_stats = {
            "total_tasks": 0,
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "total_time": 0.0,
            "parallel_time_saved": 0.0
        }

    def __repr__(self) -> str:
        """String representation."""
        return f"ParallelExecutor(max_workers={self.max_workers})"
