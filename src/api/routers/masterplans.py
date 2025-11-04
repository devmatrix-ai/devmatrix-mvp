"""
MasterPlan API Router

REST endpoints for listing and viewing MasterPlans.
"""

from fastapi import APIRouter, HTTPException, Query, Depends, BackgroundTasks
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel

from src.config.database import get_db
from src.models.masterplan import (
    MasterPlan,
    MasterPlanPhase,
    MasterPlanMilestone,
    MasterPlanTask,
    MasterPlanStatus,
    PhaseType,
    TaskStatus
)
from src.services.masterplan_generator import MasterPlanGenerator
from src.services.masterplan_execution_service import MasterplanExecutionService
from src.api.middleware.auth_middleware import get_current_user
from src.observability import StructuredLogger

router = APIRouter(prefix="/api/v1/masterplans", tags=["masterplans"])
logger = StructuredLogger("masterplans_router")


# Request/Response Models
class CreateMasterPlanRequest(BaseModel):
    """Request to create a new masterplan from a discovery document."""
    discovery_id: str
    session_id: str

    class Config:
        json_schema_extra = {
            "example": {
                "discovery_id": "550e8400-e29b-41d4-a716-446655440000",
                "session_id": "sess_abc123"
            }
        }


class CreateMasterPlanResponse(BaseModel):
    """Response after creating a masterplan."""
    masterplan_id: str
    status: str
    message: str

    class Config:
        json_schema_extra = {
            "example": {
                "masterplan_id": "660e8400-e29b-41d4-a716-446655440000",
                "status": "pending",
                "message": "MasterPlan generation started"
            }
        }


class RejectMasterPlanRequest(BaseModel):
    """Request to reject a masterplan with optional reason."""
    rejection_reason: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "rejection_reason": "Tasks are too complex, needs simplification"
            }
        }


class ExecuteMasterPlanResponse(BaseModel):
    """Response after starting masterplan execution."""
    masterplan_id: str
    status: str
    workspace_id: str
    workspace_path: str
    total_tasks: int
    message: str

    class Config:
        json_schema_extra = {
            "example": {
                "masterplan_id": "660e8400-e29b-41d4-a716-446655440000",
                "status": "in_progress",
                "workspace_id": "masterplan_my_project",
                "workspace_path": "/absolute/path/to/workspace",
                "total_tasks": 42,
                "message": "Execution started successfully"
            }
        }


class MasterPlanStatusResponse(BaseModel):
    """Response for MasterPlan status check."""
    masterplan_id: str
    status: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    error_message: Optional[str] = None
    total_tasks: Optional[int] = None
    recovery_options: List[str] = []
    can_retry: bool = False
    can_execute: bool = False

    class Config:
        json_schema_extra = {
            "example": {
                "masterplan_id": "660e8400-e29b-41d4-a716-446655440000",
                "status": "in_progress",
                "created_at": "2025-11-04T10:30:00",
                "updated_at": "2025-11-04T10:45:00",
                "error_message": None,
                "total_tasks": 42,
                "recovery_options": ["view_details", "cancel"],
                "can_retry": False,
                "can_execute": False
            }
        }


# Response Models
def serialize_subtask(subtask) -> Dict[str, Any]:
    """Serialize a MasterPlanSubtask to dict."""
    return {
        "subtask_id": str(subtask.subtask_id),
        "subtask_number": subtask.subtask_number,
        "name": subtask.name,
        "description": subtask.description,
        "status": subtask.status.value if subtask.status else "pending",
        "completed": subtask.completed,
        "completed_at": subtask.completed_at.isoformat() if subtask.completed_at else None,
    }


def serialize_task(task) -> Dict[str, Any]:
    """Serialize a MasterPlanTask to dict."""
    return {
        "task_id": str(task.task_id),
        "task_number": task.task_number,
        "name": task.name,
        "description": task.description,
        "status": task.status.value if task.status else "pending",
        "complexity": task.complexity.value if task.complexity else "medium",
        "task_type": task.task_type,
        "depends_on_tasks": task.depends_on_tasks or [],
        "target_files": task.target_files or [],
        "modified_files": task.modified_files or [],
        "llm_cost_usd": task.llm_cost_usd,
        "validation_passed": task.validation_passed,
        "retry_count": task.retry_count,
        "subtasks": [serialize_subtask(subtask) for subtask in sorted(task.subtasks, key=lambda s: s.subtask_number)] if task.subtasks else [],
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        "failed_at": task.failed_at.isoformat() if task.failed_at else None,
    }


