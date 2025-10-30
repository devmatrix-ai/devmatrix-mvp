"""
Security Monitoring Background Job

Scheduled job that runs security event detection every 5 minutes.

Detects:
- Failed login clusters (5+ in 10 minutes)
- Geo-location changes (IP country change)
- Privilege escalation (role changed to admin/superadmin)
- Unusual access patterns (access at atypical hours)
- Multiple 403s (10+ in 5 minutes)
- Account lockout events
- 2FA disabled when enforced
- Multiple concurrent sessions from different countries

Part of Phase 2 - Task Group 13: Security Event Monitoring
Extended in Task Group 14: Alert System Implementation
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from src.services.security_monitoring_service import SecurityMonitoringService
from src.services.alert_service import AlertService
from src.config.settings import get_settings
from src.observability import get_logger

logger = get_logger("security_monitoring_job")
settings = get_settings()


# Global scheduler instance
_scheduler: AsyncIOScheduler = None


def detect_security_events():
    """
    Background job to detect security events and send alerts.

    Runs every 5 minutes (configurable via SECURITY_MONITORING_INTERVAL_MINUTES).

    Workflow:
    1. Run all security event detections
    2. Send alerts for new security events (Task Group 14)

    Returns:
        int: Number of security events detected
    """
    try:
        logger.info("Security monitoring job started")

        # Step 1: Detect security events
        monitoring_service = SecurityMonitoringService()
        events = monitoring_service.run_all_detections()

        if len(events) > 0:
            logger.info(f"Security monitoring job completed: {len(events)} events detected")

            # Log event types
            event_types = {}
            for event in events:
                event_types[event.event_type] = event_types.get(event.event_type, 0) + 1

            logger.info(f"Event breakdown: {event_types}")

            # Step 2: Send alerts for new security events (Task Group 14)
            alert_service = AlertService()
            total_alerts = 0

            for event in events:
                try:
                    alert_history = alert_service.send_alert(event)
                    total_alerts += len(alert_history)
                except Exception as e:
                    logger.error(
                        f"Failed to send alert for event {event.event_id}: {str(e)}",
                        exc_info=True
                    )

            logger.info(f"Alerts sent: {total_alerts} alerts for {len(events)} events")

        else:
            logger.debug("Security monitoring job completed: No security events detected")

        return len(events)

    except Exception as e:
        logger.error(f"Security monitoring job failed: {str(e)}", exc_info=True)
        return 0


def start_scheduler():
    """
    Start the APScheduler for security monitoring background job.

    Schedules:
    - detect_security_events: Every 5 minutes (configurable)

    Usage:
        # In main.py or app startup
        from src.jobs.security_monitoring_job import start_scheduler
        start_scheduler()
    """
    global _scheduler

    if _scheduler is not None:
        logger.warning("Security monitoring scheduler already started, skipping initialization")
        return _scheduler

    logger.info("Starting security monitoring scheduler")

    _scheduler = AsyncIOScheduler()

    # Get interval from settings (default: 5 minutes)
    interval_minutes = getattr(settings, 'SECURITY_MONITORING_INTERVAL_MINUTES', 5)

    # Schedule security monitoring job
    _scheduler.add_job(
        func=detect_security_events,
        trigger=IntervalTrigger(minutes=interval_minutes),
        id="detect_security_events",
        name="Security event detection and alert delivery",
        replace_existing=True,
        max_instances=1  # Prevent concurrent execution
    )

    _scheduler.start()

    logger.info("Security monitoring scheduler started successfully")
    logger.info(f"Scheduled jobs:")
    logger.info(f"  - detect_security_events: Every {interval_minutes} minutes")

    return _scheduler


def stop_scheduler():
    """
    Stop the security monitoring scheduler.

    Usage:
        # In application shutdown
        from src.jobs.security_monitoring_job import stop_scheduler
        stop_scheduler()
    """
    global _scheduler

    if _scheduler is None:
        logger.warning("Security monitoring scheduler not running, nothing to stop")
        return

    logger.info("Stopping security monitoring scheduler")
    _scheduler.shutdown(wait=True)
    _scheduler = None
    logger.info("Security monitoring scheduler stopped")


def get_scheduler() -> AsyncIOScheduler:
    """
    Get the global security monitoring scheduler instance.

    Returns:
        AsyncIOScheduler: Scheduler instance or None if not started

    Usage:
        scheduler = get_scheduler()
        if scheduler:
            print(scheduler.get_jobs())
    """
    return _scheduler
