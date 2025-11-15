"""
Orchestrator MVP for Cognitive Architecture

Orchestrates complete execution pipeline:
1. Multi-Pass Planning → Atomic tasks
2. DAG Builder → Dependency graph
3. Level-by-level parallel execution using CPIE
4. Error handling with retry logic (3 attempts, exponential backoff)
5. Progress tracking and metrics collection
6. Pattern learning from successful executions (≥95% precision)

Spec Reference: Section 3.5 - Orchestrator MVP
Target Coverage: >90%
"""

import logging
import time
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.cognitive.planning.multi_pass_planner import MultiPassPlanner
from src.cognitive.planning.dag_builder import DAGBuilder
from src.cognitive.inference.cpie import CPIE
from src.cognitive.signatures.semantic_signature import SemanticTaskSignature
from src.cognitive.patterns.pattern_bank import PatternBank
from src.cognitive.co_reasoning.co_reasoning import CoReasoningSystem

logger = logging.getLogger(__name__)


@dataclass
class ExecutionMetrics:
    """Metrics collected during orchestration execution."""

    task_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    retry_count: int = 0
    pattern_reuse_count: int = 0
    new_patterns_learned: int = 0
    total_time: float = 0.0
    level_times: Dict[int, float] = field(default_factory=dict)
    task_times: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "task_count": self.task_count,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "retry_count": self.retry_count,
            "pattern_reuse_count": self.pattern_reuse_count,
            "new_patterns_learned": self.new_patterns_learned,
            "total_time": self.total_time,
            "level_times": self.level_times,
            "task_times": self.task_times,
        }


