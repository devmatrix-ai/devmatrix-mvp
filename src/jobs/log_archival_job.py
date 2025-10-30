"""
Log Archival Background Job

Scheduled job that runs on the 1st of each month at 2am to archive and purge old logs.

Tasks:
- Archive previous month's audit logs to S3
- Archive previous month's security events to S3
- Purge audit logs older than 90 days
- Purge security events older than 90 days
- Purge alert history older than 1 year
- Purge temporary tables older than 7 days

Part of Phase 2 - Task Group 15: Log Retention & Management
"""

from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from src.services.log_archival_service import LogArchivalService
from src.config.settings import get_settings
from src.observability import get_logger

logger = get_logger("log_archival_job")
settings = get_settings()


# Global scheduler instance
_scheduler: AsyncIOScheduler = None


def archive_and_purge_logs():
    """
    Background job to archive and purge old logs.

    Runs on the 1st of each month at 2am.

    Workflow:
    1. Archive previous month's logs to S3
    2. Purge logs older than retention period
    3. Purge temporary tables older than 7 days

    Returns:
        dict: Summary of archival and purge operations
    """
    try:
        logger.info("Log archival and purge job started")

        service = LogArchivalService()

        # Calculate previous month
        now = datetime.utcnow()
        if now.month == 1:
            prev_month = 12
            prev_year = now.year - 1
        else:
            prev_month = now.month - 1
            prev_year = now.year

        summary = {
            "audit_logs_archived": 0,
            "security_events_archived": 0,
            "audit_logs_purged": 0,
            "security_events_purged": 0,
            "alert_history_purged": 0,
            "temp_tables_purged": 0
        }

        # Step 1: Archive previous month's audit logs
        try:
            logger.info(f"Archiving audit logs for {prev_year}-{prev_month:02d}")
            manifest = service.archive_audit_logs(prev_year, prev_month)
            summary["audit_logs_archived"] = manifest["row_count"]
            logger.info(f"Archived {manifest['row_count']} audit logs")
        except Exception as e:
            logger.error(f"Failed to archive audit logs: {str(e)}", exc_info=True)

        # Step 2: Archive previous month's security events
        try:
            logger.info(f"Archiving security events for {prev_year}-{prev_month:02d}")
            manifest = service.archive_security_events(prev_year, prev_month)
            summary["security_events_archived"] = manifest["row_count"]
            logger.info(f"Archived {manifest['row_count']} security events")
        except Exception as e:
            logger.error(f"Failed to archive security events: {str(e)}", exc_info=True)

        # Step 3: Purge old audit logs (older than retention period)
        try:
            logger.info(f"Purging audit logs older than {service.audit_log_retention_days} days")
            rows_deleted = service.purge_old_logs("audit_logs", service.audit_log_retention_days)
            summary["audit_logs_purged"] = rows_deleted
            logger.info(f"Purged {rows_deleted} audit logs")
        except Exception as e:
            logger.error(f"Failed to purge audit logs: {str(e)}", exc_info=True)

        # Step 4: Purge old security events (older than retention period)
        try:
            logger.info(f"Purging security events older than {service.security_event_retention_days} days")
            rows_deleted = service.purge_old_logs("security_events", service.security_event_retention_days)
            summary["security_events_purged"] = rows_deleted
            logger.info(f"Purged {rows_deleted} security events")
        except Exception as e:
            logger.error(f"Failed to purge security events: {str(e)}", exc_info=True)

        # Step 5: Purge old alert history (older than 1 year)
        try:
            logger.info(f"Purging alert history older than {service.alert_history_retention_days} days")
            rows_deleted = service.purge_old_logs("alert_history", service.alert_history_retention_days)
            summary["alert_history_purged"] = rows_deleted
            logger.info(f"Purged {rows_deleted} alert history records")
        except Exception as e:
            logger.error(f"Failed to purge alert history: {str(e)}", exc_info=True)

        # Step 6: Purge temporary tables older than 7 days
        try:
            logger.info("Purging temporary tables older than 7 days")
            tables_purged = service.purge_temp_tables()
            summary["temp_tables_purged"] = tables_purged
            logger.info(f"Purged {tables_purged} temporary tables")
        except Exception as e:
            logger.error(f"Failed to purge temporary tables: {str(e)}", exc_info=True)

        logger.info(f"Log archival and purge job completed: {summary}")

        return summary

    except Exception as e:
        logger.error(f"Log archival and purge job failed: {str(e)}", exc_info=True)
        return {}


def start_scheduler():
    """
    Start the APScheduler for log archival background job.

    Schedules:
    - archive_and_purge_logs: 1st of month at 2am (cron: 0 2 1 * *)

    Usage:
        # In main.py or app startup
        from src.jobs.log_archival_job import start_scheduler
        start_scheduler()
    """
    global _scheduler

    if _scheduler is not None:
        logger.warning("Log archival scheduler already started, skipping initialization")
        return _scheduler

    logger.info("Starting log archival scheduler")

    _scheduler = AsyncIOScheduler()

    # Schedule log archival job (1st of month at 2am)
    _scheduler.add_job(
        func=archive_and_purge_logs,
        trigger=CronTrigger(day=1, hour=2, minute=0),
        id="archive_and_purge_logs",
        name="Archive and purge old logs",
        replace_existing=True,
        max_instances=1  # Prevent concurrent execution
    )

    _scheduler.start()

    logger.info("Log archival scheduler started successfully")
    logger.info("Scheduled jobs:")
    logger.info("  - archive_and_purge_logs: 1st of month at 2am UTC")

    return _scheduler


def stop_scheduler():
    """
    Stop the log archival scheduler.

    Usage:
        # In application shutdown
        from src.jobs.log_archival_job import stop_scheduler
        stop_scheduler()
    """
    global _scheduler

    if _scheduler is None:
        logger.warning("Log archival scheduler not running, nothing to stop")
        return

    logger.info("Stopping log archival scheduler")
    _scheduler.shutdown(wait=True)
    _scheduler = None
    logger.info("Log archival scheduler stopped")


def get_scheduler() -> AsyncIOScheduler:
    """
    Get the global log archival scheduler instance.

    Returns:
        AsyncIOScheduler: Scheduler instance or None if not started

    Usage:
        scheduler = get_scheduler()
        if scheduler:
            print(scheduler.get_jobs())
    """
    return _scheduler
