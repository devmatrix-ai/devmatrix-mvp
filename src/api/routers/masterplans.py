"""
MasterPlan API Router

REST endpoints for listing and viewing MasterPlans.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime

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
from src.observability import StructuredLogger

router = APIRouter(prefix="/api/v1/masterplans", tags=["masterplans"])
logger = StructuredLogger("masterplans_router")


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
    return summary


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