class OrchestratorMVP:
    """
    Orchestrator MVP for end-to-end pipeline execution.

    Pipeline:
    1. Multi-Pass Planning: Spec → Atomic tasks
    2. DAG Builder: Atomic tasks → Dependency graph
    3. Execution: Level-by-level parallel execution with retry

    Features:
    - Parallel execution within dependency levels
    - Retry logic: 3 attempts with exponential backoff
    - Progress tracking with metrics collection
    - Pattern learning from successful executions (≥95% precision)

    Example:
        >>> orchestrator = OrchestratorMVP()
        >>> result = orchestrator.execute("Build user authentication system")
        >>> print(result["status"])  # "success"
    """

    def __init__(
        self,
        pattern_bank: Optional[PatternBank] = None,
        planner: Optional[MultiPassPlanner] = None,
        dag_builder: Optional[DAGBuilder] = None,
        cpie: Optional[CPIE] = None,
        co_reasoning_system: Optional[CoReasoningSystem] = None,
        max_retries: int = 3,
        max_workers: int = 4,
    ):
        """
        Initialize Orchestrator MVP.

        Args:
            pattern_bank: Pattern bank for pattern reuse and learning
            planner: Multi-pass planning system
            dag_builder: DAG builder for dependency management
            cpie: CPIE inference engine
            co_reasoning_system: Co-reasoning system (Claude + DeepSeek)
            max_retries: Maximum retry attempts per task (default: 3)
            max_workers: Maximum parallel workers for level execution (default: 4)
        """
        self.pattern_bank = pattern_bank or PatternBank()
        self.planner = planner or MultiPassPlanner()
        self.dag_builder = dag_builder or DAGBuilder()

        # Initialize co-reasoning system if not provided
        if co_reasoning_system is None:
            # Note: Claude/DeepSeek clients not configured in MVP
            # CPIE will work without LLM clients for pattern matching
            co_reasoning_system = CoReasoningSystem(
                pattern_bank=self.pattern_bank,
                claude_client=None,
                deepseek_client=None,
            )

        self.cpie = cpie or CPIE(
            pattern_bank=self.pattern_bank, co_reasoning_system=co_reasoning_system
        )
        self.max_retries = max_retries
        self.max_workers = max_workers

        self.metrics = ExecutionMetrics()
        self._current_level = 0

        logger.info(
            f"OrchestratorMVP initialized (max_retries={max_retries}, "
            f"max_workers={max_workers})"
        )

    def execute(self, spec: str) -> Dict[str, Any]:
        """
        Execute complete orchestration pipeline.

        Pipeline Steps:
        1. Multi-Pass Planning → Atomic tasks
        2. DAG Builder → Dependency graph with levels
        3. Cycle Detection → Fail if circular dependencies
        4. Level-by-level Execution → Parallel execution with retry
        5. Pattern Learning → Store successful patterns
        6. Metrics Collection → Return comprehensive metrics

        Args:
            spec: Project specification text

        Returns:
            Dict with status, results, metrics, and errors

        Example:
            >>> result = orchestrator.execute("Build REST API")
            >>> # Returns: {"status": "success", "metrics": {...}, "results": {...}}
        """
        start_time = time.time()
        logger.info(f"Starting orchestration for spec: {spec[:100]}...")

        try:
            # Step 1: Multi-Pass Planning
            logger.info("Step 1: Multi-Pass Planning...")
            plan = self.planner.plan(spec)
            atomic_tasks = plan.get("atomic_breakdown", [])

            if not atomic_tasks:
                logger.warning("Planning produced no atomic tasks")
                return {
                    "status": "empty",
                    "message": "No atomic tasks generated from spec",
                    "metrics": self.metrics.to_dict(),
                }

            self.metrics.task_count = len(atomic_tasks)
            logger.info(f"Planning complete: {len(atomic_tasks)} atomic tasks")

            # Step 2: DAG Builder
            logger.info("Step 2: Building dependency DAG...")
            dag_id = self.dag_builder.build_dag(atomic_tasks)
            logger.info(f"DAG built with ID: {dag_id}")

            # Step 3: Cycle Detection
            logger.info("Step 3: Detecting cycles...")
            cycles = self.dag_builder.detect_cycles(dag_id)
            if cycles:
                logger.error(f"Circular dependencies detected: {cycles}")
                return {
                    "status": "error",
                    "error": "Circular dependencies detected",
                    "cycles": cycles,
                    "metrics": self.metrics.to_dict(),
                }

            # Step 4: Topological Sort for Level Assignment
            logger.info("Step 4: Topological sorting...")
            levels = self.dag_builder.topological_sort(dag_id)
            logger.info(f"Topological sort complete: {len(levels)} levels")

            # Step 5: Level-by-level Execution
            logger.info("Step 5: Executing tasks level-by-level...")
            results = {}
            errors = {}

            for level_num in sorted(levels.keys()):
                task_ids = levels[level_num]
                logger.info(
                    f"Executing level {level_num} with {len(task_ids)} tasks..."
                )

                level_start = time.time()
                level_results, level_errors = self._execute_level(
                    level_num, task_ids, atomic_tasks
                )
                level_time = time.time() - level_start

                results.update(level_results)
                errors.update(level_errors)

                self.metrics.level_times[level_num] = level_time
                logger.info(
                    f"Level {level_num} complete in {level_time:.2f}s "
                    f"({len(level_results)} succeeded, {len(level_errors)} failed)"
                )

            # Step 6: Final Metrics
            self.metrics.total_time = time.time() - start_time
            logger.info(
                f"Orchestration complete in {self.metrics.total_time:.2f}s "
                f"({self.metrics.success_count}/{self.metrics.task_count} succeeded)"
            )

            # Determine overall status
            if self.metrics.success_count == self.metrics.task_count:
                status = "success"
            elif self.metrics.success_count > 0:
                status = "partial"
            else:
                status = "failed"

            return {
                "status": status,
                "results": results,
                "errors": errors if errors else None,
                "metrics": self.metrics.to_dict(),
                "dag_id": dag_id,
            }

        except Exception as e:
            logger.error(f"Orchestration failed with exception: {e}", exc_info=True)
            self.metrics.total_time = time.time() - start_time
            return {
                "status": "error",
                "error": str(e),
                "metrics": self.metrics.to_dict(),
            }
        finally:
            # Cleanup
            try:
                self.dag_builder.close()
            except Exception:
                pass

    def _execute_level(
        self,
        level_num: int,
        task_ids: List[str],
        atomic_tasks: List[Dict[str, Any]],
    ) -> Tuple[Dict[str, str], Dict[str, str]]:
        """
        Execute all tasks in a level in parallel.

        Args:
            level_num: Dependency level number
            task_ids: List of task IDs at this level
            atomic_tasks: Complete list of atomic tasks

        Returns:
            Tuple of (results, errors) dicts mapping task_id → code/error
        """
        self._current_level = level_num
        results = {}
        errors = {}

        # Find task definitions
        task_map = {task["id"]: task for task in atomic_tasks}

        # Execute tasks in parallel using ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_task_id = {
                executor.submit(
                    self._execute_task_with_retry, task_id, task_map[task_id]
                ): task_id
                for task_id in task_ids
                if task_id in task_map
            }

            for future in as_completed(future_to_task_id):
                task_id = future_to_task_id[future]

                try:
                    code = future.result()

                    if code is not None:
                        results[task_id] = code
                        self.metrics.success_count += 1

                        # Pattern learning for successful tasks
                        self._learn_pattern(task_map[task_id], code)
                    else:
                        errors[task_id] = "Task failed after max retries"
                        self.metrics.failure_count += 1
                        logger.error(f"Task {task_id} failed after all retries")

                except Exception as e:
                    errors[task_id] = str(e)
                    self.metrics.failure_count += 1
                    logger.error(f"Task {task_id} raised exception: {e}")

        return results, errors

    def _execute_task_with_retry(
        self, task_id: str, task: Dict[str, Any]
    ) -> Optional[str]:
        """
        Execute a single task with retry logic.

        Retry Strategy:
        - Attempt 1: Try with pattern matching
        - Attempt 2: Retry with exponential backoff (2s)
        - Attempt 3: Retry with exponential backoff (4s)
        - After 3 failures: Return None

        Args:
            task_id: Task identifier
            task: Task definition dict

        Returns:
            Generated code or None if all attempts fail
        """
        task_start = time.time()

        # Create signature from task
        signature = SemanticTaskSignature(
            purpose=task.get("purpose", ""),
            intent=task.get("intent", "create"),
            inputs=task.get("inputs", {}),
            outputs=task.get("outputs", {}),
            domain=task.get("domain", "general"),
            security_level=task.get("security_level", "low"),
            constraints=task.get("constraints", []),
        )

        for attempt in range(1, self.max_retries + 1):
            try:
                logger.debug(f"Task {task_id} attempt {attempt}/{self.max_retries}")

                # Execute with CPIE
                code = self.cpie.infer(signature)

                if code is not None:
                    task_time = time.time() - task_start
                    self.metrics.task_times[task_id] = task_time
                    logger.info(
                        f"Task {task_id} succeeded on attempt {attempt} "
                        f"(time: {task_time:.2f}s)"
                    )
                    return code

                # Failed attempt
                if attempt < self.max_retries:
                    self.metrics.retry_count += 1
                    backoff_time = 2 ** (attempt - 1)  # Exponential backoff: 1s, 2s, 4s
                    logger.warning(
                        f"Task {task_id} attempt {attempt} failed, "
                        f"retrying in {backoff_time}s..."
                    )
                    time.sleep(backoff_time)

            except Exception as e:
                logger.error(f"Task {task_id} attempt {attempt} raised error: {e}")
                if attempt < self.max_retries:
                    self.metrics.retry_count += 1
                    backoff_time = 2 ** (attempt - 1)
                    time.sleep(backoff_time)

        # All attempts failed
        task_time = time.time() - task_start
        self.metrics.task_times[task_id] = task_time
        logger.error(f"Task {task_id} failed after {self.max_retries} attempts")
        return None

    def _learn_pattern(self, task: Dict[str, Any], code: str) -> None:
        """
        Learn pattern from successful task execution.

        Pattern is stored when:
        - Task succeeds
        - Code quality is high (≥95% precision assumed for MVP)
        - Pattern is novel or improves existing pattern

        Args:
            task: Task definition
            code: Generated code that succeeded
        """
        try:
            # Create signature
            signature = SemanticTaskSignature(
                purpose=task.get("purpose", ""),
                intent=task.get("intent", "create"),
                inputs=task.get("inputs", {}),
                outputs=task.get("outputs", {}),
                domain=task.get("domain", "general"),
                security_level=task.get("security_level", "low"),
                constraints=task.get("constraints", []),
            )

            # Store pattern (PatternBank handles duplicate detection)
            pattern_id = self.pattern_bank.store_pattern(
                signature=signature,
                code=code,
                success_rate=0.95,  # MVP: Assume high quality for successful tasks
                metadata={"source": "orchestrator_mvp", "auto_learned": True},
            )

            if pattern_id:
                self.metrics.new_patterns_learned += 1
                logger.info(
                    f"Learned new pattern: {pattern_id} for purpose: {signature.purpose}"
                )

        except Exception as e:
            logger.warning(f"Pattern learning failed: {e}")


def execute_pipeline(
    spec: str,
    pattern_bank: Optional[PatternBank] = None,
    max_retries: int = 3,
) -> Dict[str, Any]:
    """
    Convenience function for executing orchestration pipeline.

    Args:
        spec: Project specification text
        pattern_bank: Optional pattern bank
        max_retries: Maximum retry attempts per task

    Returns:
        Execution result dict with status and metrics

    Example:
        >>> result = execute_pipeline("Build REST API")
        >>> print(result["status"])  # "success"
    """
    orchestrator = OrchestratorMVP(
        pattern_bank=pattern_bank, max_retries=max_retries
    )
    return orchestrator.execute(spec)
