"""
Validation API Endpoints - MGE V2

FastAPI router for hierarchical validation operations.

Endpoints:
- POST /api/v2/validation/atom/{atom_id} - Validate atom
- POST /api/v2/validation/task/{task_id} - Validate task
- POST /api/v2/validation/milestone/{milestone_id} - Validate milestone
- POST /api/v2/validation/masterplan/{masterplan_id} - Validate masterplan
- POST /api/v2/validation/hierarchical/{masterplan_id} - Full hierarchical validation
- POST /api/v2/validation/batch/atoms - Batch validate atoms

Author: DevMatrix Team
Date: 2025-10-23
Updated: 2025-10-23 (Schema alignment)
"""

import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from src.config.database import get_db
from src.services.validation_service import ValidationService

# Create router
router = APIRouter(
    prefix="/api/v2",
    tags=["validation"],
)


# Request/Response Models
class BatchValidateAtomsRequest(BaseModel):
    """Request to batch validate atoms"""
    atom_ids: List[str] = Field(..., description="List of atom UUIDs")


class HierarchicalValidationRequest(BaseModel):
    """Request for hierarchical validation"""
    levels: Optional[List[str]] = Field(
        None,
        description="Levels to validate (atomic, task, milestone, masterplan)"
    )


# Endpoints

@router.post("/validation/atom/{atom_id}")
def validate_atom(
    atom_id: str,
    db: Session = Depends(get_db)
):
    """
    Validate individual atom (Level 1)

    Validates:
    - Syntax correctness
    - Semantic validity
    - Atomicity criteria
    - Type safety
    - Runtime safety

    Args:
        atom_id: Atom UUID

    Returns:
        Atomic validation result
    """
    try:
        # Convert string UUID to UUID
        atom_uuid = uuid.UUID(atom_id)

        # Create service
        service = ValidationService(db)

        # Validate atom
        result = service.validate_atom(atom_uuid)

        return result

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid atom_id: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Validation failed: {str(e)}"
        )


@router.post("/validation/task/{task_id}")
def validate_task(
    task_id: str,
    db: Session = Depends(get_db)
):
    """
    Validate task (Level 2)

    Validates:
    - Consistency between atoms
    - Integration coherence
    - Import resolution
    - Naming consistency
    - Task contracts

    Args:
        task_id: MasterPlanTask UUID

    Returns:
        Task validation result
    """
    try:
        # Convert string UUID to UUID
        task_uuid = uuid.UUID(task_id)

        # Create service
        service = ValidationService(db)

        # Validate task
        result = service.validate_task(task_uuid)

        return result

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid task_id: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Validation failed: {str(e)}"
        )


@router.post("/validation/milestone/{milestone_id}")
def validate_milestone(
    milestone_id: str,
    db: Session = Depends(get_db)
):
    """
    Validate milestone (Level 3)

    Validates:
    - Inter-task interfaces
    - Milestone contracts
    - API consistency
    - Task integration
    - Milestone dependencies

    Args:
        milestone_id: MasterPlanMilestone UUID

    Returns:
        Milestone validation result
    """
    try:
        # Convert string UUID to UUID
        milestone_uuid = uuid.UUID(milestone_id)

        # Create service
        service = ValidationService(db)

        # Validate milestone
        result = service.validate_milestone(milestone_uuid)

        return result

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid milestone_id: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Validation failed: {str(e)}"
        )


@router.post("/validation/masterplan/{masterplan_id}")
def validate_masterplan(
    masterplan_id: str,
    db: Session = Depends(get_db)
):
    """
    Validate entire masterplan (Level 4)

    Validates:
    - Architecture compliance
    - Cross-milestone dependencies
    - System-wide contracts
    - Performance characteristics
    - Security posture

    Args:
        masterplan_id: MasterPlan UUID

    Returns:
        MasterPlan validation result
    """
    try:
        # Convert string UUID to UUID
        masterplan_uuid = uuid.UUID(masterplan_id)

        # Create service
        service = ValidationService(db)

        # Validate masterplan
        result = service.validate_masterplan(masterplan_uuid)

        return result

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid masterplan_id: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Validation failed: {str(e)}"
        )


@router.post("/validation/hierarchical/{masterplan_id}")
def validate_hierarchical(
    masterplan_id: str,
    request: Optional[HierarchicalValidationRequest] = None,
    db: Session = Depends(get_db)
):
    """
    Validate all levels hierarchically

    Performs validation at all levels:
    1. Atomic: Validate all atoms
    2. Task: Validate all tasks
    3. Milestone: Validate all milestones
    4. MasterPlan: Validate entire masterplan

    Args:
        masterplan_id: MasterPlan UUID
        request: Optional request with specific levels to validate

    Returns:
        Combined hierarchical validation results
    """
    try:
        # Convert string UUID to UUID
        masterplan_uuid = uuid.UUID(masterplan_id)

        # Create service
        service = ValidationService(db)

        # Extract levels from request
        levels = request.levels if request else None

        # Validate hierarchically
        result = service.validate_hierarchical(masterplan_uuid, levels)

        return result

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid masterplan_id: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Validation failed: {str(e)}"
        )


@router.post("/validation/batch/atoms")
def batch_validate_atoms(
    request: BatchValidateAtomsRequest,
    db: Session = Depends(get_db)
):
    """
    Batch validate multiple atoms

    Validates multiple atoms in a single request.
    Useful for validating all atoms in a task or milestone.

    Args:
        request: Request with list of atom UUIDs

    Returns:
        Batch validation results
    """
    try:
        # Convert string UUIDs to UUIDs
        atom_uuids = [uuid.UUID(atom_id) for atom_id in request.atom_ids]

        # Create service
        service = ValidationService(db)

        # Batch validate
        result = service.batch_validate_atoms(atom_uuids)

        return result

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid atom_id: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch validation failed: {str(e)}"
        )
