"""
Execution V2 API Router - MGE V2 Execution Endpoints

DEPRECATED: This API is deprecated. Use /api/v1/orchestrate endpoints with cognitive pipeline instead.

REST API endpoints for wave-based parallel execution with intelligent retry orchestration.

Endpoints:
- POST /api/v2/execution/start - Start execution
- GET /api/v2/execution/{execution_id} - Get execution status
- GET /api/v2/execution/{execution_id}/progress - Get progress details
- GET /api/v2/execution/{execution_id}/waves/{wave_id} - Get wave status
- GET /api/v2/execution/{execution_id}/atoms/{atom_id} - Get atom status
- POST /api/v2/execution/{execution_id}/pause - Pause execution
- POST /api/v2/execution/{execution_id}/resume - Resume execution
- GET /api/v2/execution/{execution_id}/metrics - Get execution metrics

All endpoints return X-Deprecated header with migration information.

Author: DevMatrix Team
Date: 2025-10-25
"""

from typing import Dict, Any, Optional, List
from uuid import UUID
import warnings

from fastapi import APIRouter, HTTPException, status, Response
from pydantic import BaseModel, Field

from src.mge.v2.services.execution_service_v2 import (
    ExecutionServiceV2,
    ExecutionStatus,
)
from src.mge.v2.execution.wave_executor import WaveExecutor
from src.mge.v2.execution.retry_orchestrator import RetryOrchestrator
from src.observability import StructuredLogger


logger = StructuredLogger("execution_v2_api", output_json=True)

router = APIRouter(prefix="/api/v2/execution", tags=["execution-v2"])


# ============================================================================
# Deprecation Helper
# ============================================================================

DEPRECATION_MESSAGE = (
    "This API endpoint is deprecated. "
    "Use POST /api/v1/orchestrate with pipeline=cognitive instead. "
    "MGE V2 execution service will be removed in a future release."
)

def add_deprecation_warning(response: Response):
    """
    Add deprecation headers to response.

    Args:
        response: FastAPI Response object to add headers to
    """
    response.headers["X-Deprecated"] = "true"
    response.headers["X-Deprecation-Message"] = DEPRECATION_MESSAGE
    response.headers["X-Alternative-Endpoint"] = "/api/v1/orchestrate"

    # Also emit Python deprecation warning
    warnings.warn(
        DEPRECATION_MESSAGE,
        category=DeprecationWarning,
        stacklevel=2
    )


# ============================================================================
# Request/Response Models
# ============================================================================

class StartExecutionRequest(BaseModel):
    """Request to start execution for a masterplan"""
    masterplan_id: str = Field(..., description="Masterplan UUID")
    execution_plan: List[Dict[str, Any]] = Field(
        ..., description="List of execution waves"
    )
    atoms: Dict[str, Any] = Field(..., description="All atoms keyed by ID")


class StartExecutionResponse(BaseModel):
    """Response from start execution"""
    execution_id: str = Field(..., description="Execution UUID")
    masterplan_id: str = Field(..., description="Masterplan UUID")
    status: str = Field(..., description="Execution status")
    total_waves: int = Field(..., description="Total number of waves")
    atoms_total: int = Field(..., description="Total number of atoms")
    message: str = Field(..., description="Status message")


class ExecutionStatusResponse(BaseModel):
    """Response with execution status"""
    execution_id: str
    masterplan_id: str
    status: str
    current_wave: int
    total_waves: int
    atoms_completed: int
    atoms_total: int
    atoms_succeeded: int
    atoms_failed: int
    total_cost_usd: float
    total_time_seconds: float
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class ExecutionProgressResponse(BaseModel):
    """Response with execution progress details"""
    execution_id: str
    masterplan_id: str
    status: str
    completion_percent: float = Field(..., description="Overall completion %")
    precision_percent: float = Field(..., description="Success rate %")
    current_wave: int
    total_waves: int
    atoms_completed: int
    atoms_total: int
    atoms_succeeded: int
    atoms_failed: int


