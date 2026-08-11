import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_role
from app.core.exceptions import ForbiddenError, NotFoundError
from app.db import get_db
from app.models.employee import Employee
from app.models.time_off import TimeOffRequest, TimeOffStatus
from app.models.user import User, UserRole
from app.schemas.availability import TimeOffRequestCreate, TimeOffRequestRead

router = APIRouter(prefix="/time-off", tags=["time-off"])


def _assert_visible(current_user: User, employee: Employee) -> None:
    if current_user.role == UserRole.OWNER:
        return
    if current_user.role == UserRole.STORE_MANAGER and current_user.store_id == employee.store_id:
        return
    if current_user.role == UserRole.EMPLOYEE and current_user.linked_employee_id == employee.id:
        return
    raise ForbiddenError("Not allowed to view this employee's time-off requests")


@router.get("", response_model=list[TimeOffRequestRead])
def list_time_off(
    employee_id: uuid.UUID = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[TimeOffRequest]:
    employee = db.get(Employee, employee_id)
    if employee is None:
        raise NotFoundError("Employee not found")
    _assert_visible(current_user, employee)
    return db.query(TimeOffRequest).filter(TimeOffRequest.employee_id == employee_id).all()


@router.post("", response_model=TimeOffRequestRead, status_code=201)
def create_time_off_request(
    employee_id: uuid.UUID,
    payload: TimeOffRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TimeOffRequest:
    employee = db.get(Employee, employee_id)
    if employee is None:
        raise NotFoundError("Employee not found")
    _assert_visible(current_user, employee)
    request = TimeOffRequest(employee_id=employee_id, **payload.model_dump())
    db.add(request)
    db.commit()
    db.refresh(request)
    return request


@router.patch("/{request_id}/approve", response_model=TimeOffRequestRead)
def approve_time_off(
    request_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.OWNER, UserRole.STORE_MANAGER)),
) -> TimeOffRequest:
    request = db.get(TimeOffRequest, request_id)
    if request is None:
        raise NotFoundError("Time-off request not found")
    employee = db.get(Employee, request.employee_id)
    _assert_visible(current_user, employee)
    request.status = TimeOffStatus.APPROVED
    request.resolved_by_user_id = current_user.id
    request.resolved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(request)
    return request


@router.patch("/{request_id}/deny", response_model=TimeOffRequestRead)
def deny_time_off(
    request_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.OWNER, UserRole.STORE_MANAGER)),
) -> TimeOffRequest:
    request = db.get(TimeOffRequest, request_id)
    if request is None:
        raise NotFoundError("Time-off request not found")
    employee = db.get(Employee, request.employee_id)
    _assert_visible(current_user, employee)
    request.status = TimeOffStatus.DENIED
    request.resolved_by_user_id = current_user.id
    request.resolved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(request)
    return request
