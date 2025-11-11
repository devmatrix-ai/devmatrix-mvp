"""
Acceptance Gate API Router

Provides endpoints for checking and reporting on Spec Conformance Gate (Gate S).
Enforces 100% MUST + ≥95% SHOULD requirements.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from src.core.deps import get_db_session
from src.testing.acceptance_gate import AcceptanceTestGate


router = APIRouter(prefix="/gate", tags=["acceptance-gate"])


class GateCheckResponse(BaseModel):
    """Response model for gate check."""
    gate_passed: bool
    must_pass_rate: float
    should_pass_rate: float
    must_total: int
    must_passed: int
    should_total: int
    should_passed: int
    can_release: bool
    gate_status: str
    failed_requirements: list


@router.get(
    "/{masterplan_id}",
    response_model=GateCheckResponse,
    summary="Check Spec Conformance Gate (Gate S)",
    description="Check if masterplan passes Gate S: 100% MUST + ≥95% SHOULD"
)
async def check_gate(
    masterplan_id: UUID,
    wave_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Check if masterplan passes Spec Conformance Gate (Gate S).

    **Gate S Rules:**
    - 100% MUST requirements → Required for release
    - ≥95% SHOULD requirements → Required for gate pass
    - Gate passed: Both thresholds met
    - Can release: MUST threshold met (even if SHOULD <95%)

    Args:
        masterplan_id: MasterPlan UUID
        wave_id: Optional wave UUID (check specific wave)

    Returns:
        Gate check results with pass rates and failed requirements
    """
    gate = AcceptanceTestGate(db)

    try:
        result = await gate.check_gate(masterplan_id, wave_id)
        return GateCheckResponse(**result)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error checking gate: {str(e)}"
        )


@router.get(
    "/{masterplan_id}/report",
    summary="Get detailed Gate S report",
    description="Get formatted report with detailed breakdown"
)
async def get_gate_report(
    masterplan_id: UUID,
    wave_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get detailed formatted Gate S report.

    Returns:
        Formatted text report with full gate analysis
    """
    gate = AcceptanceTestGate(db)

    try:
        report = await gate.get_gate_report(masterplan_id, wave_id)
        return {
            "masterplan_id": str(masterplan_id),
            "wave_id": str(wave_id) if wave_id else None,
            "report": report
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating gate report: {str(e)}"
        )


@router.get(
    "/{masterplan_id}/requirements/{status}",
    summary="Get requirements by status",
    description="Get requirements filtered by test status (pass, fail, timeout, error)"
)
async def get_requirements_by_status(
    masterplan_id: UUID,
    status: str,
    wave_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get requirements filtered by test status.

    Args:
        masterplan_id: MasterPlan UUID
        status: Test status ('pass', 'fail', 'timeout', 'error')
        wave_id: Optional wave UUID

    Returns:
        List of requirements matching the status
    """
    if status not in ['pass', 'fail', 'timeout', 'error']:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: pass, fail, timeout, error"
        )

    gate = AcceptanceTestGate(db)

    try:
        requirements = await gate.get_requirements_by_status(
            masterplan_id,
            status,
            wave_id
        )
        return {
            "masterplan_id": str(masterplan_id),
            "status": status,
            "count": len(requirements),
            "requirements": requirements
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching requirements: {str(e)}"
        )
