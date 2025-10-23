"""
Usage & Quota API Endpoints

Provides endpoints for viewing usage statistics and quota limits.
Task Group 5.1-5.4 - Phase 6: Authentication & Multi-tenancy
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional, Dict, Any

from src.models.user import User
from src.api.middleware.auth_middleware import get_current_active_user
from src.services.usage_tracking_service import UsageTrackingService
from src.observability import get_logger

logger = get_logger("usage_router")

router = APIRouter(prefix="/api/v1/usage", tags=["usage"])


# ============================================================================
# Response Models
# ============================================================================

class UsageResponse(BaseModel):
    """User usage statistics response"""
    user_id: str
    month: str
    llm_tokens_used: int
    llm_cost_usd: float
    llm_cost_eur: float
    masterplans_created: int
    storage_bytes: int
    storage_mb: float
    api_calls: int


class QuotaResponse(BaseModel):
    """User quota limits response"""
    quota_id: Optional[str]
    user_id: str
    llm_tokens_monthly_limit: Optional[int]
    masterplans_limit: Optional[int]
    storage_bytes_limit: Optional[int]
    api_calls_per_minute: int


class QuotaStatusResponse(BaseModel):
    """Combined quota and usage status"""
    quota: Optional[Dict[str, Any]]
    usage: Dict[str, Any]
    percentages: Dict[str, Optional[float]]
    warnings: Dict[str, bool]


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/current", response_model=UsageResponse)
async def get_current_usage(current_user: User = Depends(get_current_active_user)):
    """
    Get current month's usage statistics.

    Returns usage for the authenticated user for the current month.

    **Example**:
    ```bash
    curl -X GET http://localhost:8000/api/v1/usage/current \\
      -H "Authorization: Bearer <access_token>"
    ```

    **Returns**:
    - user_id: User UUID
    - month: Month (YYYY-MM-DD)
    - llm_tokens_used: Total LLM tokens consumed
    - llm_cost_usd: Total cost in USD
    - llm_cost_eur: Total cost in EUR
    - masterplans_created: Number of masterplans created
    - storage_bytes: Current storage usage in bytes
    - storage_mb: Current storage usage in MB
    - api_calls: Total API calls made

    **Errors**:
    - 401: Not authenticated
    """
    tracker = UsageTrackingService(current_user.user_id)
    usage = tracker.get_current_usage()

    logger.info(f"User {current_user.user_id} retrieved current usage")
    return usage


@router.get("/quota", response_model=QuotaResponse)
async def get_user_quota(current_user: User = Depends(get_current_active_user)):
    """
    Get user's quota limits.

    Returns quota limits for the authenticated user.

    **Example**:
    ```bash
    curl -X GET http://localhost:8000/api/v1/usage/quota \\
      -H "Authorization: Bearer <access_token>"
    ```

    **Returns**:
    - quota_id: Quota UUID (null if no quota set)
    - user_id: User UUID
    - llm_tokens_monthly_limit: Monthly LLM token limit (null = unlimited)
    - masterplans_limit: Maximum masterplans allowed (null = unlimited)
    - storage_bytes_limit: Maximum storage in bytes (null = unlimited)
    - api_calls_per_minute: API rate limit per minute

    **Errors**:
    - 401: Not authenticated
    - 404: No quota configured
    """
    tracker = UsageTrackingService(current_user.user_id)
    quota = tracker.get_user_quota()

    if not quota:
        # Return default unlimited quota
        logger.info(f"User {current_user.user_id} has no quota configured (unlimited)")
        return {
            "quota_id": None,
            "user_id": str(current_user.user_id),
            "llm_tokens_monthly_limit": None,
            "masterplans_limit": None,
            "storage_bytes_limit": None,
            "api_calls_per_minute": 30,  # Default
        }

    logger.info(f"User {current_user.user_id} retrieved quota")
    return quota.to_dict()


@router.get("/status", response_model=QuotaStatusResponse)
async def get_quota_status(current_user: User = Depends(get_current_active_user)):
    """
    Get combined quota and usage status with percentages.

    Returns comprehensive status including quota limits, current usage,
    usage percentages, and warnings.

    **Example**:
    ```bash
    curl -X GET http://localhost:8000/api/v1/usage/status \\
      -H "Authorization: Bearer <access_token>"
    ```

    **Returns**:
    - quota: Quota limits (null if unlimited)
    - usage: Current month's usage
    - percentages:
      - tokens: Percentage of token quota used
      - storage: Percentage of storage quota used
    - warnings:
      - tokens_near_limit: True if ≥90% of token quota used
      - storage_near_limit: True if ≥90% of storage quota used

    **Errors**:
    - 401: Not authenticated
    """
    tracker = UsageTrackingService(current_user.user_id)
    status_data = tracker.get_quota_status()

    logger.info(f"User {current_user.user_id} retrieved quota status")
    return status_data


@router.get("/history")
async def get_usage_history(
    months: int = 6,
    current_user: User = Depends(get_current_active_user)
):
    """
    Get usage history for past N months.

    **Example**:
    ```bash
    curl -X GET "http://localhost:8000/api/v1/usage/history?months=6" \\
      -H "Authorization: Bearer <access_token>"
    ```

    **Parameters**:
    - months: Number of past months to retrieve (default 6, max 12)

    **Returns**:
    - Array of usage records for past months

    **Errors**:
    - 401: Not authenticated
    - 400: Invalid months parameter
    """
    from datetime import date, timedelta
    from dateutil.relativedelta import relativedelta
    from src.config.database import get_db_context
    from src.models.user_usage import UserUsage

    # Validate months parameter
    if months < 1 or months > 12:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="months must be between 1 and 12"
        )

    # Calculate date range
    today = date.today()
    current_month = date(today.year, today.month, 1)

    history = []

    with get_db_context() as db:
        for i in range(months):
            month_date = current_month - relativedelta(months=i)

            usage = db.query(UserUsage).filter(
                UserUsage.user_id == current_user.user_id,
                UserUsage.month == month_date
            ).first()

            if usage:
                history.append(usage.to_dict())
            else:
                # Return zero usage for months with no record
                history.append({
                    "user_id": str(current_user.user_id),
                    "month": month_date.isoformat(),
                    "llm_tokens_used": 0,
                    "llm_cost_usd": 0.0,
                    "masterplans_created": 0,
                    "storage_bytes": 0,
                    "api_calls": 0,
                })

    logger.info(f"User {current_user.user_id} retrieved {months} months of usage history")
    return {"history": history, "months": months}


@router.get("/health")
async def usage_health():
    """
    Health check for usage tracking service.

    **Example**:
    ```bash
    curl http://localhost:8000/api/v1/usage/health
    ```

    **Returns**:
    - status: Service status
    - message: Status message
    """
    return {
        "status": "healthy",
        "service": "usage_tracking",
        "message": "Usage tracking service is operational"
    }
