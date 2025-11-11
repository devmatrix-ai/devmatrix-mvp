"""
Traceability API Router

Endpoints for querying atom traces and E2E causal analysis.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from src.config.database import get_db
from src.traceability.trace_manager import TraceManager


router = APIRouter(prefix="/traceability", tags=["traceability"])


class AtomTraceResponse(BaseModel):
    """Atom trace response model."""
    atom_id: str
    masterplan_id: str
    atom_number: int
    description: str
    status: str
    context: dict
    validation: dict
    acceptance: dict
    retry: dict
    cost: dict
    timing: dict


class MasterplanStatsResponse(BaseModel):
    """Masterplan aggregate statistics."""
    total_atoms: int
    completed: int
    failed: int
    total_cost_usd: float
    total_time_seconds: float
    avg_cost_per_atom: float
    avg_time_per_atom: float
    total_llm_tokens: int
    total_retries: int
    cache_hit_rate: float


@router.get(
    "/atom/{atom_id}",
    response_model=AtomTraceResponse,
    summary="Get atom trace",
    description="Get complete E2E trace for an atom"
)
async def get_atom_trace(
    atom_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get complete E2E trace for an atom.

    Includes:
    - Context used (RAG, dependencies)
    - L1-L4 validation results
    - Acceptance test results
    - Retry attempts
    - Cost and timing breakdown

    Args:
        atom_id: Atom UUID

    Returns:
        Complete atom trace
    """
    trace_manager = TraceManager(db)
    trace = trace_manager.get_trace(atom_id)

    if not trace:
        raise HTTPException(
            status_code=404,
            detail=f"Trace not found for atom {atom_id}"
        )

    return AtomTraceResponse(**trace.to_dict())


@router.get(
    "/masterplan/{masterplan_id}",
    summary="Get masterplan traces",
    description="Get all atom traces for a masterplan"
)
async def get_masterplan_traces(
    masterplan_id: UUID,
    format: str = Query("json", regex="^(json|csv)$"),
    db: Session = Depends(get_db)
):
    """
    Get all atom traces for a masterplan.

    Args:
        masterplan_id: MasterPlan UUID
        format: Export format ('json' or 'csv')

    Returns:
        Traces in requested format
    """
    trace_manager = TraceManager(db)
    exported = trace_manager.export_traces(masterplan_id, format=format)

    if format == "json":
        import json
        return json.loads(exported)
    else:  # csv
        from fastapi.responses import Response
        return Response(
            content=exported,
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=traces_{masterplan_id}.csv"
            }
        )


@router.get(
    "/masterplan/{masterplan_id}/stats",
    response_model=MasterplanStatsResponse,
    summary="Get masterplan statistics",
    description="Get aggregate statistics for all atoms in masterplan"
)
async def get_masterplan_stats(
    masterplan_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get aggregate statistics for masterplan.

    Includes:
    - Total atoms, completed, failed
    - Total cost and time
    - Average cost and time per atom
    - Total LLM tokens used
    - Total retry attempts
    - Cache hit rate

    Args:
        masterplan_id: MasterPlan UUID

    Returns:
        Aggregate statistics
    """
    trace_manager = TraceManager(db)
    stats = trace_manager.get_aggregate_stats(masterplan_id)

    return MasterplanStatsResponse(**stats)


@router.get(
    "/masterplan/{masterplan_id}/correlation",
    summary="Get correlation data",
    description="Get data for correlation analysis (context size vs validation, retries vs cost, etc.)"
)
async def get_correlation_data(
    masterplan_id: UUID,
    x_axis: str = Query(..., regex="^(context_size|validation_time|retries|cost)$"),
    y_axis: str = Query(..., regex="^(validation_passed|acceptance_rate|cost|time)$"),
    db: Session = Depends(get_db)
):
    """
    Get correlation data for analysis.

    Common correlations:
    - Context size vs validation success
    - Retry count vs cost
    - Validation time vs acceptance rate

    Args:
        masterplan_id: MasterPlan UUID
        x_axis: X-axis metric
        y_axis: Y-axis metric

    Returns:
        List of {x, y} data points for scatter plot
    """
    trace_manager = TraceManager(db)
    traces = trace_manager.get_masterplan_traces(masterplan_id)

    data_points = []

    for trace in traces:
        # Extract X value
        if x_axis == "context_size":
            x = trace.context.context_size_bytes
        elif x_axis == "validation_time":
            x = trace.timing.validation_seconds
        elif x_axis == "retries":
            x = trace.retry.total_attempts
        elif x_axis == "cost":
            x = trace.cost.total_cost_usd
        else:
            x = 0

        # Extract Y value
        if y_axis == "validation_passed":
            y = 1 if all([
                trace.validation.l1_syntax,
                trace.validation.l2_imports,
                trace.validation.l3_types,
                trace.validation.l4_complexity
            ]) else 0
        elif y_axis == "acceptance_rate":
            y = (
                trace.acceptance.tests_passed / trace.acceptance.tests_executed
                if trace.acceptance.tests_executed > 0 else 0.0
            )
        elif y_axis == "cost":
            y = trace.cost.total_cost_usd
        elif y_axis == "time":
            y = trace.timing.total_seconds
        else:
            y = 0

        data_points.append({
            "atom_id": str(trace.atom_id),
            "atom_number": trace.atom_number,
            "x": x,
            "y": y
        })

    return {
        "masterplan_id": str(masterplan_id),
        "x_axis": x_axis,
        "y_axis": y_axis,
        "data_points": data_points,
        "count": len(data_points)
    }
