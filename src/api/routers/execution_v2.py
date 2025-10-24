"""
Execution V2 API Router - MGE V2 Execution Endpoints

REST API endpoints for wave-based parallel execution with retry logic.

Author: DevMatrix Team
Date: 2025-10-24
"""

import uuid
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ...database import get_db
from ...services.execution_service_v2 import ExecutionServiceV2
from ...observability import StructuredLogger


logger = StructuredLogger("execution_v2_api", output_json=True)

router = APIRouter(prefix="/api/v2/execution", tags=["execution_v2"])


# Request/Response Models
class StartExecutionRequest(BaseModel):
    """Start execution request"""
    masterplan_id: str


class StartExecutionResponse(BaseModel):
    """Start execution response"""
    execution_started: bool
    masterplan_id: str
    status: str
    message: str


class ExecutionStatusResponse(BaseModel):
    """Execution status response"""
    masterplan_id: str
    status: str
    created_at: str
    completed_at: str = None
    total_atoms: int
    atoms_by_status: Dict[str, list]
    failed_atoms_detail: list
    retry_stats: Dict[str, Any]


class ExecutionProgressResponse(BaseModel):
    """Execution progress response"""
    masterplan_id: str
    masterplan_status: str
    total_atoms: int
    completed_atoms: int
    failed_atoms: int
    pending_atoms: int
    progress_percentage: float
    wave_executor_progress: Dict[str, Any]
    retry_stats: Dict[str, Any]


class RetryAtomRequest(BaseModel):
    """Retry atom request (empty body, uses atom_id from path)"""
    pass


class RetryAtomResponse(BaseModel):
    """Retry atom response"""
    atom_id: str
    retry_started: bool
    message: str


# ============================================================================
# Execution Endpoints
# ============================================================================

@router.post("/start", response_model=StartExecutionResponse)
async def start_execution(
    request: StartExecutionRequest,
    db: Session = Depends(get_db)
):
    """
    Start masterplan execution

    Args:
        request: StartExecutionRequest with masterplan_id
        db: Database session

    Returns:
        StartExecutionResponse with execution status

    Raises:
        HTTPException: If masterplan not found or execution fails
    """
    try:
        masterplan_id = uuid.UUID(request.masterplan_id)

        logger.info(
            f"Starting execution via API for masterplan {masterplan_id}",
            extra={"masterplan_id": str(masterplan_id)}
        )

        # Create execution service
        execution_service = ExecutionServiceV2(db=db)

        # Start execution
        result = await execution_service.start_execution(masterplan_id)

        return StartExecutionResponse(
            execution_started=True,
            masterplan_id=str(masterplan_id),
            status=result['status'],
            message=f"Execution completed: {result['successful_atoms']}/{result['total_atoms']} atoms successful"
        )

    except ValueError as e:
        logger.error(f"Invalid masterplan ID: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid masterplan_id: {str(e)}"
        )
    except Exception as e:
        logger.error(
            f"Execution failed for masterplan {request.masterplan_id}: {str(e)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Execution failed: {str(e)}"
        )


@router.get("/status/{masterplan_id}", response_model=ExecutionStatusResponse)
def get_execution_status(
    masterplan_id: str,
    db: Session = Depends(get_db)
):
    """
    Get detailed execution status for masterplan

    Args:
        masterplan_id: MasterPlan UUID
        db: Database session

    Returns:
        ExecutionStatusResponse with detailed status

    Raises:
        HTTPException: If masterplan not found
    """
    try:
        masterplan_uuid = uuid.UUID(masterplan_id)

        logger.debug(
            f"Getting execution status for masterplan {masterplan_uuid}",
            extra={"masterplan_id": str(masterplan_uuid)}
        )

        # Create execution service
        execution_service = ExecutionServiceV2(db=db)

        # Get status
        status_data = execution_service.get_execution_status(masterplan_uuid)

        return ExecutionStatusResponse(**status_data)

    except ValueError as e:
        logger.error(f"Invalid masterplan ID: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid masterplan_id: {str(e)}"
        )
    except Exception as e:
        logger.error(
            f"Failed to get status for masterplan {masterplan_id}: {str(e)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get status: {str(e)}"
        )


@router.get("/progress/{masterplan_id}", response_model=ExecutionProgressResponse)
def get_execution_progress(
    masterplan_id: str,
    db: Session = Depends(get_db)
):
    """
    Get real-time execution progress for masterplan

    Args:
        masterplan_id: MasterPlan UUID
        db: Database session

    Returns:
        ExecutionProgressResponse with progress metrics

    Raises:
        HTTPException: If masterplan not found
    """
    try:
        masterplan_uuid = uuid.UUID(masterplan_id)

        logger.debug(
            f"Getting execution progress for masterplan {masterplan_uuid}",
            extra={"masterplan_id": str(masterplan_uuid)}
        )

        # Create execution service
        execution_service = ExecutionServiceV2(db=db)

        # Get progress
        progress_data = execution_service.track_progress(masterplan_uuid)

        return ExecutionProgressResponse(**progress_data)

    except ValueError as e:
        logger.error(f"Invalid masterplan ID: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid masterplan_id: {str(e)}"
        )
    except Exception as e:
        logger.error(
            f"Failed to get progress for masterplan {masterplan_id}: {str(e)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get progress: {str(e)}"
        )


@router.post("/retry/{atom_id}", response_model=RetryAtomResponse)
async def retry_single_atom(
    atom_id: str,
    db: Session = Depends(get_db)
):
    """
    Manually retry a failed atom

    Args:
        atom_id: Atom UUID
        db: Database session

    Returns:
        RetryAtomResponse with retry status

    Raises:
        HTTPException: If atom not found or retry fails
    """
    try:
        atom_uuid = uuid.UUID(atom_id)

        logger.info(
            f"Manual retry requested for atom {atom_uuid}",
            extra={"atom_id": str(atom_uuid)}
        )

        # Load atom
        from ...models import AtomicUnit

        atom = db.query(AtomicUnit).filter(
            AtomicUnit.atom_id == atom_uuid
        ).first()

        if not atom:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Atom {atom_id} not found"
            )

        if atom.status != "failed":
            return RetryAtomResponse(
                atom_id=atom_id,
                retry_started=False,
                message=f"Atom status is '{atom.status}', not 'failed'. No retry needed."
            )

        # Create execution service and retry
        execution_service = ExecutionServiceV2(db=db)

        # Retry with attempt 1
        success, code, feedback = await execution_service.retry_orchestrator.retry_atom(
            atom=atom,
            error=atom.error_message or "Manual retry",
            attempt=1,
            code_generator=None  # Will use mock for manual retries
        )

        return RetryAtomResponse(
            atom_id=atom_id,
            retry_started=True,
            message=f"Retry {'succeeded' if success else 'failed'}: {feedback}"
        )

    except ValueError as e:
        logger.error(f"Invalid atom ID: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid atom_id: {str(e)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Retry failed for atom {atom_id}: {str(e)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Retry failed: {str(e)}"
        )


# ============================================================================
# Health Check
# ============================================================================

@router.get("/health")
def execution_health():
    """
    Execution service health check

    Returns:
        Health status
    """
    return {
        "service": "execution_v2",
        "status": "healthy",
        "version": "2.0.0"
    }