class WaveStatusResponse(BaseModel):
    """Response with wave status"""
    wave_id: int
    execution_id: str
    status: str
    current: bool = Field(..., description="Is this the current wave?")


class AtomStatusResponse(BaseModel):
    """Response with atom execution status"""
    atom_id: str
    execution_id: str
    success: bool
    attempts: int
    code: Optional[str] = None
    error: Optional[str] = None
    time_seconds: float


class PauseResumeResponse(BaseModel):
    """Response from pause/resume operation"""
    execution_id: str
    status: str
    message: str


class ExecutionMetricsResponse(BaseModel):
    """Response with execution metrics"""
    execution_id: str
    masterplan_id: str
    precision_percent: float
    atoms_total: int
    atoms_succeeded: int
    atoms_failed: int
    atoms_completed: int
    completion_percent: float
    current_wave: int
    total_waves: int
    total_cost_usd: float
    total_time_seconds: float
    status: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


# ============================================================================
# Service Singleton
# ============================================================================

# In-memory singleton for ExecutionServiceV2
# In production, this would be initialized with proper DI and persistence
_execution_service: Optional[ExecutionServiceV2] = None


def get_execution_service() -> ExecutionServiceV2:
    """
    Get or create ExecutionServiceV2 singleton.

    Returns:
        ExecutionServiceV2 instance
    """
    global _execution_service

    if _execution_service is None:
        # Initialize real LLM client
        from src.llm import EnhancedAnthropicClient
        from src.mge.v2.validation.atomic_validator import AtomicValidator
        from src.config.database import get_db
        import os

        # Get API key from environment
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            logger.warning("ANTHROPIC_API_KEY not set, MGE V2 execution may fail")

        # Get database session for validator
        db_session = next(get_db())

        # Initialize real components
        llm_client = EnhancedAnthropicClient(
            api_key=api_key,
            cost_optimization=True,  # Use Haiku for simple tasks
            enable_v2_caching=True,   # Enable MGE V2 caching
        )

        # Initialize validator with database session for real validation
        validator = AtomicValidator(db=db_session)

        retry_orchestrator = RetryOrchestrator(llm_client, validator)
        wave_executor = WaveExecutor(retry_orchestrator, max_concurrency=100)

        _execution_service = ExecutionServiceV2(wave_executor)

        logger.info("ExecutionServiceV2 initialized with real LLM client and validator")

    return _execution_service


# ============================================================================
# API Endpoints
# ============================================================================

# Health check - must be before /{execution_id} to avoid path collision
@router.get("/health")
def execution_v2_health() -> Dict[str, Any]:
    """
    Execution V2 service health check.

    Returns:
        Health status with service info
    """
    service = get_execution_service()
    executions = service.list_executions()

    return {
        "service": "execution_v2",
        "status": "healthy",
        "version": "2.0.0",
        "active_executions": len(executions)
    }


