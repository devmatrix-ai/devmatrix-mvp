"""
Auto-Unlock Background Job

Scheduled job that automatically unlocks expired account lockouts.

Runs every 5 minutes to:
- Query users with expired lockouts (locked_until <= NOW)
- Reset locked_until and failed_login_attempts
- Log unlock events

Part of Phase 2 - Task Group 3: Account Lockout Protection
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from src.services.account_lockout_service import AccountLockoutService
from src.observability import get_logger

logger = get_logger("auto_unlock_job")


# Global scheduler instance
_scheduler: AsyncIOScheduler = None


def auto_unlock_expired_lockouts():
    """
    Background job to auto-unlock accounts with expired lockouts.

    Runs every 5 minutes.

    Returns:
        int: Number of accounts unlocked
    """
    try:
        logger.info("Auto-unlock job started")

        service = AccountLockoutService()
        unlocked_count = service.process_auto_unlock()

        if unlocked_count > 0:
            logger.info(f"Auto-unlock job completed: {unlocked_count} accounts unlocked")
        else:
            logger.debug("Auto-unlock job completed: No expired lockouts found")

        return unlocked_count

    except Exception as e:
        logger.error(f"Auto-unlock job failed: {str(e)}", exc_info=True)
        return 0


def start_scheduler():
    """
    Start the APScheduler for background jobs.

    Schedules:
    - auto_unlock_expired_lockouts: Every 5 minutes

    Usage:
        # In main.py or app startup
        from src.jobs.auto_unlock_job import start_scheduler
        start_scheduler()
    """
    global _scheduler

    if _scheduler is not None:
        logger.warning("Scheduler already started, skipping initialization")
        return _scheduler

    logger.info("Starting background job scheduler")

    _scheduler = AsyncIOScheduler()

    # Schedule auto-unlock job every 5 minutes
    _scheduler.add_job(
        func=auto_unlock_expired_lockouts,
        trigger=IntervalTrigger(minutes=5),
        id="auto_unlock_expired_lockouts",
        name="Auto-unlock expired account lockouts",
        replace_existing=True,
        max_instances=1  # Prevent concurrent execution
    )

    _scheduler.start()

    logger.info("Background job scheduler started successfully")
    logger.info("Scheduled jobs:")
    logger.info("  - auto_unlock_expired_lockouts: Every 5 minutes")

    return _scheduler


def stop_scheduler():
    """
    Stop the APScheduler.

    Usage:
        # In application shutdown
        from src.jobs.auto_unlock_job import stop_scheduler
        stop_scheduler()
    """
    global _scheduler

    if _scheduler is None:
        logger.warning("Scheduler not running, nothing to stop")
        return

    logger.info("Stopping background job scheduler")
    _scheduler.shutdown(wait=True)
    _scheduler = None
    logger.info("Background job scheduler stopped")


def get_scheduler() -> AsyncIOScheduler:
    """
    Get the global scheduler instance.

    Returns:
        AsyncIOScheduler: Scheduler instance or None if not started

    Usage:
        scheduler = get_scheduler()
        if scheduler:
            print(scheduler.get_jobs())
    """
    return _scheduler