def serialize_milestone(milestone) -> Dict[str, Any]:
    """Serialize a MasterPlanMilestone to dict."""
    return {
        "milestone_id": str(milestone.milestone_id),
        "milestone_number": milestone.milestone_number,
        "name": milestone.name,
        "description": milestone.description,
        "total_tasks": milestone.total_tasks,
        "completed_tasks": milestone.completed_tasks,
        "progress_percent": milestone.progress_percent,
        "depends_on_milestones": milestone.depends_on_milestones or [],
        "tasks": [serialize_task(task) for task in sorted(milestone.tasks, key=lambda t: t.task_number)],
        "started_at": milestone.started_at.isoformat() if milestone.started_at else None,
        "completed_at": milestone.completed_at.isoformat() if milestone.completed_at else None,
    }


def serialize_phase(phase) -> Dict[str, Any]:
    """Serialize a MasterPlanPhase to dict."""
    return {
        "phase_id": str(phase.phase_id),
        "phase_type": phase.phase_type.value,
        "phase_number": phase.phase_number,
        "name": phase.name,
        "description": phase.description,
        "total_milestones": phase.total_milestones,
        "total_tasks": phase.total_tasks,
        "completed_tasks": phase.completed_tasks,
        "progress_percent": phase.progress_percent,
        "milestones": [serialize_milestone(m) for m in sorted(phase.milestones, key=lambda m: m.milestone_number)],
        "created_at": phase.created_at.isoformat() if phase.created_at else None,
        "started_at": phase.started_at.isoformat() if phase.started_at else None,
        "completed_at": phase.completed_at.isoformat() if phase.completed_at else None,
    }


def serialize_masterplan_summary(masterplan: MasterPlan) -> Dict[str, Any]:
    """Serialize MasterPlan summary (for list view)."""
    return {
        "masterplan_id": str(masterplan.masterplan_id),
        "project_name": masterplan.project_name,
        "description": masterplan.description,
        "status": masterplan.status.value,
        "total_phases": masterplan.total_phases,
        "total_milestones": masterplan.total_milestones,
        "total_tasks": masterplan.total_tasks,
        "completed_tasks": masterplan.completed_tasks,
        "progress_percent": masterplan.progress_percent,
        "tech_stack": masterplan.tech_stack,
        "estimated_cost_usd": masterplan.estimated_cost_usd,
        "estimated_duration_minutes": masterplan.estimated_duration_minutes,
        "generation_cost_usd": masterplan.generation_cost_usd,
        "created_at": masterplan.created_at.isoformat(),
        "started_at": masterplan.started_at.isoformat() if masterplan.started_at else None,
        "completed_at": masterplan.completed_at.isoformat() if masterplan.completed_at else None,
    }


def serialize_masterplan_detail(masterplan: MasterPlan) -> Dict[str, Any]:
    """Serialize complete MasterPlan with all relationships."""
    summary = serialize_masterplan_summary(masterplan)
    summary["phases"] = [serialize_phase(p) for p in sorted(masterplan.phases, key=lambda p: p.phase_number)]
    summary["discovery_id"] = str(masterplan.discovery_id)
    summary["session_id"] = masterplan.session_id
    summary["user_id"] = masterplan.user_id
    summary["architecture_style"] = masterplan.architecture_style
    summary["llm_model"] = masterplan.llm_model
    summary["generation_tokens"] = masterplan.generation_tokens
    summary["version"] = masterplan.version
    summary["updated_at"] = masterplan.updated_at.isoformat() if masterplan.updated_at else None
    summary["workspace_path"] = masterplan.workspace_path
    return summary


