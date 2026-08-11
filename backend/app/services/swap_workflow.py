import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.models.employee import Employee
from app.models.schedule_run import ScheduleRun
from app.models.shift_assignment import AssignmentStatus, ShiftAssignment
from app.models.swap_request import SwapRequest, SwapStatus
from app.models.user import User, UserRole
from app.services.compliance import run_compliance_check


def _get_published_assignment(db: Session, assignment_id: uuid.UUID) -> ShiftAssignment:
    assignment = db.get(ShiftAssignment, assignment_id)
    if assignment is None:
        raise NotFoundError("Shift assignment not found")
    if assignment.status != AssignmentStatus.PUBLISHED:
        raise ConflictError("Swaps are only allowed against published assignments")
    return assignment


def create_swap_request(
    db: Session,
    current_user: User,
    source_assignment_id: uuid.UUID,
    target_employee_id: uuid.UUID | None,
    target_assignment_id: uuid.UUID | None,
) -> SwapRequest:
    source = _get_published_assignment(db, source_assignment_id)

    if current_user.role == UserRole.EMPLOYEE and source.employee_id != current_user.linked_employee_id:
        raise ForbiddenError("Employees may only request swaps for their own shifts")

    if target_assignment_id is not None:
        target = _get_published_assignment(db, target_assignment_id)
        source_run = db.get(ScheduleRun, source.schedule_run_id)
        target_run = db.get(ScheduleRun, target.schedule_run_id)
        if source_run.store_id != target_run.store_id:
            raise ConflictError("Cannot swap shifts across different stores")
        # No skill/role differentiation on who can swap with whom in v1
        # (assumption documented in the plan) - any employee within the
        # same store may swap with any other.

    swap = SwapRequest(
        source_assignment_id=source_assignment_id,
        target_employee_id=target_employee_id,
        target_assignment_id=target_assignment_id,
        status=SwapStatus.PENDING,
    )
    db.add(swap)
    db.commit()
    db.refresh(swap)
    return swap


def approve_swap(db: Session, swap_id: uuid.UUID, resolver: User) -> SwapRequest:
    swap = db.get(SwapRequest, swap_id)
    if swap is None:
        raise NotFoundError("Swap request not found")
    if swap.status != SwapStatus.PENDING:
        raise ConflictError(f"Swap request is already {swap.status.value}")
    if swap.target_assignment_id is None:
        raise ConflictError("Open swaps (no target assignment) aren't supported in v1 - assign a target first")

    source = _get_published_assignment(db, swap.source_assignment_id)
    target = _get_published_assignment(db, swap.target_assignment_id)

    # Atomic mutation: swap the employee_id on both assignments in the same
    # transaction, so a crash mid-operation can never leave one shift
    # reassigned without its counterpart.
    source.employee_id, target.employee_id = target.employee_id, source.employee_id
    source.manually_edited = True
    target.manually_edited = True

    swap.status = SwapStatus.APPROVED
    swap.resolved_by_user_id = resolver.id
    swap.resolved_at = datetime.now(timezone.utc)
    db.flush()

    affected_run_ids = {source.schedule_run_id, target.schedule_run_id}
    for run_id in affected_run_ids:
        run = db.get(ScheduleRun, run_id)
        run_compliance_check(db, run)

    db.commit()
    db.refresh(swap)
    return swap


def deny_swap(db: Session, swap_id: uuid.UUID, resolver: User) -> SwapRequest:
    swap = db.get(SwapRequest, swap_id)
    if swap is None:
        raise NotFoundError("Swap request not found")
    if swap.status != SwapStatus.PENDING:
        raise ConflictError(f"Swap request is already {swap.status.value}")

    swap.status = SwapStatus.DENIED
    swap.resolved_by_user_id = resolver.id
    swap.resolved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(swap)
    return swap
