import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_role
from app.core.exceptions import ForbiddenError, NotFoundError
from app.db import get_db
from app.models.schedule_run import ScheduleRun
from app.models.shift_assignment import ShiftAssignment
from app.models.swap_request import SwapRequest, SwapStatus
from app.models.user import User, UserRole
from app.schemas.swap import SwapRequestCreate, SwapRequestRead
from app.services.swap_workflow import approve_swap, create_swap_request, deny_swap

router = APIRouter(prefix="/swaps", tags=["swaps"])


def _store_id_for_assignment(db: Session, assignment_id: uuid.UUID) -> uuid.UUID:
    assignment = db.get(ShiftAssignment, assignment_id)
    if assignment is None:
        raise NotFoundError("Shift assignment not found")
    run = db.get(ScheduleRun, assignment.schedule_run_id)
    return run.store_id


@router.post("", response_model=SwapRequestRead, status_code=201)
def request_swap(
    payload: SwapRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SwapRequest:
    store_id = _store_id_for_assignment(db, payload.source_assignment_id)
    if current_user.role != UserRole.OWNER and current_user.store_id != store_id:
        raise ForbiddenError("Not scoped to this store")

    return create_swap_request(
        db,
        current_user=current_user,
        source_assignment_id=payload.source_assignment_id,
        target_employee_id=payload.target_employee_id,
        target_assignment_id=payload.target_assignment_id,
    )


@router.get("", response_model=list[SwapRequestRead])
def list_swaps(
    store_id: uuid.UUID = Query(...),
    status: SwapStatus | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.OWNER, UserRole.STORE_MANAGER)),
) -> list[SwapRequest]:
    if current_user.role != UserRole.OWNER and current_user.store_id != store_id:
        raise ForbiddenError("Not scoped to this store")

    query = (
        db.query(SwapRequest)
        .join(ShiftAssignment, SwapRequest.source_assignment_id == ShiftAssignment.id)
        .join(ScheduleRun, ShiftAssignment.schedule_run_id == ScheduleRun.id)
        .filter(ScheduleRun.store_id == store_id)
    )
    if status is not None:
        query = query.filter(SwapRequest.status == status)
    return query.all()


@router.patch("/{swap_id}/approve", response_model=SwapRequestRead)
def approve(
    swap_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.OWNER, UserRole.STORE_MANAGER)),
) -> SwapRequest:
    swap = db.get(SwapRequest, swap_id)
    if swap is None:
        raise NotFoundError("Swap request not found")
    store_id = _store_id_for_assignment(db, swap.source_assignment_id)
    if current_user.role != UserRole.OWNER and current_user.store_id != store_id:
        raise ForbiddenError("Not scoped to this store")
    return approve_swap(db, swap_id, current_user)


@router.patch("/{swap_id}/deny", response_model=SwapRequestRead)
def deny(
    swap_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.OWNER, UserRole.STORE_MANAGER)),
) -> SwapRequest:
    swap = db.get(SwapRequest, swap_id)
    if swap is None:
        raise NotFoundError("Swap request not found")
    store_id = _store_id_for_assignment(db, swap.source_assignment_id)
    if current_user.role != UserRole.OWNER and current_user.store_id != store_id:
        raise ForbiddenError("Not scoped to this store")
    return deny_swap(db, swap_id, current_user)
