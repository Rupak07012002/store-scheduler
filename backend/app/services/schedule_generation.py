import uuid
from datetime import date

from sqlalchemy.orm import Session

from app.config import settings
from app.models.employee import Employee
from app.models.schedule_run import ScheduleRun, ScheduleRunStatus, SolverStatus
from app.models.shift_assignment import AssignmentStatus, ShiftAssignment
from app.models.shift_template import ShiftTemplate
from app.models.store import Store
from app.services.forecasting.seasonal_baseline import SeasonalBaselineForecaster
from app.services.labor_requirements import translate_to_headcount
from app.services.labor_rules import get_effective_labor_rules
from app.services.optimization.availability_index import build_availability_index
from app.services.optimization.cp_sat_model import solve_schedule

_forecaster = SeasonalBaselineForecaster()

_SOLVER_STATUS_MAP = {
    "optimal": SolverStatus.OPTIMAL,
    "feasible": SolverStatus.FEASIBLE,
    "infeasible": SolverStatus.INFEASIBLE,
}


def generate_schedule_run(db: Session, store_id: uuid.UUID, week_start: date, generated_by: str = "system") -> ScheduleRun:
    store = db.get(Store, store_id)
    if store is None:
        raise ValueError(f"Store {store_id} not found")

    templates = (
        db.query(ShiftTemplate)
        .filter(ShiftTemplate.store_id == store_id, ShiftTemplate.is_active.is_(True))
        .all()
    )
    employees = db.query(Employee).filter(Employee.store_id == store_id, Employee.is_active.is_(True)).all()

    forecast_points = _forecaster.predict_week(db, store_id, week_start)
    requirements = translate_to_headcount(forecast_points, store)
    required_headcount = {(r.date, r.shift_template_id): r.required_headcount for r in requirements}

    availability_index = build_availability_index(db, [e.id for e in employees])
    labor_rules = get_effective_labor_rules(db, store_id, week_start)

    result = solve_schedule(
        employees=employees,
        week_start=week_start,
        templates=templates,
        required_headcount=required_headcount,
        availability_index=availability_index,
        labor_rules=labor_rules,
        time_limit_seconds=settings.solver_time_limit_seconds,
    )

    forecast_snapshot = {
        "generated_for_week_start": week_start.isoformat(),
        "requirements": [
            {
                "date": r.date.isoformat(),
                "shift_template_id": str(r.shift_template_id),
                "shift_template_name": r.shift_template_name,
                "predicted_footfall": r.predicted_footfall,
                "required_headcount": r.required_headcount,
            }
            for r in requirements
        ],
        "understaffed_slots": [
            {
                "date": s.date.isoformat(),
                "shift_template_id": str(s.shift_template_id),
                "required": s.required,
                "filled": s.filled,
            }
            for s in result.understaffed_slots
        ],
    }

    schedule_run = ScheduleRun(
        store_id=store_id,
        week_start_date=week_start,
        status=ScheduleRunStatus.DRAFT,
        solver_status=_SOLVER_STATUS_MAP[result.status],
        objective_value=result.objective_value,
        forecast_snapshot=forecast_snapshot,
        generated_by=generated_by,
    )
    db.add(schedule_run)
    db.flush()

    for assignment in result.assignments:
        db.add(
            ShiftAssignment(
                schedule_run_id=schedule_run.id,
                employee_id=assignment.employee_id,
                shift_template_id=assignment.shift_template_id,
                date=assignment.date,
                status=AssignmentStatus.PROPOSED,
            )
        )

    db.commit()
    db.refresh(schedule_run)
    return schedule_run