@router.post("/start", response_model=StartExecutionResponse, status_code=status.HTTP_202_ACCEPTED)
async def start_execution(request: StartExecutionRequest, response: Response) -> StartExecutionResponse:
    """
    Start execution for a masterplan.

    DEPRECATED: Use POST /api/v1/orchestrate with pipeline=cognitive instead.

    Starts background execution and returns immediately with execution_id.
    Use GET /{execution_id} to track progress.

    Args:
        request: StartExecutionRequest with masterplan_id, execution_plan, atoms

    Returns:
        StartExecutionResponse with execution_id and initial status

    Raises:
        HTTPException: 400 for invalid request, 500 for internal errors
    """
    # Add deprecation headers
    add_deprecation_warning(response)

    try:
        masterplan_id = UUID(request.masterplan_id)

        logger.info(
            f"🚀 Starting execution via API for masterplan {masterplan_id}",
            extra={"masterplan_id": str(masterplan_id)}
        )

        # Get service
        service = get_execution_service()

        # Start execution (returns immediately, runs in background)
        execution_id = await service.start_execution(
            masterplan_id=masterplan_id,
            execution_plan=request.execution_plan,
            atoms=request.atoms
        )

        # Get initial state
        state = service.get_execution_state(execution_id)

        logger.info(
            f"✅ Execution {execution_id} started for masterplan {masterplan_id}",
            extra={
                "execution_id": str(execution_id),
                "masterplan_id": str(masterplan_id),
                "total_waves": state.total_waves,
                "atoms_total": state.atoms_total
            }
        )

        return StartExecutionResponse(
            execution_id=str(execution_id),
            masterplan_id=str(masterplan_id),
            status=state.status.value,
            total_waves=state.total_waves,
            atoms_total=state.atoms_total,
            message=f"Execution started with {state.atoms_total} atoms across {state.total_waves} waves"
        )

    except ValueError as e:
        logger.error(f"Invalid request: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid request: {str(e)}"
        )
    except Exception as e:
        logger.error(
            f"Failed to start execution: {str(e)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start execution: {str(e)}"
        )


@router.get("/{execution_id}", response_model=ExecutionStatusResponse)
def get_execution_status(execution_id: str) -> ExecutionStatusResponse:
    """
    Get execution status.

    Args:
        execution_id: Execution UUID

    Returns:
        ExecutionStatusResponse with current status

    Raises:
        HTTPException: 404 if not found, 400 for invalid UUID
    """
    try:
        exec_uuid = UUID(execution_id)

        service = get_execution_service()
        state = service.get_execution_state(exec_uuid)

        if not state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Execution {execution_id} not found"
            )

        return ExecutionStatusResponse(
            execution_id=str(state.execution_id),
            masterplan_id=str(state.masterplan_id),
            status=state.status.value,
            current_wave=state.current_wave,
            total_waves=state.total_waves,
            atoms_completed=state.atoms_completed,
            atoms_total=state.atoms_total,
            atoms_succeeded=state.atoms_succeeded,
            atoms_failed=state.atoms_failed,
            total_cost_usd=state.total_cost_usd,
            total_time_seconds=state.total_time_seconds,
            started_at=state.started_at.isoformat() if state.started_at else None,
            completed_at=state.completed_at.isoformat() if state.completed_at else None
        )

    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid execution_id: {execution_id}"
        )


@router.get("/{execution_id}/progress", response_model=ExecutionProgressResponse)
def get_execution_progress(execution_id: str) -> ExecutionProgressResponse:
    """
    Get execution progress details.

    Args:
        execution_id: Execution UUID

    Returns:
        ExecutionProgressResponse with progress metrics

    Raises:
        HTTPException: 404 if not found, 400 for invalid UUID
    """
    try:
        exec_uuid = UUID(execution_id)

        service = get_execution_service()
        metrics = service.get_execution_metrics(exec_uuid)

        if not metrics:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Execution {execution_id} not found"
            )

        return ExecutionProgressResponse(
            execution_id=metrics["execution_id"],
            masterplan_id=metrics["masterplan_id"],
            status=metrics["status"],
            completion_percent=metrics["completion_percent"],
            precision_percent=metrics["precision_percent"],
            current_wave=metrics["current_wave"],
            total_waves=metrics["total_waves"],
            atoms_completed=metrics["atoms_completed"],
            atoms_total=metrics["atoms_total"],
            atoms_succeeded=metrics["atoms_succeeded"],
            atoms_failed=metrics["atoms_failed"]
        )

    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid execution_id: {execution_id}"
        )


