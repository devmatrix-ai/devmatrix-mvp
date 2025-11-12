"""
Task Executor - Individual Task Execution with RAG

Executes individual tasks from MasterPlan using LLM + RAG context.

Flow:
1. Load task from database
2. Check dependencies (all must be completed)
3. Retrieve similar examples from RAG
4. Build execution context (discovery, masterplan, dependencies)
5. Generate code with LLM (Haiku/Sonnet based on complexity)
6. Save generated code to workspace
7. Update task status

Cost: $0.12-0.25 per task (with prompt caching)
Model Selection: 60% Haiku, 40% Sonnet (based on complexity)
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from uuid import UUID

from src.llm import EnhancedAnthropicClient, TaskType
from src.models.masterplan import (
    MasterPlanTask,
    MasterPlan,
    DiscoveryDocument,
    TaskStatus,
    TaskComplexity
)
from src.config.database import get_db_context
from src.rag import create_retriever, create_vector_store, create_embedding_model, create_feedback_service
from src.observability import get_logger
from src.observability.metrics_collector import MetricsCollector

logger = get_logger("task_executor")


# Task Execution System Prompt
TASK_EXECUTION_SYSTEM_PROMPT = """You are an expert software developer.

Your task is to implement a specific feature/task according to detailed specifications.

## Guidelines:

1. **Follow the Task Description**: Implement exactly what's described, no more, no less
2. **Use Project Context**: Leverage discovery, existing code patterns, and dependencies
3. **Code Quality**: Write clean, maintainable, well-documented code
4. **Follow Conventions**: Match the project's coding style and patterns
5. **Handle Errors**: Include proper error handling and validation
6. **Use Type Hints**: Python code should use type hints
7. **Add Docstrings**: Document all functions/classes

## Output Format:

Return ONLY the complete code for the specified file(s).

If multiple files, format as:

```python
# File: path/to/file1.py
[code here]

# File: path/to/file2.py
[code here]
```

