import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.jobs.tasks import generate_weekly_drafts

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def start_scheduler() -> None:
    """
    APScheduler running in-process inside the FastAPI app - appropriate at
    this scale (one weekly job across 8 stores) and avoids operating a
    separate Redis+Celery stack for v1. If this ever needs to run outside
    the API process, run multiple API replicas, or get retry/observability,
    move generate_weekly_drafts (already a plain function, no framework
    coupling) into a Celery task - see docs/scaling-guide.md.
    """
    global _scheduler
    if _scheduler is not None:
        return

    _scheduler = BackgroundScheduler(timezone="UTC")
    # Sunday 02:00 UTC: drafts are ready well before a Monday-starting week,
    # with time for a manager to review before it starts.
    _scheduler.add_job(
        generate_weekly_drafts,
        trigger=CronTrigger(day_of_week="sun", hour=2, minute=0),
        id="generate_weekly_drafts",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info("Weekly draft-schedule job scheduled (Sundays 02:00 UTC)")


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
