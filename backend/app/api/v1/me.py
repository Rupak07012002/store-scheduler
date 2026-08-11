from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.exceptions import ForbiddenError
from app.db import get_db
from app.models.schedule_run import ScheduleRun, ScheduleRunStatus
from app.models.shift_assignment import ShiftAssignment
from app.models.user import User, UserRole
from app.schemas.schedule import ShiftAssignmentRead

router = APIRouter(prefix="/me", tags=["me"])


@router.get("/shifts", response_model=list[ShiftAssignmentRead])
def my_published_shifts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ShiftAssignment]:
    """
    Convenience endpoint for the employee self-service portal: this
    employee's own upcoming shifts, published schedules only. Equivalent to
    filtering GET /schedules?store_id=... client-side, but saves the
    employee portal from having to know its own store_id or filter by
    employee_id itself.
    """
    if current_user.role != UserRole.EMPLOYEE or current_user.linked_employee_id is None:
        raise ForbiddenError("This endpoint is for employee accounts linked to an Employee record")

    return (
        db.query(ShiftAssignment)
        .join(ScheduleRun, ShiftAssignment.schedule_run_id == ScheduleRun.id)
        .filter(
            ShiftAssignment.employee_id == current_user.linked_employee_id,
            ScheduleRun.status == ScheduleRunStatus.PUBLISHED,
        )
        .order_by(ShiftAssignment.date)
        .all()
    )