**IMPORTANT**:
- Return ONLY code, no explanations, no markdown unless it's for multi-file output
- Code must be ready to save directly to file
- Include all necessary imports
- Ensure code is syntactically correct
"""


class TaskExecutor:
    """
    Task Executor for individual task execution.

    Usage:
        executor = TaskExecutor()
        result = await executor.execute_task(task_id=UUID("..."))
    """

    def __init__(
        self,
        llm_client: Optional[EnhancedAnthropicClient] = None,
        metrics_collector: Optional[MetricsCollector] = None,
        workspace_dir: str = "./workspace",
        use_rag: bool = True
    ):
        """
        Initialize Task Executor.

        Args:
            llm_client: LLM client
            metrics_collector: Metrics collector
            workspace_dir: Directory for generated code
            use_rag: Whether to use RAG for examples
        """
        self.llm = llm_client or EnhancedAnthropicClient()
        self.metrics = metrics_collector or MetricsCollector()
        self.workspace_dir = Path(workspace_dir)
        self.use_rag = use_rag

        # Initialize RAG
        if self.use_rag:
            try:
                embedding_model = create_embedding_model()
                self.vector_store = create_vector_store(embedding_model)
                self.retriever = create_retriever(self.vector_store)
                self.feedback_service = create_feedback_service(self.vector_store)
                logger.info("RAG retriever and feedback service initialized for Task Execution")
            except Exception as e:
                logger.warning(f"Failed to initialize RAG: {e}. Continuing without RAG.")
                self.use_rag = False
                self.retriever = None
                self.vector_store = None
                self.feedback_service = None
        else:
            self.retriever = None
            self.vector_store = None
            self.feedback_service = None

        logger.info("TaskExecutor initialized", workspace_dir=str(self.workspace_dir), use_rag=self.use_rag)

    async def execute_task(
        self,
        task_id: UUID,
        retry_on_failure: bool = True,
        max_retries: int = 1
    ) -> Dict[str, Any]:
        """
        Execute a single task.

        Args:
            task_id: Task UUID
            retry_on_failure: Whether to retry on failure
            max_retries: Maximum retry attempts

        Returns:
            Execution result dict

        Raises:
            ValueError: If task not found or blocked
            RuntimeError: If execution fails
        """
        logger.info("Starting task execution", task_id=str(task_id))

        # Record start
        self.metrics.increment_counter(
            "task_executions_total",
            labels={"task_id": str(task_id)},
            help_text="Total task executions"
        )

        try:
            # Load task and context
            task, masterplan, discovery = self._load_task_context(task_id)

            if not task:
                raise ValueError(f"Task not found: {task_id}")

            # Check if task is ready (dependencies met)
            if not self._check_dependencies_met(task):
                task.status = TaskStatus.BLOCKED
                self._update_task_status(task)
                raise ValueError(f"Task dependencies not met: {task_id}")

            # Mark as in_progress
            task.status = TaskStatus.IN_PROGRESS
            self._update_task_status(task)

            # Retrieve RAG examples
            rag_examples = await self._retrieve_rag_examples(task, discovery)

            # Generate code
            code_result = await self._generate_code(
                task=task,
                masterplan=masterplan,
                discovery=discovery,
                rag_examples=rag_examples
            )

            # Save code to workspace
            saved_files = self._save_generated_code(
                task=task,
                masterplan=masterplan,
                code=code_result["content"]
            )

            # Update task with results
            task.status = TaskStatus.COMPLETED
            task.llm_model = code_result["model"]
            task.llm_response = code_result["content"]
            task.llm_cost_usd = code_result["cost_usd"]
            task.llm_tokens_input = code_result["usage"]["input_tokens"]
            task.llm_tokens_output = code_result["usage"]["output_tokens"]
            task.llm_cached_tokens = code_result["usage"].get("cache_read_input_tokens", 0)
            task.modified_files = saved_files

            self._update_task_status(task)

            # Auto-index approved task code to RAG for continuous learning
            self._index_task_code_to_rag(task, code_result["content"])

            # Record success
            self.metrics.increment_counter(
                "task_executions_success_total",
                labels={"task_id": str(task_id), "complexity": str(task.complexity.value)},
                help_text="Successful task executions"
            )

            logger.info(
                "Task execution completed successfully",
                task_id=str(task_id),
                task_number=task.task_number,
                model=code_result["model"],
                cost=code_result["cost_usd"],
                files_saved=len(saved_files)
            )

            return {
                "task_id": str(task_id),
                "task_number": task.task_number,
                "status": "completed",
                "model": code_result["model"],
                "cost_usd": code_result["cost_usd"],
                "files_saved": saved_files,
                "cached_tokens": task.llm_cached_tokens
            }

        except Exception as e:
            # Record failure
            self.metrics.increment_counter(
                "task_executions_failures_total",
                labels={"task_id": str(task_id), "error_type": type(e).__name__},
                help_text="Failed task executions"
            )

            logger.error(
                "Task execution failed",
                task_id=str(task_id),
                error=str(e),
                error_type=type(e).__name__
            )

            # Update task status
            try:
                task, _, _ = self._load_task_context(task_id)
                if task:
                    task.status = TaskStatus.FAILED
                    task.last_error = str(e)
                    task.retry_count = (task.retry_count or 0) + 1
                    self._update_task_status(task)
            except:
                pass

            raise RuntimeError(f"Task execution failed: {str(e)}") from e

    def _load_task_context(self, task_id: UUID):
        """Load task, masterplan, and discovery."""
        with get_db_context() as db:
            task = db.query(MasterPlanTask).filter(
                MasterPlanTask.task_id == task_id
            ).first()

            if not task:
                return None, None, None

            # Load milestone → phase → masterplan → discovery
            milestone = task.milestone
            phase = milestone.phase
            masterplan = phase.masterplan
            discovery = masterplan.discovery

            return task, masterplan, discovery

    def _check_dependencies_met(self, task: MasterPlanTask) -> bool:
        """Check if all task dependencies are completed."""
        if not task.depends_on_tasks:
            return True

        with get_db_context() as db:
            for dep_id in task.depends_on_tasks:
                dep_task = db.query(MasterPlanTask).filter(
                    MasterPlanTask.task_id == UUID(dep_id)
                ).first()

                if not dep_task or dep_task.status != TaskStatus.COMPLETED:
                    logger.warning(
                        f"Task {task.task_number} blocked by incomplete dependency",
                        task_id=str(task.task_id),
                        dependency_id=dep_id,
                        dependency_status=dep_task.status.value if dep_task else "not_found"
                    )
                    return False

        return True

    def _update_task_status(self, task: MasterPlanTask):
        """Update task status in database."""
        with get_db_context() as db:
            db_task = db.query(MasterPlanTask).filter(
                MasterPlanTask.task_id == task.task_id
            ).first()

            if db_task:
                db_task.status = task.status
                db_task.llm_model = task.llm_model
                db_task.llm_response = task.llm_response
                db_task.llm_cost_usd = task.llm_cost_usd
                db_task.llm_tokens_input = task.llm_tokens_input
                db_task.llm_tokens_output = task.llm_tokens_output
                db_task.llm_cached_tokens = task.llm_cached_tokens
                db_task.modified_files = task.modified_files
                db_task.last_error = task.last_error
                db_task.retry_count = task.retry_count

    async def _retrieve_rag_examples(
        self,
        task: MasterPlanTask,
        discovery: DiscoveryDocument
    ) -> List[Dict]:
        """Retrieve similar examples from RAG."""
        if not self.use_rag or not self.retriever:
            return []

        try:
            # Build query from task
            query = f"{task.name}. {task.description[:200]}"

            results = self.retriever.retrieve(
                query=query,
                top_k=5,
                min_similarity=0.7
            )

            logger.info(f"Retrieved {len(results)} RAG examples for task {task.task_number}")

            return [
                {
                    "code": r.code,
                    "metadata": r.metadata,
                    "similarity": r.similarity
                }
                for r in results
            ]

        except Exception as e:
            logger.warning(f"Failed to retrieve RAG examples: {e}")
            return []

    async def _generate_code(
        self,
        task: MasterPlanTask,
        masterplan: MasterPlan,
        discovery: DiscoveryDocument,
        rag_examples: List[Dict]
    ) -> Dict[str, Any]:
        """Generate code using LLM."""
        import time

        start_time = time.time()

        # Build context
        discovery_context = {
            "domain": discovery.domain,
            "bounded_contexts": discovery.bounded_contexts,
            "aggregates": discovery.aggregates
        }

        masterplan_context = {
            "project_name": masterplan.project_name,
            "tech_stack": masterplan.tech_stack,
            "architecture_style": masterplan.architecture_style
        }

        rag_context = {
            "examples_count": len(rag_examples),
            "examples": rag_examples[:3]
        } if rag_examples else None

        # Build variable prompt
        variable_prompt = f"""Implement the following task:

