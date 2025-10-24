"""
Execution API Endpoints - MGE V2

FastAPI router for code execution operations.

Endpoints:
- POST /api/v2/execution/atom/{atom_id} - Execute single atom
- POST /api/v2/execution/wave/{masterplan_id}/{wave_number} - Execute wave
- POST /api/v2/execution/masterplan/{masterplan_id} - Execute masterplan
- GET /api/v2/execution/summary/{masterplan_id} - Get execution summary
- GET /api/v2/execution/metrics - Get execution metrics

Author: DevMatrix Team
Date: 2025-10-23
"""

import uuid
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from src.config.database import get_db
from src.services.execution_service import ExecutionService

# Create router
router = APIRouter(
    prefix="/api/v2",
    tags=["execution"],
)


# Request/Response Models
class ExecuteAtomRequest(BaseModel):
    """Request to execute atom"""
    input_data: Optional[Dict[str, Any]] = Field(None, description="Optional input data")


class ExecuteMasterplanRequest(BaseModel):
    """Request to execute masterplan"""
    execute_by_waves: bool = Field(True, description="Execute using dependency waves")


# Endpoints

@router.post("/execution/atom/{atom_id}")
def execute_atom(
    atom_id: str,
    request: Optional[ExecuteAtomRequest] = None,
    db: Session = Depends(get_db)
):
    """Execute single atom"""
    try:
        atom_uuid = uuid.UUID(atom_id)
        service = ExecutionService(db)

        input_data = request.input_data if request else None
        result = service.execute_atom(atom_uuid, input_data)

        return result

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid atom_id: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Execution failed: {str(e)}"
        )


@router.post("/execution/wave/{masterplan_id}/{wave_number}")
def execute_wave(
    masterplan_id: str,
    wave_number: int,
    db: Session = Depends(get_db)
):
    """Execute specific wave"""
    try:
        masterplan_uuid = uuid.UUID(masterplan_id)
        service = ExecutionService(db)

        result = service.execute_wave(masterplan_uuid, wave_number)
        return result

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid masterplan_id: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Wave execution failed: {str(e)}"
        )


@router.post("/execution/masterplan/{masterplan_id}")
def execute_masterplan(
    masterplan_id: str,
    request: Optional[ExecuteMasterplanRequest] = None,
    db: Session = Depends(get_db)
):
    """Execute entire masterplan"""
    try:
        masterplan_uuid = uuid.UUID(masterplan_id)
        service = ExecutionService(db)

        execute_by_waves = request.execute_by_waves if request else True
        result = service.execute_masterplan(masterplan_uuid, execute_by_waves)

        return result

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid masterplan_id: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Masterplan execution failed: {str(e)}"
        )


@router.get("/execution/summary/{masterplan_id}")
def get_execution_summary(
    masterplan_id: str,
    db: Session = Depends(get_db)
):
    """Get execution summary"""
    try:
        masterplan_uuid = uuid.UUID(masterplan_id)
        service = ExecutionService(db)

        summary = service.get_execution_summary(masterplan_uuid)
        return summary

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid masterplan_id: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get summary: {str(e)}"
        )


@router.get("/execution/metrics")
def get_execution_metrics(db: Session = Depends(get_db)):
    """Get execution metrics"""
    try:
        service = ExecutionService(db)
        metrics = service.monitoring.get_summary()

        return metrics

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get metrics: {str(e)}"
        )
