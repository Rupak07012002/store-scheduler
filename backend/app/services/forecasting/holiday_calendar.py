import uuid
from datetime import date

from sqlalchemy.orm import Session

from app.models.holiday_calendar import HolidayCalendarEntry


def get_multiplier(db: Session, store_id: uuid.UUID, target_date: date) -> float:
    """
    Store-specific entries take precedence over global (store_id=NULL)
    entries for the same date, since an owner overriding a specific store's
    multiplier should win over the general default.
    """
    store_specific = (
        db.query(HolidayCalendarEntry)
        .filter(HolidayCalendarEntry.store_id == store_id, HolidayCalendarEntry.date == target_date)
        .first()
    )
    if store_specific is not None:
        return float(store_specific.expected_footfall_multiplier)

    global_entry = (
        db.query(HolidayCalendarEntry)
        .filter(HolidayCalendarEntry.store_id.is_(None), HolidayCalendarEntry.date == target_date)
        .first()
    )
    if global_entry is not None:
        return float(global_entry.expected_footfall_multiplier)

    return 1.0
