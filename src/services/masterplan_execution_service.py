"""
MasterPlan Execution Service

Orchestrates masterplan execution with workspace creation, task execution,
database persistence, and WebSocket event broadcasting.
"""

from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime
from sqlalchemy.orm import Session
from collections import defaultdict
import asyncio

from src.models.masterplan import (
    MasterPlan,
    MasterPlanPhase,
    MasterPlanMilestone,
    MasterPlanTask,
    MasterPlanStatus,
    TaskStatus,
)
from src.services.workspace_service import WorkspaceService
from src.observability import StructuredLogger

# Import Socket.IO server from websocket router
try:
    from src.api.routers.websocket import sio
except ImportError:
    # Fallback for testing or when websocket is not available
    sio = None


class MasterplanExecutionService:
    """
    Service for executing masterplans.

    Responsibilities:
    - Create workspace for masterplan execution
    - Store workspace_path in database
    - Coordinate task execution with OrchestratorAgent
    - Update masterplan and task status during execution
    - Emit WebSocket events for real-time monitoring
    """

    def __init__(self, db_session: Session, workspace_base_dir: str = "./workspace"):
        """
        Initialize execution service.

        Args:
            db_session: SQLAlchemy database session
            workspace_base_dir: Base directory for workspace creation
        """
        self.db = db_session
        self.logger = StructuredLogger("masterplan_execution")
        self.workspace_service = WorkspaceService(base_workspace_dir=workspace_base_dir)

    def create_workspace(self, masterplan_id: UUID) -> str:
        """
        Create workspace for masterplan execution and store path in database.

        Args:
            masterplan_id: UUID of the masterplan

        Returns:
            Absolute path to created workspace

        Raises:
            ValueError: If masterplan not found or workspace creation fails
        """
        # Load masterplan from database
        masterplan = self.db.query(MasterPlan).filter_by(masterplan_id=masterplan_id).first()

        if not masterplan:
            self.logger.error("Masterplan not found", masterplan_id=str(masterplan_id))
            raise ValueError(f"Masterplan {masterplan_id} not found")

        try:
            # Create workspace using WorkspaceService
            workspace_name = f"masterplan_{masterplan.project_name}".replace(" ", "_").lower()
            workspace = self.workspace_service.create_workspace(
                name=workspace_name,
                metadata={
                    "masterplan_id": str(masterplan_id),
                    "project_name": masterplan.project_name,
                    "created_at": datetime.utcnow().isoformat(),
                }
            )

            # Store workspace_path in masterplans table
            workspace_path = str(workspace.base_path.absolute())
            masterplan.workspace_path = workspace_path
            self.db.commit()

            self.logger.info(
                "Workspace created for masterplan",
                masterplan_id=str(masterplan_id),
                workspace_path=workspace_path,
                workspace_id=workspace.workspace_id,
            )

            return workspace_path

        except Exception as e:
            self.db.rollback()
            self.logger.error(
                "Failed to create workspace",
                masterplan_id=str(masterplan_id),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise ValueError(f"Failed to create workspace: {e}")

    def get_workspace_path(self, masterplan_id: UUID) -> Optional[str]:
        """
        Get workspace path for masterplan.

        Args:
            masterplan_id: UUID of the masterplan

        Returns:
            Workspace path if set, None otherwise
        """
        masterplan = self.db.query(MasterPlan).filter_by(masterplan_id=masterplan_id).first()

        if not masterplan:
            return None

        return masterplan.workspace_path

    def update_masterplan_status(
        self, masterplan_id: UUID, status: MasterPlanStatus
    ) -> bool:
        """
        Update masterplan execution status.

        Args:
            masterplan_id: UUID of the masterplan
            status: New status

        Returns:
            True if updated successfully, False otherwise
        """
        try:
            masterplan = self.db.query(MasterPlan).filter_by(masterplan_id=masterplan_id).first()

            if not masterplan:
                self.logger.error("Masterplan not found", masterplan_id=str(masterplan_id))
                return False

            masterplan.status = status
            masterplan.updated_at = datetime.utcnow()

            # Set started_at or completed_at based on status
            if status == MasterPlanStatus.IN_PROGRESS and not masterplan.started_at:
                masterplan.started_at = datetime.utcnow()
            elif status == MasterPlanStatus.COMPLETED and not masterplan.completed_at:
                masterplan.completed_at = datetime.utcnow()

            self.db.commit()

            self.logger.info(
                "Masterplan status updated",
                masterplan_id=str(masterplan_id),
                old_status=masterplan.status.value if hasattr(masterplan.status, 'value') else str(masterplan.status),
                new_status=status.value,
            )

            return True

        except Exception as e:
            self.db.rollback()
            self.logger.error(
                "Failed to update masterplan status",
                masterplan_id=str(masterplan_id),
                status=status.value,
                error=str(e),
                error_type=type(e).__name__,
            )
            return False

    def _emit_websocket_event(
        self,
        event_name: str,
        masterplan_id: UUID,
        data: Dict[str, Any]
    ):
        """
        Emit WebSocket event for real-time monitoring.

        Uses Socket.IO to broadcast events to clients in the masterplan room.
        Room name format: f"masterplan_{masterplan_id}"

        Args:
            event_name: Name of the event (e.g., "masterplan_execution_start")
            masterplan_id: UUID of the masterplan
            data: Event payload data
        """
        if not sio:
            self.logger.warning(
                "Socket.IO not available, skipping WebSocket event",
                event_name=event_name,
                masterplan_id=str(masterplan_id)
            )
            return

        try:
            room = f"masterplan_{masterplan_id}"

            # Use asyncio to emit event (Socket.IO emit is async)
            # Create event loop if not exists
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            # Schedule the emit coroutine
            if loop.is_running():
                # If loop is already running, create a task
                asyncio.create_task(sio.emit(event_name, data, room=room))
            else:
                # If loop is not running, run until complete
                loop.run_until_complete(sio.emit(event_name, data, room=room))

            self.logger.info(
                "WebSocket event emitted",
                event_name=event_name,
                masterplan_id=str(masterplan_id),
                room=room
            )

        except Exception as e:
            # Log error but don't fail execution
            self.logger.error(
                "Failed to emit WebSocket event",
                event_name=event_name,
                masterplan_id=str(masterplan_id),
                error=str(e),
                error_type=type(e).__name__
            )

    def execute(self, masterplan_id: UUID) -> Dict[str, Any]:
        """
        Execute masterplan tasks in dependency order.

        This method orchestrates the complete execution flow:
        1. Load masterplan with all phases, milestones, tasks
        2. Emit masterplan_execution_start WebSocket event
        3. Extract target_files from each task
        4. Build task execution plan with dependency resolution (topological sort)
        5. Execute tasks in order, handling retries and failures
        6. Emit task_execution_progress and task_execution_complete events
        7. Update task and masterplan status in database
        8. Complete execution

        Args:
            masterplan_id: UUID of the masterplan to execute

        Returns:
            Dictionary with execution results
        """
        try:
            self.logger.info("Starting masterplan execution", masterplan_id=str(masterplan_id))

            # Load masterplan with all relationships
            masterplan = (
                self.db.query(MasterPlan)
                .filter_by(masterplan_id=masterplan_id)
                .first()
            )

            if not masterplan:
                raise ValueError(f"Masterplan {masterplan_id} not found")

            # Get workspace path (should already exist from create_workspace)
            workspace_path = masterplan.workspace_path
            if not workspace_path:
                raise ValueError(f"Workspace path not set for masterplan {masterplan_id}")

            # Collect all tasks from all phases and milestones
            all_tasks = []
            for phase in masterplan.phases:
                for milestone in phase.milestones:
                    for task in milestone.tasks:
                        all_tasks.append(task)

            total_tasks = len(all_tasks)
            self.logger.info(
                "Loaded masterplan tasks",
                masterplan_id=str(masterplan_id),
                total_tasks=total_tasks
            )

            # Emit masterplan_execution_start event
            self._emit_websocket_event(
                event_name="masterplan_execution_start",
                masterplan_id=masterplan_id,
                data={
                    "masterplan_id": str(masterplan_id),
                    "workspace_id": workspace_path.split("/")[-1] if workspace_path else "unknown",
                    "workspace_path": workspace_path,
                    "total_tasks": total_tasks
                }
            )

            # Build dependency graph for topological sort
            dependency_graph = self._build_dependency_graph(all_tasks)

            # Execute tasks in dependency order
            execution_order = self._topological_sort(all_tasks, dependency_graph)

            if not execution_order:
                self.logger.error("Circular dependencies detected", masterplan_id=str(masterplan_id))
                self.update_masterplan_status(masterplan_id, MasterPlanStatus.FAILED)
                return {
                    "success": False,
                    "error": "Circular dependencies detected in task graph",
                    "completed_tasks": 0,
                    "total_tasks": total_tasks
                }

            # Execute tasks
            completed_count = 0
            failed_count = 0
            skipped_count = 0

            for idx, task in enumerate(execution_order):
                # Update progress callback - emit task_execution_progress
                self._progress_callback(
                    masterplan_id=masterplan_id,
                    task=task,
                    status="in_progress",
                    current_task=idx + 1,
                    total_tasks=total_tasks
                )

                # Execute task (stub for now, full implementation will use OrchestratorAgent)
                success = self._execute_single_task(task, masterplan_id)

                if success:
                    completed_count += 1
                    # Emit task_execution_complete event
                    self._emit_websocket_event(
                        event_name="task_execution_complete",
                        masterplan_id=masterplan_id,
                        data={
                            "masterplan_id": str(masterplan_id),
                            "task_id": str(task.task_id),
                            "status": "completed",
                            "output_files": task.target_files or [],
                            "completed_tasks": completed_count,
                            "total_tasks": total_tasks
                        }
                    )
                    self._progress_callback(
                        masterplan_id=masterplan_id,
                        task=task,
                        status="completed",
                        current_task=idx + 1,
                        total_tasks=total_tasks
                    )
                else:
                    # Handle retry logic
                    if task.retry_count < task.max_retries:
                        task.retry_count += 1
                        self.db.commit()
                        self.logger.info(
                            "Retrying task",
                            task_id=str(task.task_id),
                            retry_count=task.retry_count,
                            max_retries=task.max_retries
                        )
                        # Retry the task
                        success = self._execute_single_task(task, masterplan_id)
                        if success:
                            completed_count += 1
                            # Emit task_execution_complete event
                            self._emit_websocket_event(
                                event_name="task_execution_complete",
                                masterplan_id=masterplan_id,
                                data={
                                    "masterplan_id": str(masterplan_id),
                                    "task_id": str(task.task_id),
                                    "status": "completed",
                                    "output_files": task.target_files or [],
                                    "completed_tasks": completed_count,
                                    "total_tasks": total_tasks
                                }
                            )
                            self._progress_callback(
                                masterplan_id=masterplan_id,
                                task=task,
                                status="completed",
                                current_task=idx + 1,
                                total_tasks=total_tasks
                            )
                        else:
                            failed_count += 1
                            # Emit task_execution_complete with failed status
                            self._emit_websocket_event(
                                event_name="task_execution_complete",
                                masterplan_id=masterplan_id,
                                data={
                                    "masterplan_id": str(masterplan_id),
                                    "task_id": str(task.task_id),
                                    "status": "failed",
                                    "output_files": task.target_files or [],
                                    "completed_tasks": completed_count,
                                    "total_tasks": total_tasks
                                }
                            )
                            self._progress_callback(
                                masterplan_id=masterplan_id,
                                task=task,
                                status="failed",
                                current_task=idx + 1,
                                total_tasks=total_tasks
                            )
                    else:
                        failed_count += 1
                        # Emit task_execution_complete with failed status
                        self._emit_websocket_event(
                            event_name="task_execution_complete",
                            masterplan_id=masterplan_id,
                            data={
                                "masterplan_id": str(masterplan_id),
                                "task_id": str(task.task_id),
                                "status": "failed",
                                "output_files": task.target_files or [],
                                "completed_tasks": completed_count,
                                "total_tasks": total_tasks
                            }
                        )
                        self._progress_callback(
                            masterplan_id=masterplan_id,
                            task=task,
                            status="failed",
                            current_task=idx + 1,
                            total_tasks=total_tasks
                        )

            # Update masterplan status to completed
            self.update_masterplan_status(masterplan_id, MasterPlanStatus.COMPLETED)

            # Update progress counters
            masterplan.completed_tasks = completed_count
            masterplan.progress_percent = (completed_count / total_tasks * 100) if total_tasks > 0 else 0
            self.db.commit()

            self.logger.info(
                "Masterplan execution completed",
                masterplan_id=str(masterplan_id),
                completed=completed_count,
                failed=failed_count,
                total=total_tasks
            )

            return {
                "success": True,
                "completed_tasks": completed_count,
                "failed_tasks": failed_count,
                "total_tasks": total_tasks,
                "workspace_path": workspace_path
            }

        except Exception as e:
            self.logger.error(
                "Masterplan execution failed",
                masterplan_id=str(masterplan_id),
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True
            )
            self.update_masterplan_status(masterplan_id, MasterPlanStatus.FAILED)
            return {
                "success": False,
                "error": str(e),
                "completed_tasks": 0,
                "total_tasks": 0
            }

    def _build_dependency_graph(self, tasks: List[MasterPlanTask]) -> Dict[UUID, List[UUID]]:
        """
        Build dependency graph from tasks.

        Args:
            tasks: List of MasterPlanTask objects

        Returns:
            Dictionary mapping task_id to list of dependency task_ids
        """
        dependency_graph = {}
        task_id_map = {task.task_id: task for task in tasks}

        for task in tasks:
            # depends_on_tasks is a list of task_ids (strings) in the JSON field
            depends_on = task.depends_on_tasks or []
            # Convert string UUIDs to UUID objects
            dependency_uuids = []
            for dep_str in depends_on:
                try:
                    dep_uuid = UUID(dep_str) if isinstance(dep_str, str) else dep_str
                    if dep_uuid in task_id_map:
                        dependency_uuids.append(dep_uuid)
                except (ValueError, TypeError):
                    self.logger.warning(
                        "Invalid dependency UUID",
                        task_id=str(task.task_id),
                        dependency=str(dep_str)
                    )

            dependency_graph[task.task_id] = dependency_uuids

        return dependency_graph

    def _topological_sort(
        self,
        tasks: List[MasterPlanTask],
        dependency_graph: Dict[UUID, List[UUID]]
    ) -> List[MasterPlanTask]:
        """
        Topological sort of tasks based on dependencies.

        Returns tasks in execution order, or empty list if circular dependency.
        Implementation follows orchestrator_agent.py _topological_sort method.

        Args:
            tasks: List of MasterPlanTask objects
            dependency_graph: Dictionary mapping task_id to list of dependency task_ids

        Returns:
            List of tasks in execution order, or empty list if circular dependency
        """
        # Build in-degree map
        in_degree = {task.task_id: 0 for task in tasks}
        for task_id, deps in dependency_graph.items():
            for dep in deps:
                if dep in in_degree:  # Only count dependencies that exist
                    in_degree[task_id] += 1

        # Find tasks with no dependencies
        queue = [task for task in tasks if in_degree[task.task_id] == 0]
        result = []

        while queue:
            # Take task with no dependencies
            current_task = queue.pop(0)
            result.append(current_task)
            current_id = current_task.task_id

            # Find tasks that depend on current task
            for task in tasks:
                if current_id in dependency_graph.get(task.task_id, []):
                    in_degree[task.task_id] -= 1
                    if in_degree[task.task_id] == 0:
                        queue.append(task)

        # If not all tasks processed, there's a cycle
        if len(result) != len(tasks):
            return []

        return result

    def _progress_callback(
        self,
        masterplan_id: UUID,
        task: MasterPlanTask,
        status: str,
        current_task: int,
        total_tasks: int
    ):
        """
        Progress callback to handle task updates.

        Updates task status in database and emits WebSocket events.

        Args:
            masterplan_id: UUID of the masterplan
            task: MasterPlanTask object
            status: Task status (ready, in_progress, completed, failed)
            current_task: Current task number (1-indexed)
            total_tasks: Total number of tasks
        """
        try:
            # Update task status in database
            if status == "ready":
                task.status = TaskStatus.READY
            elif status == "in_progress":
                task.status = TaskStatus.IN_PROGRESS
                if not task.started_at:
                    task.started_at = datetime.utcnow()
            elif status == "completed":
                task.status = TaskStatus.COMPLETED
                task.completed_at = datetime.utcnow()
            elif status == "failed":
                task.status = TaskStatus.FAILED
                task.failed_at = datetime.utcnow()

            # Persist changes immediately
            self.db.commit()

            self.logger.info(
                "Task status updated",
                masterplan_id=str(masterplan_id),
                task_id=str(task.task_id),
                task_number=task.task_number,
                status=status,
                progress=f"{current_task}/{total_tasks}"
            )

            # Emit WebSocket event for task_execution_progress
            self._emit_websocket_event(
                event_name="task_execution_progress",
                masterplan_id=masterplan_id,
                data={
                    "masterplan_id": str(masterplan_id),
                    "task_id": str(task.task_id),
                    "task_number": task.task_number,
                    "status": status,
                    "description": task.description,
                    "current_task": current_task,
                    "total_tasks": total_tasks
                }
            )

        except Exception as e:
            self.db.rollback()
            self.logger.error(
                "Failed to update task status",
                masterplan_id=str(masterplan_id),
                task_id=str(task.task_id),
                status=status,
                error=str(e),
                error_type=type(e).__name__
            )

    def _execute_single_task(
        self,
        task: MasterPlanTask,
        masterplan_id: UUID
    ) -> bool:
        """
        Execute a single task.

        This is a stub implementation for Group 3. Full implementation with
        OrchestratorAgent integration will be completed in a future iteration.

        Args:
            task: MasterPlanTask to execute
            masterplan_id: UUID of the masterplan

        Returns:
            True if task executed successfully, False otherwise
        """
        try:
            self.logger.info(
                "Executing task (stub)",
                task_id=str(task.task_id),
                task_number=task.task_number,
                name=task.name,
                target_files=task.target_files or []
            )

            # Extract target_files from task (fixes file overwriting bug)
            target_files = task.target_files or []

            # Validate target_files are set
            if not target_files:
                self.logger.warning(
                    "Task has no target_files specified",
                    task_id=str(task.task_id),
                    task_number=task.task_number
                )

            # TODO: Integrate with OrchestratorAgent for actual execution
            # For now, mark task as completed (stub)
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.utcnow()
            self.db.commit()

            return True

        except Exception as e:
            self.logger.error(
                "Task execution failed",
                task_id=str(task.task_id),
                error=str(e),
                error_type=type(e).__name__
            )
            task.status = TaskStatus.FAILED
            task.failed_at = datetime.utcnow()
            task.last_error = str(e)
            self.db.commit()
            return False
