import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.exceptions import ForbiddenError, NotFoundError
from app.db import get_db
from app.models.availability import Availability
from app.models.employee import Employee
from app.models.user import User, UserRole
from app.schemas.availability import AvailabilityCreate, AvailabilityRead

router = APIRouter(prefix="/availability", tags=["availability"])


def _assert_can_manage(current_user: User, employee: Employee, db: Session) -> None:
    if current_user.role == UserRole.OWNER:
        return
    if current_user.role == UserRole.STORE_MANAGER and current_user.store_id == employee.store_id:
        return
    if current_user.role == UserRole.EMPLOYEE and current_user.linked_employee_id == employee.id:
        return
    raise ForbiddenError("Not allowed to manage this employee's availability")


@router.get("", response_model=list[AvailabilityRead])
def list_availability(
    employee_id: uuid.UUID = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Availability]:
    employee = db.get(Employee, employee_id)
    if employee is None:
        raise NotFoundError("Employee not found")
    _assert_can_manage(current_user, employee, db)
    return db.query(Availability).filter(Availability.employee_id == employee_id).all()


@router.post("", response_model=AvailabilityRead, status_code=201)
def create_availability(
    employee_id: uuid.UUID,
    payload: AvailabilityCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Availability:
    employee = db.get(Employee, employee_id)
    if employee is None:
        raise NotFoundError("Employee not found")
    _assert_can_manage(current_user, employee, db)
    availability = Availability(employee_id=employee_id, **payload.model_dump())
    db.add(availability)
    db.commit()
    db.refresh(availability)
    return availability


@router.delete("/{availability_id}", status_code=204)
def delete_availability(
    availability_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    availability = db.get(Availability, availability_id)
    if availability is None:
        raise NotFoundError("Availability window not found")
    employee = db.get(Employee, availability.employee_id)
    _assert_can_manage(current_user, employee, db)
    db.delete(availability)
    db.commit()
