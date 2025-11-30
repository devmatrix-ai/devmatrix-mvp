"""
Health Check Endpoints

Provides /health and /ready endpoints for monitoring.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.database import get_db
import structlog

router = APIRouter(prefix="/health", tags=["health"])
logger = structlog.get_logger(__name__)


@router.get("")
async def health_check():
    """
    Basic health check - always returns OK.
    Bug #129 Fix: Changed from /health to "" (prefix already adds /health)

    Returns:
        dict: Service status
    """
    return {
        "status": "ok",
        "service": "API"
    }


@router.get("/ready")
async def readiness_check(db: AsyncSession = Depends(get_db)):
    """
    Readiness check - verifies dependencies.

    Checks:
        - Database connection

    Args:
        db: Database session

    Returns:
        dict: Readiness status with component checks

    Raises:
        HTTPException: 503 if not ready
    """
    try:
        # Check database connection (use text() to avoid SQLAlchemy warning)
        await db.execute(text("SELECT 1"))

        return {
            "status": "ready",
            "checks": {
                "database": "ok"
            }
        }
    except Exception as e:
        logger.error("readiness_check_failed", error=str(e), exc_info=True)

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "not_ready",
                "checks": {
                    "database": "failed"
                },
                "error": str(e)
            }
        )