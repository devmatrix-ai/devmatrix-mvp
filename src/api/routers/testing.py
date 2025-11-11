"""
Acceptance Testing API Endpoints

API for acceptance test generation, execution, and gate checking.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import Optional, List, AsyncGenerator
import logging

from src.config.database import DatabaseConfig
from src.models import AcceptanceTest, AcceptanceTestResult
from src.testing import (
    AcceptanceTestGenerator,
    AcceptanceTestRunner,
    AcceptanceTestGate
)
from src.api.middleware.auth_middleware import get_current_user
from src.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/testing", tags=["acceptance-testing"])


# Async database session dependency
async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """Get async database session for FastAPI dependency injection."""
    AsyncSessionLocal = DatabaseConfig.get_async_session_factory()
    async_db = AsyncSessionLocal()
    try:
        yield async_db
        await async_db.commit()
    except Exception:
        await async_db.rollback()
        raise
    finally:
        await async_db.close()


@router.post("/generate/{masterplan_id}")
async def generate_acceptance_tests(
    masterplan_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generate acceptance tests from masterplan requirements

    Returns:
        {
            "tests_generated": 15,
            "must_tests": 10,
            "should_tests": 5,
            "tests": [...]
        }
    """
    try:
        logger.info(f"Generating acceptance tests for masterplan {masterplan_id}")

        # Generate tests
        generator = AcceptanceTestGenerator(db)
        tests = await generator.generate_from_masterplan(masterplan_id)

        must_tests = [t for t in tests if t.requirement_priority == 'must']
        should_tests = [t for t in tests if t.requirement_priority == 'should']

        logger.info(
            f"Generated {len(tests)} tests for masterplan {masterplan_id}: "
            f"{len(must_tests)} MUST, {len(should_tests)} SHOULD"
        )

        return {
            "tests_generated": len(tests),
            "must_tests": len(must_tests),
            "should_tests": len(should_tests),
            "tests": [
                {
                    "test_id": str(t.test_id),
                    "requirement": t.requirement_text,
                    "priority": t.requirement_priority,
                    "language": t.test_language,
                    "timeout_seconds": t.timeout_seconds
                }
                for t in tests
            ]
        }

    except ValueError as e:
        logger.error(f"Validation error generating tests: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Test generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Test generation failed: {str(e)}")


