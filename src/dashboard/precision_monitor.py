"""
Precision Monitoring Dashboard

Real-time monitoring dashboard for MGE V2 precision metrics.

Features:
- Current precision vs target (98%)
- Determinism score tracking
- Phase progress visualization
- Recent execution history
- Regression alerts

API Endpoints:
- GET /api/dashboard/precision - Get current precision metrics
- GET /api/dashboard/history - Get execution history
- GET /api/dashboard/trends - Get precision trends
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from src.config.database import get_db
from src.models.masterplan import MasterPlan, MasterPlanTask, TaskStatus
from src.models.atomic_unit import AtomicUnit

logger = logging.getLogger(__name__)

# Router for dashboard endpoints
router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


# Response Models

class PrecisionMetrics(BaseModel):
    """Current precision metrics."""
    current_precision: float = Field(description="Current precision percentage")
    target_precision: float = Field(default=98.0, description="Target precision percentage")
    determinism_score: float = Field(description="Determinism percentage")
    phase: int = Field(description="Current implementation phase (1-5)")
    gap_to_target: float = Field(description="Gap to target percentage")
    total_executions: int = Field(description="Total executions tracked")
    last_updated: str = Field(description="Last update timestamp")


class ExecutionSummary(BaseModel):
    """Summary of a single execution."""
    execution_id: str
    masterplan_id: str
    project_name: str
    atoms_total: int
    atoms_succeeded: int
    atoms_failed: int
    precision_percent: float
    execution_time_seconds: Optional[float] = None
    cost_usd: Optional[float] = None
    started_at: str
    completed_at: Optional[str] = None
    status: str


class Alert(BaseModel):
    """Alert for precision regression or issues."""
    severity: str  # "info", "warning", "error"
    message: str
    timestamp: str
    details: Optional[Dict[str, Any]] = None


class DashboardResponse(BaseModel):
    """Complete dashboard response."""
    metrics: PrecisionMetrics
    last_executions: List[ExecutionSummary]
    alerts: List[Alert]


class TrendPoint(BaseModel):
    """Single trend data point."""
    timestamp: str
    precision: float
    determinism: float
    execution_count: int


class TrendsResponse(BaseModel):
    """Precision trends over time."""
    trends: List[TrendPoint]
    period: str  # "hour", "day", "week"


# Service Layer

class PrecisionMonitorService:
    """Service for tracking and reporting precision metrics."""

    def __init__(self, db: Session):
        self.db = db
        self.baseline_file = Path("./reports/precision/baseline_latest.json")

    def get_current_metrics(self) -> PrecisionMetrics:
        """
        Get current precision metrics.

        Calculates:
        - Current precision from recent executions
        - Determinism score from baseline measurements
        - Phase progress
        - Gap to target
        """
        # Get recent masterplan executions
        recent_masterplans = self.db.query(MasterPlan).filter(
            MasterPlan.completed_at.isnot(None)
        ).order_by(desc(MasterPlan.completed_at)).limit(10).all()

        if not recent_masterplans:
            # No executions yet - return defaults
            return PrecisionMetrics(
                current_precision=0.0,
                target_precision=98.0,
                determinism_score=0.0,
                phase=1,
                gap_to_target=98.0,
                total_executions=0,
                last_updated=datetime.utcnow().isoformat()
            )

        # Calculate average precision from recent executions
        precision_scores = []

        for mp in recent_masterplans:
            # Get atoms for this masterplan
            atoms = self.db.query(AtomicUnit).filter(
                AtomicUnit.masterplan_id == mp.masterplan_id
            ).all()

            if atoms:
                succeeded = sum(1 for a in atoms if a.status == "completed")
                total = len(atoms)
                precision = (succeeded / total * 100) if total > 0 else 0.0
                precision_scores.append(precision)

        current_precision = (
            sum(precision_scores) / len(precision_scores)
            if precision_scores
            else 0.0
        )

        # Load determinism score from baseline file
        determinism_score = self._load_determinism_score()

        # Determine current phase (based on precision)
        phase = self._calculate_phase(current_precision)

        # Calculate gap to target
        gap_to_target = max(0.0, 98.0 - current_precision)

        return PrecisionMetrics(
            current_precision=round(current_precision, 2),
            target_precision=98.0,
            determinism_score=round(determinism_score, 2),
            phase=phase,
            gap_to_target=round(gap_to_target, 2),
            total_executions=len(recent_masterplans),
            last_updated=datetime.utcnow().isoformat()
        )

    def get_execution_history(
        self,
        limit: int = 20,
        offset: int = 0
    ) -> List[ExecutionSummary]:
        """Get recent execution history."""
        masterplans = self.db.query(MasterPlan).filter(
            MasterPlan.started_at.isnot(None)
        ).order_by(desc(MasterPlan.started_at)).limit(limit).offset(offset).all()

        history = []

        for mp in masterplans:
            # Get atoms for this masterplan
            atoms = self.db.query(AtomicUnit).filter(
                AtomicUnit.masterplan_id == mp.masterplan_id
            ).all()

            atoms_total = len(atoms)
            atoms_succeeded = sum(1 for a in atoms if a.status == "completed")
            atoms_failed = sum(1 for a in atoms if a.status == "failed")

            precision = (
                (atoms_succeeded / atoms_total * 100)
                if atoms_total > 0
                else 0.0
            )

            history.append(ExecutionSummary(
                execution_id=str(mp.masterplan_id),
                masterplan_id=str(mp.masterplan_id),
                project_name=mp.project_name or "Unknown",
                atoms_total=atoms_total,
                atoms_succeeded=atoms_succeeded,
                atoms_failed=atoms_failed,
                precision_percent=round(precision, 2),
                execution_time_seconds=mp.actual_duration_minutes * 60 if mp.actual_duration_minutes else None,
                cost_usd=mp.actual_cost_usd,
                started_at=mp.started_at.isoformat() if mp.started_at else "",
                completed_at=mp.completed_at.isoformat() if mp.completed_at else None,
                status=mp.status.value if mp.status else "unknown"
            ))

        return history

    def get_alerts(self) -> List[Alert]:
        """
        Generate alerts based on current metrics.

        Alerts for:
        - Precision regression (drop > 5%)
        - Low determinism (< 80%)
        - High failure rate (> 20%)
        """
        alerts = []

        metrics = self.get_current_metrics()

        # Alert: Low precision
        if metrics.current_precision < 50.0:
            alerts.append(Alert(
                severity="error",
                message=f"Precision critically low: {metrics.current_precision}%",
                timestamp=datetime.utcnow().isoformat(),
                details={"current": metrics.current_precision, "threshold": 50.0}
            ))
        elif metrics.current_precision < 70.0:
            alerts.append(Alert(
                severity="warning",
                message=f"Precision below target: {metrics.current_precision}%",
                timestamp=datetime.utcnow().isoformat(),
                details={"current": metrics.current_precision, "threshold": 70.0}
            ))

        # Alert: Low determinism
        if metrics.determinism_score < 80.0:
            alerts.append(Alert(
                severity="warning",
                message=f"Low determinism detected: {metrics.determinism_score}%",
                timestamp=datetime.utcnow().isoformat(),
                details={"current": metrics.determinism_score, "threshold": 80.0}
            ))

        # Alert: Large gap to target
        if metrics.gap_to_target > 50.0:
            alerts.append(Alert(
                severity="info",
                message=f"Large gap to target: {metrics.gap_to_target}% improvement needed",
                timestamp=datetime.utcnow().isoformat(),
                details={"gap": metrics.gap_to_target, "target": 98.0}
            ))

        # Check for recent regressions
        regression_alert = self._check_regression()
        if regression_alert:
            alerts.append(regression_alert)

        return alerts

    def get_trends(self, period: str = "day") -> TrendsResponse:
        """
        Get precision trends over time.

        Args:
            period: "hour", "day", or "week"
        """
        # Calculate time range
        now = datetime.utcnow()

        if period == "hour":
            start_time = now - timedelta(hours=24)
            interval = timedelta(hours=1)
        elif period == "day":
            start_time = now - timedelta(days=7)
            interval = timedelta(days=1)
        elif period == "week":
            start_time = now - timedelta(weeks=12)
            interval = timedelta(weeks=1)
        else:
            raise ValueError(f"Invalid period: {period}")

        # Load baseline measurements
        baseline_data = self._load_baseline_data()

        # Generate trend points
        trends = []
        current = start_time

        while current <= now:
            # Get executions in this time window
            window_end = current + interval

            executions = self.db.query(MasterPlan).filter(
                MasterPlan.completed_at >= current,
                MasterPlan.completed_at < window_end
            ).all()

            if executions:
                # Calculate average precision for this window
                precision_scores = []

                for mp in executions:
                    atoms = self.db.query(AtomicUnit).filter(
                        AtomicUnit.masterplan_id == mp.masterplan_id
                    ).all()

                    if atoms:
                        succeeded = sum(1 for a in atoms if a.status == "completed")
                        precision = (succeeded / len(atoms) * 100) if atoms else 0.0
                        precision_scores.append(precision)

                avg_precision = (
                    sum(precision_scores) / len(precision_scores)
                    if precision_scores
                    else 0.0
                )

                trends.append(TrendPoint(
                    timestamp=current.isoformat(),
                    precision=round(avg_precision, 2),
                    determinism=self._load_determinism_score(),
                    execution_count=len(executions)
                ))

            current += interval

        return TrendsResponse(
            trends=trends,
            period=period
        )

    # Helper methods

    def _load_determinism_score(self) -> float:
        """Load determinism score from baseline file."""
        try:
            if self.baseline_file.exists():
                with open(self.baseline_file) as f:
                    data = json.load(f)
                    return data.get("summary", {}).get("determinism_score", 0.0)
        except Exception as e:
            logger.warning(f"Failed to load determinism score: {e}")

        return 0.0

    def _load_baseline_data(self) -> Optional[Dict[str, Any]]:
        """Load complete baseline data."""
        try:
            if self.baseline_file.exists():
                with open(self.baseline_file) as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load baseline data: {e}")

        return None

    def _calculate_phase(self, precision: float) -> int:
        """
        Calculate current implementation phase based on precision.

        Phases:
        1. Baseline (0-50%)
        2. Validation Gates (50-70%)
        3. Recovery (70-85%)
        4. Stability (85-95%)
        5. Excellence (95-98%+)
        """
        if precision < 50:
            return 1
        elif precision < 70:
            return 2
        elif precision < 85:
            return 3
        elif precision < 95:
            return 4
        else:
            return 5

    def _check_regression(self) -> Optional[Alert]:
        """Check for precision regression."""
        # Get last 5 executions
        recent = self.db.query(MasterPlan).filter(
            MasterPlan.completed_at.isnot(None)
        ).order_by(desc(MasterPlan.completed_at)).limit(5).all()

        if len(recent) < 2:
            return None

        # Calculate precision for each
        precisions = []

        for mp in recent:
            atoms = self.db.query(AtomicUnit).filter(
                AtomicUnit.masterplan_id == mp.masterplan_id
            ).all()

            if atoms:
                succeeded = sum(1 for a in atoms if a.status == "completed")
                precision = (succeeded / len(atoms) * 100) if atoms else 0.0
                precisions.append(precision)

        # Check for regression (last < first - 5%)
        if len(precisions) >= 2:
            first = precisions[0]
            last = precisions[-1]

            if last < first - 5.0:
                return Alert(
                    severity="warning",
                    message=f"Precision regression detected: {first:.1f}% → {last:.1f}%",
                    timestamp=datetime.utcnow().isoformat(),
                    details={
                        "previous": round(first, 2),
                        "current": round(last, 2),
                        "drop": round(first - last, 2)
                    }
                )

        return None


# API Endpoints

@router.get("/precision", response_model=DashboardResponse)
async def get_precision_dashboard(db: Session = Depends(get_db)):
    """
    Get precision monitoring dashboard.

    Returns:
        Current precision metrics, execution history, and alerts
    """
    try:
        service = PrecisionMonitorService(db)

        metrics = service.get_current_metrics()
        history = service.get_execution_history(limit=10)
        alerts = service.get_alerts()

        return DashboardResponse(
            metrics=metrics,
            last_executions=history,
            alerts=alerts
        )

    except Exception as e:
        logger.error(f"Dashboard error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history", response_model=List[ExecutionSummary])
async def get_execution_history(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """
    Get execution history.

    Args:
        limit: Number of executions to return (max 100)
        offset: Offset for pagination

    Returns:
        List of execution summaries
    """
    try:
        service = PrecisionMonitorService(db)
        return service.get_execution_history(limit=limit, offset=offset)

    except Exception as e:
        logger.error(f"History error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trends", response_model=TrendsResponse)
async def get_precision_trends(
    period: str = Query("day", regex="^(hour|day|week)$"),
    db: Session = Depends(get_db)
):
    """
    Get precision trends over time.

    Args:
        period: Time period ("hour", "day", or "week")

    Returns:
        Precision trends data
    """
    try:
        service = PrecisionMonitorService(db)
        return service.get_trends(period=period)

    except Exception as e:
        logger.error(f"Trends error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts", response_model=List[Alert])
async def get_precision_alerts(db: Session = Depends(get_db)):
    """
    Get current precision alerts.

    Returns:
        List of active alerts
    """
    try:
        service = PrecisionMonitorService(db)
        return service.get_alerts()

    except Exception as e:
        logger.error(f"Alerts error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
