import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_role
from app.core.exceptions import ForbiddenError, NotFoundError
from app.db import get_db
from app.models.employee import Employee
from app.models.user import User, UserRole
from app.schemas.employee import EmployeeCreate, EmployeeRead, EmployeeUpdate

router = APIRouter(prefix="/employees", tags=["employees"])


def _assert_store_scope(user: User, store_id: uuid.UUID) -> None:
    if user.role != UserRole.OWNER and user.store_id != store_id:
        raise ForbiddenError("Not scoped to this store")


@router.get("", response_model=list[EmployeeRead])
def list_employees(
    store_id: uuid.UUID = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Employee]:
    _assert_store_scope(current_user, store_id)
    return db.query(Employee).filter(Employee.store_id == store_id).order_by(Employee.full_name).all()


@router.post("", response_model=EmployeeRead, status_code=201)
def create_employee(
    payload: EmployeeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.OWNER, UserRole.STORE_MANAGER)),
) -> Employee:
    _assert_store_scope(current_user, payload.store_id)
    employee = Employee(**payload.model_dump())
    db.add(employee)
    db.commit()
    db.refresh(employee)
    return employee


@router.patch("/{employee_id}", response_model=EmployeeRead)
def update_employee(
    employee_id: uuid.UUID,
    payload: EmployeeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.OWNER, UserRole.STORE_MANAGER)),
) -> Employee:
    employee = db.get(Employee, employee_id)
    if employee is None:
        raise NotFoundError("Employee not found")
    _assert_store_scope(current_user, employee.store_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(employee, field, value)
    db.commit()
    db.refresh(employee)
    return employee
