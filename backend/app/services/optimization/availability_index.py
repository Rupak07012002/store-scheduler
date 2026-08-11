import uuid
from dataclasses import dataclass, field
from datetime import date, time

from sqlalchemy.orm import Session

from app.models.availability import Availability
from app.models.shift_template import ShiftTemplate
from app.models.time_off import TimeOffRequest, TimeOffStatus


@dataclass
class AvailabilityIndex:
    """
    Prefetches all Availability/TimeOffRequest rows for a store once, so
    checking "is employee E available for date D, template T" during model
    construction (~employees x 7 days x templates checks) doesn't issue a
    DB query per check.
    """

    availability_by_employee: dict[uuid.UUID, list[Availability]] = field(default_factory=dict)
    time_off_by_employee: dict[uuid.UUID, list[tuple[date, date]]] = field(default_factory=dict)

    def is_available(self, employee_id: uuid.UUID, target_date: date, template: ShiftTemplate) -> bool:
        for start, end in self.time_off_by_employee.get(employee_id, []):
            if start <= target_date <= end:
                return False

        rows = self.availability_by_employee.get(employee_id, [])
        weekday = target_date.weekday()
        matching = [
            row
            for row in rows
            if row.day_of_week == weekday
            and (row.effective_from is None or row.effective_from <= target_date)
            and (row.effective_until is None or target_date <= row.effective_until)
            and _covers(row.start_time, row.end_time, template.start_time, template.end_time)
        ]
        if any(not row.is_available for row in matching):
            return False
        return any(row.is_available for row in matching)


def _covers(window_start: time, window_end: time, shift_start: time, shift_end: time) -> bool:
    return window_start <= shift_start and shift_end <= window_end


def build_availability_index(db: Session, employee_ids: list[uuid.UUID]) -> AvailabilityIndex:
    index = AvailabilityIndex()

    for row in db.query(Availability).filter(Availability.employee_id.in_(employee_ids)).all():
        index.availability_by_employee.setdefault(row.employee_id, []).append(row)

    approved_time_off = (
        db.query(TimeOffRequest)
        .filter(TimeOffRequest.employee_id.in_(employee_ids), TimeOffRequest.status == TimeOffStatus.APPROVED)
        .all()
    )
    for row in approved_time_off:
        index.time_off_by_employee.setdefault(row.employee_id, []).append((row.start_date, row.end_date))

    return index