## Task #{task.task_number}: {task.name}

**Description**:
{task.description}

**Target Files**: {', '.join(task.target_files)}

**Complexity**: {task.complexity.value}

## Project Context:
**Domain**: {discovery.domain}
**Tech Stack**: {masterplan.tech_stack}

Generate complete, production-ready code for this task.
"""

        # Map DB complexity to LLM complexity
        complexity_map = {
            TaskComplexity.LOW: "low",
            TaskComplexity.MEDIUM: "medium",
            TaskComplexity.HIGH: "high",
            TaskComplexity.CRITICAL: "critical"
        }

        # Generate with caching
        response = await self.llm.generate_with_caching(
            task_type=TaskType.TASK_EXECUTION,
            complexity=complexity_map.get(task.complexity, "medium"),
            cacheable_context={
                "system_prompt": TASK_EXECUTION_SYSTEM_PROMPT,
                "discovery_doc": discovery_context,
                "masterplan_context": masterplan_context,
                "rag_examples": rag_context
            },
            variable_prompt=variable_prompt,
            max_tokens=8000,
            temperature=0.0  # Deterministic mode
        )

        duration = time.time() - start_time

        logger.info(
            "Code generation complete",
            task_number=task.task_number,
            model=response["model"],
            cost=response["cost_usd"],
            duration=duration,
            cached_tokens=response["usage"].get("cache_read_input_tokens", 0)
        )

        return {
            "content": response["content"],
            "model": response["model"],
            "cost_usd": response["cost_usd"],
            "usage": response["usage"],
            "duration_seconds": duration
        }

    def _save_generated_code(
        self,
        task: MasterPlanTask,
        masterplan: MasterPlan,
        code: str
    ) -> List[str]:
        """Save generated code to workspace."""
        # Create project workspace
        project_dir = self.workspace_dir / masterplan.project_name.lower().replace(" ", "_")
        project_dir.mkdir(parents=True, exist_ok=True)

        saved_files = []

        # Check if multi-file output
        if "# File:" in code:
            # Parse multi-file output
            files = self._parse_multifile_code(code)

            for file_path, file_code in files.items():
                full_path = project_dir / file_path
                full_path.parent.mkdir(parents=True, exist_ok=True)

                full_path.write_text(file_code)
                saved_files.append(str(full_path))

                logger.debug(f"Saved file: {full_path}")

        else:
            # Single file output
            if task.target_files:
                file_path = task.target_files[0]
                full_path = project_dir / file_path
                full_path.parent.mkdir(parents=True, exist_ok=True)

                full_path.write_text(code)
                saved_files.append(str(full_path))

                logger.debug(f"Saved file: {full_path}")

        logger.info(f"Saved {len(saved_files)} files for task {task.task_number}")

        return saved_files

    def _parse_multifile_code(self, code: str) -> Dict[str, str]:
        """Parse multi-file code output."""
        files = {}
        current_file = None
        current_code = []

        for line in code.split('\n'):
            if line.startswith("# File:"):
                # Save previous file
                if current_file:
                    files[current_file] = '\n'.join(current_code).strip()

                # Start new file
                current_file = line.replace("# File:", "").strip()
                current_code = []
            else:
                if current_file:
                    current_code.append(line)

        # Save last file
        if current_file:
            files[current_file] = '\n'.join(current_code).strip()

        return files

    def _index_task_code_to_rag(self, task: MasterPlanTask, code: str):
        """Index the generated code into the RAG vector store."""
        if self.feedback_service and self.use_rag:
            try:
                self.feedback_service.record_approval(
                    task_id=str(task.task_id),
                    code=code,
                    metadata={
                        "task_name": task.name,
                        "task_description": task.description,
                        "task_complexity": task.complexity.value,
                        "task_target_files": task.target_files,
                        "task_dependencies": task.depends_on_tasks
                    }
                )
                logger.info(f"Task code for {task.task_number} successfully indexed to RAG.")
            except Exception as e:
                logger.warning(f"Failed to index task code to RAG: {e}")

    def get_task_status(self, task_id: UUID) -> Optional[Dict[str, Any]]:
        """Get task execution status."""
        task, _, _ = self._load_task_context(task_id)

        if not task:
            return None

        return {
            "task_id": str(task.task_id),
            "task_number": task.task_number,
            "name": task.name,
            "status": task.status.value,
            "complexity": task.complexity.value,
            "llm_model": task.llm_model,
            "cost_usd": task.llm_cost_usd,
            "modified_files": task.modified_files,
            "retry_count": task.retry_count,
            "last_error": task.last_error
        }