@router.get("/{execution_id}/waves/{wave_id}", response_model=WaveStatusResponse)
def get_wave_status(execution_id: str, wave_id: int) -> WaveStatusResponse:
    """
    Get wave status.

    Args:
        execution_id: Execution UUID
        wave_id: Wave ID (0-indexed)

    Returns:
        WaveStatusResponse with wave status

    Raises:
        HTTPException: 404 if not found, 400 for invalid UUID
    """
    try:
        exec_uuid = UUID(execution_id)

        service = get_execution_service()
        wave_status = service.get_wave_status(exec_uuid, wave_id)

        if not wave_status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Wave {wave_id} not found for execution {execution_id}"
            )

        return WaveStatusResponse(**wave_status)

    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid execution_id: {execution_id}"
        )


@router.get("/{execution_id}/atoms/{atom_id}", response_model=AtomStatusResponse)
def get_atom_status(execution_id: str, atom_id: str) -> AtomStatusResponse:
    """
    Get atom execution status.

    Args:
        execution_id: Execution UUID
        atom_id: Atom UUID

    Returns:
        AtomStatusResponse with atom status

    Raises:
        HTTPException: 404 if not found, 400 for invalid UUID
    """
    try:
        exec_uuid = UUID(execution_id)
        atom_uuid = UUID(atom_id)

        service = get_execution_service()
        result = service.get_atom_status(exec_uuid, atom_uuid)

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Atom {atom_id} not found for execution {execution_id}"
            )

        return AtomStatusResponse(
            atom_id=str(result.atom_id),
            execution_id=str(exec_uuid),
            success=result.success,
            attempts=result.attempts,
            code=result.code,
            error=result.error_message,
            time_seconds=result.execution_time_seconds
        )

    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid execution_id or atom_id"
        )


@router.post("/{execution_id}/pause", response_model=PauseResumeResponse)
async def pause_execution(execution_id: str) -> PauseResumeResponse:
    """
    Pause execution.

    Args:
        execution_id: Execution UUID

    Returns:
        PauseResumeResponse with pause status

    Raises:
        HTTPException: 404 if not found, 400 for invalid UUID or state
    """
    try:
        exec_uuid = UUID(execution_id)

        service = get_execution_service()
        success = await service.pause_execution(exec_uuid)

        if not success:
            state = service.get_execution_state(exec_uuid)
            if not state:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Execution {execution_id} not found"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot pause execution in status: {state.status.value}"
                )

        logger.info(f"⏸️ Execution {execution_id} paused via API")

        return PauseResumeResponse(
            execution_id=execution_id,
            status="paused",
            message="Execution paused successfully"
        )

    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid execution_id: {execution_id}"
        )


@router.post("/{execution_id}/resume", response_model=PauseResumeResponse)
async def resume_execution(execution_id: str) -> PauseResumeResponse:
    """
    Resume paused execution.

    Args:
        execution_id: Execution UUID

    Returns:
        PauseResumeResponse with resume status

    Raises:
        HTTPException: 404 if not found, 400 for invalid UUID or state
    """
    try:
        exec_uuid = UUID(execution_id)

        service = get_execution_service()
        success = await service.resume_execution(exec_uuid)

        if not success:
            state = service.get_execution_state(exec_uuid)
            if not state:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Execution {execution_id} not found"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot resume execution in status: {state.status.value}"
                )

        logger.info(f"▶️ Execution {execution_id} resumed via API")

        return PauseResumeResponse(
            execution_id=execution_id,
            status="running",
            message="Execution resumed successfully"
        )

    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid execution_id: {execution_id}"
        )


@router.get("/{execution_id}/metrics", response_model=ExecutionMetricsResponse)
def get_execution_metrics(execution_id: str) -> ExecutionMetricsResponse:
    """
    Get execution metrics.

    Args:
        execution_id: Execution UUID

    Returns:
        ExecutionMetricsResponse with all metrics

    Raises:
        HTTPException: 404 if not found, 400 for invalid UUID
    """
    try:
        exec_uuid = UUID(execution_id)

        service = get_execution_service()
        metrics = service.get_execution_metrics(exec_uuid)

        if not metrics:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Execution {execution_id} not found"
            )

        return ExecutionMetricsResponse(**metrics)

    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid execution_id: {execution_id}"
        )
