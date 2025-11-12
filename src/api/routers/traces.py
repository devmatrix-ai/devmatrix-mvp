"""
API Endpoints for E2E Tracing

Provides access to atom execution traces and correlation dashboards.
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from uuid import UUID

from src.mge.v2.tracing import get_trace_collector, AtomTrace, TraceCorrelation

router = APIRouter(prefix="/api/v2/traces", tags=["tracing"])


@router.get("/{trace_id}", response_model=AtomTrace)
async def get_trace(trace_id: UUID):
    """
    Get trace by ID.

    Args:
        trace_id: Trace UUID

    Returns:
        AtomTrace with complete execution flow

    Raises:
        404: Trace not found
    """
    collector = get_trace_collector()
    trace = collector.get_trace(trace_id)

    if not trace:
        raise HTTPException(
            status_code=404,
            detail=f"Trace {trace_id} not found"
        )

    return trace


@router.get("/atom/{atom_id}", response_model=AtomTrace)
async def get_trace_by_atom(atom_id: UUID):
    """
    Get trace for specific atom.

    Args:
        atom_id: Atom UUID

    Returns:
        AtomTrace with complete execution flow

    Raises:
        404: Trace not found for atom
    """
    collector = get_trace_collector()
    trace = collector.get_trace_by_atom(atom_id)

    if not trace:
        raise HTTPException(
            status_code=404,
            detail=f"No trace found for atom {atom_id}"
        )

    return trace


@router.get("/masterplan/{masterplan_id}", response_model=List[AtomTrace])
async def get_masterplan_traces(
    masterplan_id: UUID,
    limit: Optional[int] = Query(None, ge=1, le=1000, description="Limit number of traces returned"),
    status: Optional[str] = Query(None, description="Filter by status: success, failed, error")
):
    """
    Get all traces for a masterplan.

    Args:
        masterplan_id: Masterplan UUID
        limit: Optional limit on number of traces
        status: Optional status filter

    Returns:
        List of AtomTraces for the masterplan
    """
    collector = get_trace_collector()
    traces = collector.get_masterplan_traces(masterplan_id)

    # Filter by status if specified
    if status:
        traces = [t for t in traces if t.final_status == status]

    # Apply limit if specified
    if limit:
        traces = traces[:limit]

    return traces


@router.get("/masterplan/{masterplan_id}/correlations", response_model=TraceCorrelation)
async def get_correlations(masterplan_id: UUID):
    """
    Get correlation data for dashboard visualizations.

    Provides correlation analysis for:
    - Retries vs success rate
    - Validation issues vs success rate
    - Complexity vs execution time
    - Cost vs success rate
    - Acceptance tests vs final success

    Args:
        masterplan_id: Masterplan UUID

    Returns:
        TraceCorrelation with correlation metrics
    """
    collector = get_trace_collector()
    correlations = collector.calculate_correlations(masterplan_id)

    return correlations


@router.get("/masterplan/{masterplan_id}/summary")
async def get_masterplan_summary(masterplan_id: UUID):
    """
    Get summary statistics for masterplan traces.

    Args:
        masterplan_id: Masterplan UUID

    Returns:
        Dict with summary statistics
    """
    collector = get_trace_collector()
    traces = collector.get_masterplan_traces(masterplan_id)

    if not traces:
        return {
            "masterplan_id": str(masterplan_id),
            "total_atoms": 0,
            "success_count": 0,
            "failed_count": 0,
            "success_rate": 0.0,
            "avg_duration_ms": 0.0,
            "avg_retries": 0.0,
            "avg_cost_usd": 0.0
        }

    success_count = sum(1 for t in traces if t.final_status == "success")
    failed_count = sum(1 for t in traces if t.final_status == "failed")

    avg_duration = (
        sum(t.time.total_duration_ms for t in traces) / len(traces)
        if traces else 0.0
    )

    avg_retries = (
        sum(t.total_attempts for t in traces) / len(traces)
        if traces else 0.0
    )

    avg_cost = (
        sum(t.cost.llm_api_cost_usd for t in traces) / len(traces)
        if traces else 0.0
    )

    return {
        "masterplan_id": str(masterplan_id),
        "total_atoms": len(traces),
        "success_count": success_count,
        "failed_count": failed_count,
        "success_rate": (success_count / len(traces) * 100) if traces else 0.0,
        "avg_duration_ms": avg_duration,
        "avg_retries": avg_retries,
        "avg_cost_usd": avg_cost,
        "total_cost_usd": sum(t.cost.llm_api_cost_usd for t in traces)
    }


@router.delete("/masterplan/{masterplan_id}")
async def clear_masterplan_traces(masterplan_id: UUID):
    """
    Clear traces for a masterplan.

    Args:
        masterplan_id: Masterplan UUID

    Returns:
        Success message
    """
    collector = get_trace_collector()
    collector.clear_traces(masterplan_id)

    return {"message": f"Cleared traces for masterplan {masterplan_id}"}


@router.delete("/all")
async def clear_all_traces():
    """
    Clear all traces from memory.

    Returns:
        Success message
    """
    collector = get_trace_collector()
    collector.clear_traces()

    return {"message": "Cleared all traces"}
