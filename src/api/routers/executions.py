"""
Workflow Execution Router

Endpoints for executing and monitoring workflows.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum

from fastapi import APIRouter, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, Field


router = APIRouter(prefix="/executions", tags=["executions"])


class ExecutionStatus(str, Enum):
    """Execution status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskStatus(BaseModel):
    """Task execution status."""
    task_id: str
    status: ExecutionStatus
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    result: Optional[Dict[str, Any]] = None


class ExecutionCreate(BaseModel):
    """Execution creation request."""
    workflow_id: str = Field(..., description="Workflow to execute")
    input_data: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Input data for workflow")
    priority: int = Field(default=5, ge=1, le=10, description="Execution priority")


class ExecutionResponse(BaseModel):
    """Execution response model."""
    execution_id: str
    workflow_id: str
    status: ExecutionStatus
    input_data: Dict[str, Any]
    priority: int
    task_statuses: List[TaskStatus]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error: Optional[str]
    result: Optional[Dict[str, Any]]
    created_at: datetime


# In-memory storage
executions_db: Dict[str, Dict[str, Any]] = {}


async def execute_workflow_background(execution_id: str, workflow_id: str, input_data: Dict[str, Any]):
    """
    Execute workflow in background.

    Args:
        execution_id: Execution identifier
        workflow_id: Workflow to execute
        input_data: Input data for workflow
    """
    import asyncio
    from ...observability import StructuredLogger

    logger = StructuredLogger("executions")
    logger.info(f"Starting execution {execution_id} for workflow {workflow_id}")

    execution = executions_db[execution_id]
    execution["status"] = ExecutionStatus.RUNNING
    execution["started_at"] = datetime.now()

    try:
        # Simulate workflow execution
        # In production, this would use the actual DAGExecutor
        await asyncio.sleep(2)  # Simulate work

        # Update task statuses
        task_statuses = []
        for task in execution.get("tasks", []):
            task_statuses.append({
                "task_id": task["task_id"],
                "status": ExecutionStatus.COMPLETED,
                "started_at": datetime.now(),
                "completed_at": datetime.now(),
                "error": None,
                "result": {"output": f"Task {task['task_id']} completed successfully"},
            })

        execution["task_statuses"] = task_statuses
        execution["status"] = ExecutionStatus.COMPLETED
        execution["completed_at"] = datetime.now()
        execution["result"] = {"output": "Workflow completed successfully"}

        logger.info(f"Execution {execution_id} completed successfully")

    except Exception as e:
        execution["status"] = ExecutionStatus.FAILED
        execution["completed_at"] = datetime.now()
        execution["error"] = str(e)
        logger.error(f"Execution {execution_id} failed: {str(e)}")


@router.post(
    "",
    response_model=ExecutionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start workflow execution",
    description="Start a new workflow execution",
)
async def create_execution(
    execution: ExecutionCreate,
    background_tasks: BackgroundTasks,
) -> ExecutionResponse:
    """
    Start workflow execution.

    Args:
        execution: Execution creation data
        background_tasks: FastAPI background tasks

    Returns:
        Created execution with ID

    Raises:
        HTTPException: If workflow not found or execution fails to start
    """
    import uuid
    from .workflows import workflows_db

    # Validate workflow exists
    if execution.workflow_id not in workflows_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow {execution.workflow_id} not found",
        )

    execution_id = str(uuid.uuid4())
    now = datetime.now()

    workflow = workflows_db[execution.workflow_id]

    execution_data = {
        "execution_id": execution_id,
        "workflow_id": execution.workflow_id,
        "status": ExecutionStatus.PENDING,
        "input_data": execution.input_data,
        "priority": execution.priority,
        "tasks": workflow["tasks"],
        "task_statuses": [],
        "started_at": None,
        "completed_at": None,
        "error": None,
        "result": None,
        "created_at": now,
    }

    executions_db[execution_id] = execution_data

    # Start execution in background
    background_tasks.add_task(
        execute_workflow_background,
        execution_id,
        execution.workflow_id,
        execution.input_data,
    )

    return ExecutionResponse(**execution_data)


@router.get(
    "",
    response_model=List[ExecutionResponse],
    summary="List all executions",
    description="Retrieve all workflow executions",
)
async def list_executions(
    workflow_id: Optional[str] = None,
    status: Optional[ExecutionStatus] = None,
) -> List[ExecutionResponse]:
    """
    List executions with optional filtering.

    Args:
        workflow_id: Filter by workflow ID
        status: Filter by execution status

    Returns:
        List of executions
    """
    executions = list(executions_db.values())

    if workflow_id:
        executions = [e for e in executions if e["workflow_id"] == workflow_id]

    if status:
        executions = [e for e in executions if e["status"] == status]

    return [ExecutionResponse(**e) for e in executions]


@router.get(
    "/{execution_id}",
    response_model=ExecutionResponse,
    summary="Get execution by ID",
    description="Retrieve a specific execution by its ID",
)
async def get_execution(execution_id: str) -> ExecutionResponse:
    """
    Get execution by ID.

    Args:
        execution_id: Execution identifier

    Returns:
        Execution data

    Raises:
        HTTPException: If execution not found
    """
    if execution_id not in executions_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Execution {execution_id} not found",
        )

    return ExecutionResponse(**executions_db[execution_id])


@router.post(
    "/{execution_id}/cancel",
    response_model=ExecutionResponse,
    summary="Cancel execution",
    description="Cancel a running workflow execution",
)
async def cancel_execution(execution_id: str) -> ExecutionResponse:
    """
    Cancel execution.

    Args:
        execution_id: Execution identifier

    Returns:
        Updated execution

    Raises:
        HTTPException: If execution not found or cannot be cancelled
    """
    if execution_id not in executions_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Execution {execution_id} not found",
        )

    execution = executions_db[execution_id]

    if execution["status"] not in [ExecutionStatus.PENDING, ExecutionStatus.RUNNING]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel execution with status {execution['status']}",
        )

    execution["status"] = ExecutionStatus.CANCELLED
    execution["completed_at"] = datetime.now()
    execution["error"] = "Execution cancelled by user"

    return ExecutionResponse(**execution)


@router.delete(
    "/{execution_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete execution",
    description="Delete an execution record",
)
async def delete_execution(execution_id: str):
    """
    Delete execution.

    Args:
        execution_id: Execution identifier

    Raises:
        HTTPException: If execution not found
    """
    if execution_id not in executions_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Execution {execution_id} not found",
        )

    del executions_db[execution_id]
