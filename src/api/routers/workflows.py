"""
Workflow Management Router

CRUD operations for workflow definitions.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field


router = APIRouter(prefix="/workflows", tags=["workflows"])


# Pydantic models for request/response
class TaskDefinition(BaseModel):
    """Task definition model."""
    task_id: str = Field(..., description="Unique task identifier")
    agent_type: str = Field(..., description="Type of agent to execute task")
    prompt: str = Field(..., description="Task prompt")
    dependencies: List[str] = Field(default_factory=list, description="Task dependencies")
    max_retries: int = Field(default=3, ge=0, le=10, description="Maximum retry attempts")
    timeout: int = Field(default=300, ge=1, le=3600, description="Task timeout in seconds")


class WorkflowCreate(BaseModel):
    """Workflow creation request."""
    name: str = Field(..., min_length=1, max_length=100, description="Workflow name")
    description: Optional[str] = Field(None, max_length=500, description="Workflow description")
    tasks: List[TaskDefinition] = Field(..., min_items=1, description="List of tasks")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")


class WorkflowUpdate(BaseModel):
    """Workflow update request."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    tasks: Optional[List[TaskDefinition]] = None
    metadata: Optional[Dict[str, Any]] = None


class WorkflowResponse(BaseModel):
    """Workflow response model."""
    workflow_id: str
    name: str
    description: Optional[str]
    tasks: List[TaskDefinition]
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime


# In-memory storage (replace with database in production)
workflows_db: Dict[str, Dict[str, Any]] = {}


@router.post(
    "",
    response_model=WorkflowResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new workflow",
    description="Create a new workflow definition with tasks and dependencies",
)
async def create_workflow(workflow: WorkflowCreate) -> WorkflowResponse:
    """
    Create a new workflow.

    Args:
        workflow: Workflow creation data

    Returns:
        Created workflow with ID and timestamps

    Raises:
        HTTPException: If workflow creation fails
    """
    import uuid

    workflow_id = str(uuid.uuid4())
    now = datetime.now()

    workflow_data = {
        "workflow_id": workflow_id,
        "name": workflow.name,
        "description": workflow.description,
        "tasks": [task.model_dump() for task in workflow.tasks],
        "metadata": workflow.metadata,
        "created_at": now,
        "updated_at": now,
    }

    workflows_db[workflow_id] = workflow_data

    return WorkflowResponse(**workflow_data)


@router.get(
    "",
    response_model=List[WorkflowResponse],
    summary="List all workflows",
    description="Retrieve all workflow definitions",
)
async def list_workflows() -> List[WorkflowResponse]:
    """
    List all workflows.

    Returns:
        List of all workflows
    """
    return [WorkflowResponse(**wf) for wf in workflows_db.values()]


@router.get(
    "/{workflow_id}",
    response_model=WorkflowResponse,
    summary="Get workflow by ID",
    description="Retrieve a specific workflow by its ID",
)
async def get_workflow(workflow_id: str) -> WorkflowResponse:
    """
    Get workflow by ID.

    Args:
        workflow_id: Workflow identifier

    Returns:
        Workflow data

    Raises:
        HTTPException: If workflow not found
    """
    if workflow_id not in workflows_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow {workflow_id} not found",
        )

    return WorkflowResponse(**workflows_db[workflow_id])


@router.put(
    "/{workflow_id}",
    response_model=WorkflowResponse,
    summary="Update workflow",
    description="Update an existing workflow definition",
)
async def update_workflow(
    workflow_id: str,
    workflow: WorkflowUpdate,
) -> WorkflowResponse:
    """
    Update workflow.

    Args:
        workflow_id: Workflow identifier
        workflow: Update data

    Returns:
        Updated workflow

    Raises:
        HTTPException: If workflow not found
    """
    if workflow_id not in workflows_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow {workflow_id} not found",
        )

    workflow_data = workflows_db[workflow_id]

    # Update fields
    if workflow.name is not None:
        workflow_data["name"] = workflow.name
    if workflow.description is not None:
        workflow_data["description"] = workflow.description
    if workflow.tasks is not None:
        workflow_data["tasks"] = [task.model_dump() for task in workflow.tasks]
    if workflow.metadata is not None:
        workflow_data["metadata"] = workflow.metadata

    workflow_data["updated_at"] = datetime.now()

    return WorkflowResponse(**workflow_data)


@router.delete(
    "/{workflow_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete workflow",
    description="Delete a workflow definition",
)
async def delete_workflow(workflow_id: str):
    """
    Delete workflow.

    Args:
        workflow_id: Workflow identifier

    Raises:
        HTTPException: If workflow not found
    """
    if workflow_id not in workflows_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow {workflow_id} not found",
        )

    del workflows_db[workflow_id]