@router.post("/run/{wave_id}")
async def run_acceptance_tests(
    wave_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """
    Execute all acceptance tests for a wave's masterplan

    Returns:
        {
            "wave_id": "...",
            "execution_summary": {
                "total": 15,
                "passed": 14,
                "failed": 1,
                ...
            },
            "gate_status": "PENDING"
        }
    """
    try:
        logger.info(f"Running acceptance tests for wave {wave_id}")

        runner = AcceptanceTestRunner(db)
        results = await runner.run_tests_for_wave(wave_id)

        logger.info(
            f"Wave {wave_id} test execution complete: "
            f"{results['passed']}/{results['total']} passed"
        )

        return {
            "wave_id": str(wave_id),
            "execution_summary": results,
            "gate_status": "PENDING"  # Gate check happens separately
        }

    except Exception as e:
        logger.error(f"Test execution failed for wave {wave_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Test execution failed: {str(e)}")


@router.get("/gate/{masterplan_id}")
async def check_gate_status(
    masterplan_id: UUID,
    wave_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """
    Check if masterplan passes Gate S (100% must + ≥95% should)

    Query params:
        wave_id: Optional wave UUID to check specific wave

    Returns:
        {
            "gate_passed": true,
            "must_pass_rate": 1.0,
            "should_pass_rate": 0.96,
            "can_release": true,
            "gate_status": "PASS",
            ...
        }
    """
    try:
        logger.info(f"Checking Gate S for masterplan {masterplan_id}, wave {wave_id}")

        gate = AcceptanceTestGate(db)
        result = await gate.check_gate(masterplan_id, wave_id)

        logger.info(
            f"Gate S status for masterplan {masterplan_id}: {result['gate_status']} "
            f"(must: {result['must_pass_rate']:.1%}, should: {result['should_pass_rate']:.1%})"
        )

        return result

    except Exception as e:
        logger.error(f"Gate check failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Gate check failed: {str(e)}")


@router.get("/results/{masterplan_id}")
async def get_test_results(
    masterplan_id: UUID,
    priority: Optional[str] = None,
    status: Optional[str] = None,
    wave_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get acceptance test results with optional filters

    Query params:
        priority: Filter by 'must' or 'should'
        status: Filter by 'pass', 'fail', 'timeout', 'error'
        wave_id: Filter by wave

    Returns:
        {
            "total_tests": 15,
            "results": [...]
        }
    """
    try:
        logger.info(
            f"Fetching test results for masterplan {masterplan_id} "
            f"(priority={priority}, status={status}, wave={wave_id})"
        )

        # Get runner to fetch latest results
        runner = AcceptanceTestRunner(db)
        aggregated = await runner.get_latest_results(masterplan_id, wave_id)

        # Filter results if needed
        results = aggregated['results']

        if priority:
            results = [r for r in results if r.test.requirement_priority == priority]

        if status:
            results = [r for r in results if r.status == status]

        logger.info(f"Returning {len(results)} test results for masterplan {masterplan_id}")

        return {
            "total_tests": len(results),
            "results": [
                {
                    "test_id": str(r.test.test_id),
                    "requirement": r.test.requirement_text,
                    "priority": r.test.requirement_priority,
                    "status": r.status,
                    "execution_time_ms": r.execution_duration_ms,
                    "error": r.error_message,
                    "executed_at": r.execution_time.isoformat() if r.execution_time else None
                }
                for r in results
            ]
        }

    except Exception as e:
        logger.error(f"Failed to fetch test results: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch results: {str(e)}")


@router.get("/gate/{masterplan_id}/report")
async def get_gate_report(
    masterplan_id: UUID,
    wave_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get detailed Gate S report with all failed requirements

    Returns:
        {
            "report": "text report...",
            "failed_requirements": [...]
        }
    """
    try:
        gate = AcceptanceTestGate(db)

        # Get gate result
        gate_result = await gate.check_gate(masterplan_id, wave_id)

        # Get formatted report
        report = await gate.get_gate_report(masterplan_id, wave_id)

        return {
            "report": report,
            "gate_status": gate_result['gate_status'],
            "gate_passed": gate_result['gate_passed'],
            "can_release": gate_result['can_release'],
            "failed_requirements": gate_result['failed_requirements']
        }

    except Exception as e:
        logger.error(f"Failed to generate gate report: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {str(e)}")


@router.delete("/tests/{masterplan_id}")
async def delete_acceptance_tests(
    masterplan_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete all acceptance tests for a masterplan

    Requires superuser permissions.

    Returns:
        {
            "deleted_count": 15
        }
    """
    # Check permissions
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superusers can delete acceptance tests"
        )

    try:
        logger.info(f"Deleting acceptance tests for masterplan {masterplan_id}")

        generator = AcceptanceTestGenerator(db)
        count = await generator.delete_tests_for_masterplan(masterplan_id)

        logger.info(f"Deleted {count} tests for masterplan {masterplan_id}")

        return {
            "deleted_count": count
        }

    except Exception as e:
        logger.error(f"Failed to delete tests: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete tests: {str(e)}")


@router.post("/regenerate/{masterplan_id}")
async def regenerate_failed_tests(
    masterplan_id: UUID,
    failed_test_ids: List[UUID],
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """
    Regenerate specific failed tests with improved templates

    Body:
        {
            "failed_test_ids": ["uuid1", "uuid2", ...]
        }

    Returns:
        {
            "regenerated_count": 3,
            "tests": [...]
        }
    """
    try:
        logger.info(f"Regenerating {len(failed_test_ids)} failed tests for masterplan {masterplan_id}")

        generator = AcceptanceTestGenerator(db)
        regenerated = await generator.regenerate_failed_tests(masterplan_id, failed_test_ids)

        logger.info(f"Regenerated {len(regenerated)} tests")

        return {
            "regenerated_count": len(regenerated),
            "tests": [
                {
                    "test_id": str(t.test_id),
                    "requirement": t.requirement_text,
                    "priority": t.requirement_priority
                }
                for t in regenerated
            ]
        }

    except Exception as e:
        logger.error(f"Failed to regenerate tests: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to regenerate tests: {str(e)}")


@router.get("/statistics/{masterplan_id}")
async def get_test_statistics(
    masterplan_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get statistics about generated tests for a masterplan

    Returns:
        {
            "total_tests": 15,
            "must_tests": 10,
            "should_tests": 5,
            "languages": {"pytest": 10, "jest": 5},
            "avg_timeout": 30
        }
    """
    try:
        generator = AcceptanceTestGenerator(db)
        stats = await generator.get_test_statistics(masterplan_id)

        return stats

    except Exception as e:
        logger.error(f"Failed to get statistics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}")
