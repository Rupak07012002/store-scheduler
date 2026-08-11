import uuid
from collections import defaultdict
from datetime import date

from sqlalchemy.orm import Session

from app.models.compliance_flag import ComplianceFlag, ComplianceFlagSeverity, ComplianceFlagType
from app.models.schedule_run import ScheduleRun
from app.models.shift_assignment import ShiftAssignment
from app.models.shift_template import ShiftTemplate
from app.services.labor_rules import get_effective_labor_rules
from app.services.optimization.constraints import duration_minutes, rest_gap_hours


def run_compliance_check(db: Session, schedule_run: ScheduleRun) -> list[ComplianceFlag]:
    """
    Recomputes every ComplianceFlag for a run from its CURRENT
    ShiftAssignment rows (not the solver's original output) - this is what
    catches a manager's manual edit introducing a new violation the solver
    never would have allowed. Old flags for this run are cleared and
    replaced each call, since flags are a snapshot of "is this run
    compliant right now", not an accumulating log (the run's own audit trail
    of what changed lives on ShiftAssignment.manually_edited).

    HARD flags block publish (see schedules.py's publish endpoint); SOFT
    flags are informational only.

    Previously-open flags for this run are marked resolved=True (not
    deleted) before recomputing, so the audit trail shows "this run had an
    overtime flag that got fixed before publish" even after the issue goes
    away - only currently-detected issues get a fresh resolved=False row.
    """
    db.query(ComplianceFlag).filter(
        ComplianceFlag.schedule_run_id == schedule_run.id, ComplianceFlag.resolved.is_(False)
    ).update({"resolved": True})

    assignments = (
        db.query(ShiftAssignment).filter(ShiftAssignment.schedule_run_id == schedule_run.id).all()
    )
    templates = {
        t.id: t for t in db.query(ShiftTemplate).filter(ShiftTemplate.store_id == schedule_run.store_id).all()
    }
    labor_rules = get_effective_labor_rules(db, schedule_run.store_id, schedule_run.week_start_date)

    flags: list[ComplianceFlag] = []
    flags.extend(_check_coverage(schedule_run, assignments))
    flags.extend(_check_rest_and_consecutive_days(schedule_run, assignments, templates, labor_rules))
    flags.extend(_check_overtime(schedule_run, assignments, templates, labor_rules))

    db.add_all(flags)
    db.flush()
    return flags


def _check_coverage(schedule_run: ScheduleRun, assignments: list[ShiftAssignment]) -> list[ComplianceFlag]:
    required_by_slot: dict[tuple[str, str], int] = {
        (r["date"], r["shift_template_id"]): r["required_headcount"]
        for r in schedule_run.forecast_snapshot.get("requirements", [])
    }
    filled_by_slot: dict[tuple[str, str], int] = defaultdict(int)
    for a in assignments:
        filled_by_slot[(a.date.isoformat(), str(a.shift_template_id))] += 1

    flags = []
    for slot, required in required_by_slot.items():
        filled = filled_by_slot.get(slot, 0)
        if filled < required:
            flags.append(
                ComplianceFlag(
                    schedule_run_id=schedule_run.id,
                    flag_type=ComplianceFlagType.UNDERSTAFFED_SLOT,
                    severity=ComplianceFlagSeverity.HARD,
                    message=f"{slot[0]} needs {required} staff but only {filled} are scheduled.",
                )
            )
        elif filled > required:
            flags.append(
                ComplianceFlag(
                    schedule_run_id=schedule_run.id,
                    flag_type=ComplianceFlagType.OVERSTAFFED_SLOT,
                    severity=ComplianceFlagSeverity.SOFT,
                    message=f"{slot[0]} only needs {required} staff but {filled} are scheduled.",
                )
            )
    return flags


def _check_rest_and_consecutive_days(
    schedule_run: ScheduleRun,
    assignments: list[ShiftAssignment],
    templates: dict[uuid.UUID, ShiftTemplate],
    labor_rules,
) -> list[ComplianceFlag]:
    by_employee: dict[uuid.UUID, list[ShiftAssignment]] = defaultdict(list)
    for a in assignments:
        by_employee[a.employee_id].append(a)

    flags = []
    min_rest = float(labor_rules.min_rest_hours_between_shifts)
    max_consecutive = labor_rules.max_consecutive_days

    for employee_id, emp_assignments in by_employee.items():
        emp_assignments.sort(key=lambda a: a.date)

        for i in range(len(emp_assignments) - 1):
            a, b = emp_assignments[i], emp_assignments[i + 1]
            if a.date == b.date:
                continue  # same-day double-booking isn't a rest violation - handled as data integrity elsewhere
            gap = rest_gap_hours(a.date, templates[a.shift_template_id].end_time, b.date, templates[b.shift_template_id].start_time)
            if 0 <= gap < min_rest:
                flags.append(
                    ComplianceFlag(
                        schedule_run_id=schedule_run.id,
                        employee_id=employee_id,
                        flag_type=ComplianceFlagType.INSUFFICIENT_REST,
                        severity=ComplianceFlagSeverity.HARD,
                        message=f"Only {gap:.1f}h rest between {a.date} and {b.date} shifts (minimum is {min_rest}h).",
                    )
                )

        worked_dates = sorted({a.date for a in emp_assignments})
        run_length = 1
        for i in range(1, len(worked_dates)):
            if (worked_dates[i] - worked_dates[i - 1]).days == 1:
                run_length += 1
            else:
                run_length = 1
            if run_length > max_consecutive:
                flags.append(
                    ComplianceFlag(
                        schedule_run_id=schedule_run.id,
                        employee_id=employee_id,
                        flag_type=ComplianceFlagType.TOO_MANY_CONSECUTIVE_DAYS,
                        severity=ComplianceFlagSeverity.HARD,
                        message=f"Scheduled {run_length} consecutive days (maximum is {max_consecutive}).",
                    )
                )
                break  # one flag per employee is enough signal; avoid duplicate flags per extra day

    return flags


def _check_overtime(
    schedule_run: ScheduleRun,
    assignments: list[ShiftAssignment],
    templates: dict[uuid.UUID, ShiftTemplate],
    labor_rules,
) -> list[ComplianceFlag]:
    minutes_by_employee: dict[uuid.UUID, int] = defaultdict(int)
    for a in assignments:
        t = templates[a.shift_template_id]
        minutes_by_employee[a.employee_id] += duration_minutes(t.start_time, t.end_time)

    max_regular_minutes = int(float(labor_rules.max_hours_before_overtime) * 60)
    flags = []
    for employee_id, minutes in minutes_by_employee.items():
        if minutes > max_regular_minutes:
            flags.append(
                ComplianceFlag(
                    schedule_run_id=schedule_run.id,
                    employee_id=employee_id,
                    flag_type=ComplianceFlagType.OVERTIME_RISK,
                    severity=ComplianceFlagSeverity.SOFT,
                    message=f"Scheduled {minutes / 60:.1f}h, which is {(minutes - max_regular_minutes) / 60:.1f}h over the {labor_rules.max_hours_before_overtime}h overtime threshold.",
                )
            )
    return flags
