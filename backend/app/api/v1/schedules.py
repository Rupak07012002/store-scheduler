import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_role
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.db import get_db
from app.models.compliance_flag import ComplianceFlag, ComplianceFlagSeverity
from app.models.schedule_run import ScheduleRun, ScheduleRunStatus
from app.models.shift_assignment import AssignmentStatus, ShiftAssignment
from app.models.user import User, UserRole
from app.schemas.compliance import AddAssignmentRequest, ComplianceFlagRead
from app.schemas.schedule import GenerateScheduleRequest, ScheduleRunRead
from app.services.compliance import run_compliance_check
from app.services.schedule_generation import generate_schedule_run

router = APIRouter(prefix="/schedules", tags=["schedules"])


def _assert_store_scope(user: User, store_id: uuid.UUID) -> None:
    if user.role != UserRole.OWNER and user.store_id != store_id:
        raise ForbiddenError("Not scoped to this store")


def _get_run_or_404(db: Session, schedule_run_id: uuid.UUID) -> ScheduleRun:
    run = db.get(ScheduleRun, schedule_run_id)
    if run is None:
        raise NotFoundError("Schedule run not found")
    return run


@router.post("/generate", response_model=ScheduleRunRead, status_code=201)
def generate(
    payload: GenerateScheduleRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.OWNER, UserRole.STORE_MANAGER)),
) -> ScheduleRun:
    _assert_store_scope(current_user, payload.store_id)
    run = generate_schedule_run(
        db, store_id=payload.store_id, week_start=payload.week_start, generated_by=str(current_user.id)
    )
    run_compliance_check(db, run)
    db.commit()
    db.refresh(run)
    return run


@router.get("", response_model=list[ScheduleRunRead])
def list_schedule_runs(
    store_id: uuid.UUID = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ScheduleRun]:
    _assert_store_scope(current_user, store_id)
    query = db.query(ScheduleRun).filter(ScheduleRun.store_id == store_id)
    if current_user.role == UserRole.EMPLOYEE:
        # Employees never see drafts - only published schedules are visible to them.
        query = query.filter(ScheduleRun.status == ScheduleRunStatus.PUBLISHED)
    return query.order_by(ScheduleRun.week_start_date.desc()).all()


@router.get("/{schedule_run_id}", response_model=ScheduleRunRead)
def get_schedule_run(
    schedule_run_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ScheduleRun:
    run = _get_run_or_404(db, schedule_run_id)
    _assert_store_scope(current_user, run.store_id)
    if current_user.role == UserRole.EMPLOYEE and run.status != ScheduleRunStatus.PUBLISHED:
        raise NotFoundError("Schedule run not found")
    return run


@router.get("/{schedule_run_id}/compliance", response_model=list[ComplianceFlagRead])
def get_compliance_flags(
    schedule_run_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.OWNER, UserRole.STORE_MANAGER)),
) -> list[ComplianceFlag]:
    run = _get_run_or_404(db, schedule_run_id)
    _assert_store_scope(current_user, run.store_id)
    return (
        db.query(ComplianceFlag)
        .filter(ComplianceFlag.schedule_run_id == schedule_run_id, ComplianceFlag.resolved.is_(False))
        .all()
    )


@router.post("/{schedule_run_id}/assignments", response_model=ScheduleRunRead, status_code=201)
def add_assignment(
    schedule_run_id: uuid.UUID,
    payload: AddAssignmentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.OWNER, UserRole.STORE_MANAGER)),
) -> ScheduleRun:
    run = _get_run_or_404(db, schedule_run_id)
    _assert_store_scope(current_user, run.store_id)
    if run.status == ScheduleRunStatus.PUBLISHED:
        raise ConflictError("Cannot edit a published schedule run - use the swap workflow instead")

    db.add(
        ShiftAssignment(
            schedule_run_id=run.id,
            employee_id=payload.employee_id,
            shift_template_id=payload.shift_template_id,
            date=payload.date,
            status=AssignmentStatus.EDITED,
            manually_edited=True,
        )
    )
    run.status = ScheduleRunStatus.UNDER_REVIEW
    db.flush()
    run_compliance_check(db, run)
    db.commit()
    db.refresh(run)
    return run


@router.delete("/{schedule_run_id}/assignments/{assignment_id}", response_model=ScheduleRunRead)
def remove_assignment(
    schedule_run_id: uuid.UUID,
    assignment_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.OWNER, UserRole.STORE_MANAGER)),
) -> ScheduleRun:
    run = _get_run_or_404(db, schedule_run_id)
    _assert_store_scope(current_user, run.store_id)
    if run.status == ScheduleRunStatus.PUBLISHED:
        raise ConflictError("Cannot edit a published schedule run - use the swap workflow instead")

    assignment = db.get(ShiftAssignment, assignment_id)
    if assignment is None or assignment.schedule_run_id != run.id:
        raise NotFoundError("Assignment not found on this schedule run")

    db.delete(assignment)
    run.status = ScheduleRunStatus.UNDER_REVIEW
    db.flush()
    run_compliance_check(db, run)
    db.commit()
    db.refresh(run)
    return run


@router.post("/{schedule_run_id}/publish", response_model=ScheduleRunRead)
def publish(
    schedule_run_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.OWNER, UserRole.STORE_MANAGER)),
) -> ScheduleRun:
    run = _get_run_or_404(db, schedule_run_id)
    _assert_store_scope(current_user, run.store_id)
    if run.status == ScheduleRunStatus.PUBLISHED:
        raise ConflictError("Schedule run is already published")

    unresolved_hard_flags = (
        db.query(ComplianceFlag)
        .filter(
            ComplianceFlag.schedule_run_id == run.id,
            ComplianceFlag.resolved.is_(False),
            ComplianceFlag.severity == ComplianceFlagSeverity.HARD,
        )
        .count()
    )
    if unresolved_hard_flags > 0:
        raise ConflictError(
            f"Cannot publish: {unresolved_hard_flags} unresolved hard compliance flag(s). "
            "Resolve them or adjust assignments first."
        )

    run.status = ScheduleRunStatus.PUBLISHED
    run.published_at = datetime.now(timezone.utc)
    for assignment in run.assignments:
        assignment.status = AssignmentStatus.PUBLISHED

    db.commit()
    db.refresh(run)
    return run
