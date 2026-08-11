import logging
from datetime import date, timedelta

from app.db import SessionLocal
from app.models.store import Store
from app.services.compliance import run_compliance_check
from app.services.schedule_generation import generate_schedule_run

logger = logging.getLogger(__name__)


def _next_monday(from_date: date) -> date:
    return from_date + timedelta(days=(7 - from_date.weekday()) % 7 or 7)


def generate_weekly_drafts() -> None:
    """
    Plain, importable function (not a decorated Celery/APScheduler task) so
    it can be called directly from a test, from APScheduler (v1), or wrapped
    as a Celery task later with an unchanged body - see docs/scaling-guide.md.

    Generates a draft ScheduleRun for next week for every active store. This
    only ever produces DRAFTS - a manager/owner still has to review and
    publish (see app/api/v1/schedules.py), so a bad forecast or a solver
    hiccup can never auto-publish something nobody looked at.
    """
    db = SessionLocal()
    week_start = _next_monday(date.today())
    try:
        stores = db.query(Store).filter(Store.is_active.is_(True)).all()
        for store in stores:
            try:
                run = generate_schedule_run(db, store_id=store.id, week_start=week_start, generated_by="system")
                run_compliance_check(db, run)
                db.commit()
                logger.info("Generated draft schedule for store %s, week %s", store.id, week_start)
            except Exception:
                db.rollback()
                logger.exception("Failed to generate draft schedule for store %s", store.id)
    finally:
        db.close()
