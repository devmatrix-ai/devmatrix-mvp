"""
ThunderingHerdPrevention - Prevent thundering herd on wave start

Prevents all 100+ atoms from executing simultaneously when a wave starts
by staggering execution with jitter.
"""
import asyncio
import logging
import random
from typing import Callable, Any, Awaitable
from datetime import datetime

logger = logging.getLogger(__name__)


class ThunderingHerdPrevention:
    """
    Prevent thundering herd with staggered execution

    Features:
    - Jittered delays on execution start
    - Configurable stagger window
    - Batch execution control
    - Monitoring of execution distribution
    """

    def __init__(
        self,
        max_jitter_seconds: float = 2.0,
        batch_size: int = 20,
        batch_delay_seconds: float = 0.5
    ):
        """
        Initialize ThunderingHerdPrevention

        Args:
            max_jitter_seconds: Maximum random delay (0 to this value)
            batch_size: Number of tasks per batch
            batch_delay_seconds: Delay between batches
        """
        self.max_jitter_seconds = max_jitter_seconds
        self.batch_size = batch_size
        self.batch_delay_seconds = batch_delay_seconds

        # Statistics
        self._total_executions = 0
        self._current_batch = 0

    async def execute_with_jitter(
        self,
        task_func: Callable[[], Awaitable[Any]],
        task_id: str
    ) -> Any:
        """
        Execute task with random jitter delay

        Args:
            task_func: Async function to execute
            task_id: Task identifier for logging

        Returns:
            Result of task_func()
        """
        # Random jitter
        jitter = random.uniform(0, self.max_jitter_seconds)

        logger.debug(
            f"Task {task_id} waiting {jitter:.2f}s before execution (thundering herd prevention)"
        )

        await asyncio.sleep(jitter)

        self._total_executions += 1

        # Execute task
        result = await task_func()

        return result

    async def execute_in_batches(
        self,
        tasks: list[tuple[Callable[[], Awaitable[Any]], str]]
    ) -> list[Any]:
        """
        Execute tasks in controlled batches

        Args:
            tasks: List of (task_func, task_id) tuples

        Returns:
            List of task results
        """
        results = []
        total_tasks = len(tasks)

        logger.info(
            f"Executing {total_tasks} tasks in batches of {self.batch_size} "
            f"with {self.batch_delay_seconds}s delay between batches"
        )

        for batch_num in range(0, total_tasks, self.batch_size):
            batch = tasks[batch_num:batch_num + self.batch_size]
            self._current_batch = batch_num // self.batch_size

            logger.debug(
                f"Starting batch {self._current_batch + 1} "
                f"({len(batch)} tasks)"
            )

            # Execute batch with jitter
            batch_tasks = [
                self.execute_with_jitter(task_func, task_id)
                for task_func, task_id in batch
            ]

            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            results.extend(batch_results)

            # Delay before next batch (except for last batch)
            if batch_num + self.batch_size < total_tasks:
                await asyncio.sleep(self.batch_delay_seconds)

        logger.info(f"Completed all {total_tasks} tasks")

        return results

    def get_statistics(self) -> dict:
        """
        Get execution statistics

        Returns:
            Dict with stats: {
                'total_executions': int,
                'current_batch': int,
                'max_jitter_seconds': float,
                'batch_size': int
            }
        """
        return {
            'total_executions': self._total_executions,
            'current_batch': self._current_batch,
            'max_jitter_seconds': self.max_jitter_seconds,
            'batch_size': self.batch_size
        }

    def reset_statistics(self):
        """Reset execution statistics"""
        self._total_executions = 0
        self._current_batch = 0
        logger.info("Reset thundering herd prevention statistics")