@router.post("", response_model=CreateMasterPlanResponse)
async def create_masterplan(
    request: CreateMasterPlanRequest,
    current_user = Depends(get_current_user)
) -> CreateMasterPlanResponse:
    """
    Create a new MasterPlan from a Discovery Document.

    This endpoint initiates the generation of a complete MasterPlan from an existing
    Discovery Document. The generation happens asynchronously, and progress updates
    are sent via WebSocket.

    Args:
        request: Contains discovery_id and session_id
        current_user: Authenticated user from JWT token

    Returns:
        CreateMasterPlanResponse with the new masterplan_id and status

    Raises:
        HTTPException 400: If discovery_id is invalid
        HTTPException 404: If discovery document not found
        HTTPException 500: If generation fails
    """
    try:
        logger.info(
            "Creating masterplan",
            extra={
                "discovery_id": request.discovery_id,
                "session_id": request.session_id,
                "user_id": current_user.user_id
            }
        )

        # Validate discovery_id format
        try:
            discovery_uuid = UUID(request.discovery_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid discovery_id format")

        # Initialize MasterPlan generator with WebSocket manager for real-time progress updates
        # Import here to avoid circular imports
        from src.api.routers.websocket import ws_manager
        generator = MasterPlanGenerator(websocket_manager=ws_manager)

        # Generate masterplan (async)
        masterplan_id = await generator.generate_masterplan(
            discovery_id=discovery_uuid,
            session_id=request.session_id,
            user_id=str(current_user.user_id)
        )

        logger.info(
            "MasterPlan created successfully",
            extra={
                "masterplan_id": str(masterplan_id),
                "discovery_id": request.discovery_id
            }
        )

        return CreateMasterPlanResponse(
            masterplan_id=str(masterplan_id),
            status="completed",
            message="MasterPlan generated successfully"
        )

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        logger.error(f"Generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error creating masterplan: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("")
async def list_masterplans(
    limit: int = Query(50, ge=1, le=100, description="Number of masterplans to return"),
    offset: int = Query(0, ge=0, description="Number of masterplans to skip"),
    status: Optional[str] = Query(None, description="Filter by status"),
) -> Dict[str, Any]:
    """
    List MasterPlans with pagination.

    Returns:
        {
            "masterplans": [...],
            "total": 123,
            "limit": 50,
            "offset": 0
        }
    """
    try:
        logger.info(f"Listing masterplans", extra={"limit": limit, "offset": offset, "status": status})

        db = next(get_db())

        # Build query
        query = db.query(MasterPlan)

        # Filter by status if provided
        if status:
            try:
                status_enum = MasterPlanStatus(status)
                query = query.filter(MasterPlan.status == status_enum)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

        # Get total count
        total = query.count()

        # Apply pagination and ordering
        masterplans = query.order_by(MasterPlan.created_at.desc()).offset(offset).limit(limit).all()

        # Serialize
        result = {
            "masterplans": [serialize_masterplan_summary(mp) for mp in masterplans],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

        logger.info(f"Listed {len(masterplans)} masterplans", extra={"total": total})

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing masterplans: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{masterplan_id}")
async def get_masterplan(masterplan_id: str) -> Dict[str, Any]:
    """
    Get complete MasterPlan with all phases, milestones, and tasks.

    Returns:
        Complete MasterPlan object with nested structure
    """
    try:
        logger.info(f"Getting masterplan {masterplan_id}")

        # Validate UUID
        try:
            masterplan_uuid = UUID(masterplan_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid masterplan_id format")

        db = next(get_db())

        # Query with eager loading of all relationships
        masterplan = (
            db.query(MasterPlan)
            .filter(MasterPlan.masterplan_id == masterplan_uuid)
            .first()
        )

        if not masterplan:
            raise HTTPException(status_code=404, detail=f"MasterPlan {masterplan_id} not found")

        # Serialize complete object
        result = serialize_masterplan_detail(masterplan)

        logger.info(f"Retrieved masterplan {masterplan_id}", extra={"project_name": masterplan.project_name})

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting masterplan {masterplan_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{masterplan_id}/approve")
async def approve_masterplan(masterplan_id: str) -> Dict[str, Any]:
    """
    Approve a draft MasterPlan.

    Changes the masterplan status from 'draft' to 'approved', allowing it to be executed.

    Args:
        masterplan_id: UUID of the masterplan to approve

    Returns:
        Updated masterplan detail with status='approved'

    Raises:
        HTTPException 400: If masterplan_id format is invalid or status is not 'draft'
        HTTPException 404: If masterplan not found
        HTTPException 500: If database update fails
    """
    try:
        logger.info(f"Approving masterplan {masterplan_id}")

        # Validate UUID
        try:
            masterplan_uuid = UUID(masterplan_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid masterplan_id format")

        db = next(get_db())

        # Query masterplan
        masterplan = (
            db.query(MasterPlan)
            .filter(MasterPlan.masterplan_id == masterplan_uuid)
            .first()
        )

        if not masterplan:
            raise HTTPException(status_code=404, detail=f"MasterPlan {masterplan_id} not found")

        # Validate status is 'draft'
        if masterplan.status != MasterPlanStatus.DRAFT:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot approve masterplan with status '{masterplan.status.value}'. Only draft masterplans can be approved."
            )

        # Update status to approved
        masterplan.status = MasterPlanStatus.APPROVED
        masterplan.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(masterplan)

        logger.info(
            f"Masterplan approved successfully",
            extra={
                "masterplan_id": masterplan_id,
                "project_name": masterplan.project_name
            }
        )

        # Return updated masterplan
        return serialize_masterplan_detail(masterplan)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error approving masterplan {masterplan_id}: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{masterplan_id}/reject")
async def reject_masterplan(
    masterplan_id: str,
    request: Optional[RejectMasterPlanRequest] = None
) -> Dict[str, Any]:
    """
    Reject a draft MasterPlan.

    Changes the masterplan status from 'draft' to 'rejected'. Optionally accepts a rejection reason.

    Args:
        masterplan_id: UUID of the masterplan to reject
        request: Optional rejection reason

    Returns:
        Updated masterplan detail with status='rejected'

    Raises:
        HTTPException 400: If masterplan_id format is invalid or status is not 'draft'
        HTTPException 404: If masterplan not found
        HTTPException 500: If database update fails
    """
    try:
        logger.info(
            f"Rejecting masterplan {masterplan_id}",
            extra={"rejection_reason": request.rejection_reason if request else None}
        )

        # Validate UUID
        try:
            masterplan_uuid = UUID(masterplan_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid masterplan_id format")

        db = next(get_db())

        # Query masterplan
        masterplan = (
            db.query(MasterPlan)
            .filter(MasterPlan.masterplan_id == masterplan_uuid)
            .first()
        )

        if not masterplan:
            raise HTTPException(status_code=404, detail=f"MasterPlan {masterplan_id} not found")

        # Validate status is 'draft'
        if masterplan.status != MasterPlanStatus.DRAFT:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot reject masterplan with status '{masterplan.status.value}'. Only draft masterplans can be rejected."
            )

        # Update status to rejected
        masterplan.status = MasterPlanStatus.REJECTED
        masterplan.updated_at = datetime.utcnow()

        # Store rejection reason if provided (could be added to model in future)
        # For now, we'll just log it
        if request and request.rejection_reason:
            logger.info(
                f"Rejection reason for masterplan {masterplan_id}",
                extra={"rejection_reason": request.rejection_reason}
            )

        db.commit()
        db.refresh(masterplan)

        logger.info(
            f"Masterplan rejected successfully",
            extra={
                "masterplan_id": masterplan_id,
                "project_name": masterplan.project_name
            }
        )

        # Return updated masterplan
        return serialize_masterplan_detail(masterplan)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rejecting masterplan {masterplan_id}: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{masterplan_id}/execute", response_model=ExecuteMasterPlanResponse)
async def execute_masterplan(
    masterplan_id: str,
    background_tasks: BackgroundTasks
) -> ExecuteMasterPlanResponse:
    """
    Execute an approved MasterPlan.

    Creates a workspace and starts asynchronous execution of all tasks in the masterplan.
    Tasks execute in dependency order using topological sort. Updates status to 'in_progress'.

    Args:
        masterplan_id: UUID of the masterplan to execute
        background_tasks: FastAPI background tasks for async execution

    Returns:
        ExecuteMasterPlanResponse with workspace details and total task count

    Raises:
        HTTPException 400: If masterplan_id format is invalid or status is not 'approved'
        HTTPException 404: If masterplan not found
        HTTPException 500: If workspace creation or execution fails
    """
    try:
        logger.info(f"Executing masterplan {masterplan_id}")

        # Validate UUID
        try:
            masterplan_uuid = UUID(masterplan_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid masterplan_id format")

        db = next(get_db())

        # Query masterplan with all relationships
        masterplan = (
            db.query(MasterPlan)
            .filter(MasterPlan.masterplan_id == masterplan_uuid)
            .first()
        )

        if not masterplan:
            raise HTTPException(status_code=404, detail=f"MasterPlan {masterplan_id} not found")

        # Validate status is 'approved'
        if masterplan.status != MasterPlanStatus.APPROVED:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot execute masterplan with status '{masterplan.status.value}'. Only approved masterplans can be executed."
            )

        # Initialize execution service
        execution_service = MasterplanExecutionService(db_session=db)

        # Create workspace
        try:
            workspace_path = execution_service.create_workspace(masterplan_uuid)
        except ValueError as e:
            logger.error(f"Failed to create workspace: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to create workspace: {e}")

        # Update masterplan status to in_progress
        masterplan.status = MasterPlanStatus.IN_PROGRESS
        masterplan.started_at = datetime.utcnow()
        masterplan.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(masterplan)

        # Extract workspace_id from workspace_path (last directory name)
        workspace_id = workspace_path.split('/')[-1] if '/' in workspace_path else workspace_path

        # Start async execution in background
        background_tasks.add_task(
            execution_service.execute,
            masterplan_uuid
        )

        logger.info(
            f"Masterplan execution started successfully",
            extra={
                "masterplan_id": masterplan_id,
                "workspace_path": workspace_path,
                "workspace_id": workspace_id,
                "total_tasks": masterplan.total_tasks
            }
        )

        return ExecuteMasterPlanResponse(
            masterplan_id=str(masterplan_uuid),
            status="in_progress",
            workspace_id=workspace_id,
            workspace_path=workspace_path,
            total_tasks=masterplan.total_tasks,
            message="Execution started successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing masterplan {masterplan_id}: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{masterplan_id}/status", response_model=MasterPlanStatusResponse)
async def get_masterplan_status(
    masterplan_id: str,
) -> MasterPlanStatusResponse:
    """
    Get current status and recovery information for a MasterPlan.

    Provides detailed status information including:
    - Current generation/execution status
    - Creation and last update timestamps
    - Error details if generation failed
    - Available recovery/retry options
    - Flags indicating possible next actions

    Args:
        masterplan_id: UUID of the masterplan

    Returns:
        MasterPlanStatusResponse with current status and recovery options

    Raises:
        HTTPException 400: If masterplan_id format is invalid
        HTTPException 404: If masterplan not found
        HTTPException 500: If database query fails
    """
    try:
        logger.info(f"Checking status for masterplan {masterplan_id}")

        # Validate UUID
        try:
            masterplan_uuid = UUID(masterplan_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid masterplan_id format")

        db = next(get_db())

        # Query masterplan
        masterplan = (
            db.query(MasterPlan)
            .filter(MasterPlan.masterplan_id == masterplan_uuid)
            .first()
        )

        if not masterplan:
            raise HTTPException(status_code=404, detail=f"MasterPlan {masterplan_id} not found")

        # Determine recovery options based on status
        recovery_options = []
        can_retry = False
        can_execute = False

        if masterplan.status == MasterPlanStatus.DRAFT:
            recovery_options = ["approve", "reject"]
        elif masterplan.status == MasterPlanStatus.APPROVED:
            recovery_options = ["execute", "reject"]
            can_execute = True
        elif masterplan.status == MasterPlanStatus.IN_PROGRESS:
            recovery_options = ["view_details", "cancel"]
        elif masterplan.status == MasterPlanStatus.FAILED:
            recovery_options = ["retry", "view_details", "reject"]
            can_retry = True
        elif masterplan.status == MasterPlanStatus.COMPLETED:
            recovery_options = ["view_details", "export"]
        elif masterplan.status == MasterPlanStatus.PAUSED:
            recovery_options = ["resume", "cancel"]
        elif masterplan.status == MasterPlanStatus.CANCELLED:
            recovery_options = ["view_details"]
        elif masterplan.status == MasterPlanStatus.REJECTED:
            recovery_options = ["view_details"]

        logger.info(
            f"Status retrieved for masterplan {masterplan_id}",
            status=masterplan.status.value,
            recovery_options=recovery_options,
        )

        return MasterPlanStatusResponse(
            masterplan_id=str(masterplan_uuid),
            status=masterplan.status.value,
            created_at=masterplan.created_at,
            updated_at=masterplan.updated_at,
            error_message=getattr(masterplan, "error_message", None),
            total_tasks=masterplan.total_tasks,
            recovery_options=recovery_options,
            can_retry=can_retry,
            can_execute=can_execute,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking status for masterplan {masterplan_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
