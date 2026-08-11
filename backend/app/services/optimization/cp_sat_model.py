import uuid
from dataclasses import dataclass, field
from datetime import date, timedelta

from ortools.sat.python import cp_model

from app.models.employee import Employee
from app.models.labor_rule_config import LaborRuleConfig
from app.models.shift_template import ShiftTemplate
from app.services.optimization.availability_index import AvailabilityIndex
from app.services.optimization.constraints import duration_minutes, rest_gap_hours
from app.services.optimization.cost import objective_weight_cents_per_hour

UNDERSTAFF_PENALTY_PER_HEAD = 100_000  # dominates the objective - coverage matters far more than hours
OVERTIME_PENALTY_PER_MINUTE = 50  # soft-discourages OT without forbidding it (retail sometimes needs it)


@dataclass
class Assignment:
    employee_id: uuid.UUID
    date: date
    shift_template_id: uuid.UUID


@dataclass
class UnderstaffedSlot:
    date: date
    shift_template_id: uuid.UUID
    required: int
    filled: int


@dataclass
class SolveResult:
    status: str  # "optimal" | "feasible" | "infeasible"
    objective_value: float | None
    assignments: list[Assignment] = field(default_factory=list)
    understaffed_slots: list[UnderstaffedSlot] = field(default_factory=list)
    overtime_minutes_by_employee: dict[uuid.UUID, int] = field(default_factory=dict)


def solve_schedule(
    employees: list[Employee],
    week_start: date,
    templates: list[ShiftTemplate],
    required_headcount: dict[tuple[date, uuid.UUID], int],
    availability_index: AvailabilityIndex,
    labor_rules: LaborRuleConfig,
    time_limit_seconds: float,
) -> SolveResult:
    """
    Builds and solves the weekly shift-assignment CP-SAT model.

    Decision variables: assign[employee, date, template] (boolean), created
    only for combinations where the template runs on that weekday AND the
    employee is available - unavailable combinations are never given a
    variable (cheaper than a runtime constraint forcing it to 0).

    See docs/forecasting-and-optimization.md for the full plain-language
    walkthrough of every constraint below.
    """
    model = cp_model.CpModel()
    week_dates = [week_start + timedelta(days=i) for i in range(7)]

    assign_vars: dict[tuple[uuid.UUID, date, uuid.UUID], cp_model.IntVar] = {}
    for d in week_dates:
        weekday = d.weekday()
        for template in templates:
            if template.day_of_week is not None and template.day_of_week != weekday:
                continue
            for employee in employees:
                if availability_index.is_available(employee.id, d, template):
                    assign_vars[(employee.id, d, template.id)] = model.NewBoolVar(
                        f"assign_{employee.id}_{d.isoformat()}_{template.id}"
                    )

    # --- Coverage (with penalized understaffing slack so an infeasible
    #     week still returns a usable, flagged best-effort schedule) ---
    understaff_vars: dict[tuple[date, uuid.UUID], cp_model.IntVar] = {}
    for (d, template_id), required in required_headcount.items():
        if required <= 0:
            continue
        vars_for_slot = [v for (eid, vd, tid), v in assign_vars.items() if vd == d and tid == template_id]
        slack = model.NewIntVar(0, required, f"understaff_{d.isoformat()}_{template_id}")
        model.Add(sum(vars_for_slot) + slack >= required)
        understaff_vars[(d, template_id)] = slack

    # --- One template per employee per day ---
    for employee in employees:
        for d in week_dates:
            vars_for_day = [v for (eid, vd, tid), v in assign_vars.items() if eid == employee.id and vd == d]
            if vars_for_day:
                model.Add(sum(vars_for_day) <= 1)

    # --- Weekly hours cap, soft (overtime allowed but penalized) ---
    template_by_id = {t.id: t for t in templates}
    max_regular_minutes = int(float(labor_rules.max_hours_before_overtime) * 60)
    overtime_vars: dict[uuid.UUID, cp_model.IntVar] = {}
    for employee in employees:
        terms = [
            (v, duration_minutes(template_by_id[tid].start_time, template_by_id[tid].end_time))
            for (eid, vd, tid), v in assign_vars.items()
            if eid == employee.id
        ]
        if not terms:
            continue
        total_minutes_expr = sum(v * minutes for v, minutes in terms)
        overtime = model.NewIntVar(0, 7 * 24 * 60, f"overtime_{employee.id}")
        model.Add(total_minutes_expr <= max_regular_minutes + overtime)
        overtime_vars[employee.id] = overtime

    # --- Minimum rest between shifts on adjacent days ---
    min_rest_hours = float(labor_rules.min_rest_hours_between_shifts)
    for i in range(len(week_dates) - 1):
        d, next_d = week_dates[i], week_dates[i + 1]
        for template in templates:
            if template.day_of_week is not None and template.day_of_week != d.weekday():
                continue
            for next_template in templates:
                if next_template.day_of_week is not None and next_template.day_of_week != next_d.weekday():
                    continue
                gap = rest_gap_hours(d, template.end_time, next_d, next_template.start_time)
                if gap >= min_rest_hours:
                    continue
                for employee in employees:
                    v1 = assign_vars.get((employee.id, d, template.id))
                    v2 = assign_vars.get((employee.id, next_d, next_template.id))
                    if v1 is not None and v2 is not None:
                        model.Add(v1 + v2 <= 1)

    # --- Max consecutive working days (rolling window over the week) ---
    max_consecutive = labor_rules.max_consecutive_days
    window_size = max_consecutive + 1
    if window_size <= 7:
        for employee in employees:
            for start_idx in range(0, 7 - window_size + 1):
                window_dates = week_dates[start_idx : start_idx + window_size]
                day_worked_terms = []
                for d in window_dates:
                    vars_for_day = [v for (eid, vd, tid), v in assign_vars.items() if eid == employee.id and vd == d]
                    day_worked_terms.extend(vars_for_day)
                if day_worked_terms:
                    model.Add(sum(day_worked_terms) <= max_consecutive)

    # --- Objective: minimize weighted hours + understaffing + overtime penalties ---
    cost_terms = []
    for (eid, vd, tid), v in assign_vars.items():
        employee = next(e for e in employees if e.id == eid)
        minutes = duration_minutes(template_by_id[tid].start_time, template_by_id[tid].end_time)
        cost_terms.append(v * (objective_weight_cents_per_hour(employee) * minutes))

    understaff_terms = [v * UNDERSTAFF_PENALTY_PER_HEAD for v in understaff_vars.values()]
    overtime_terms = [v * OVERTIME_PENALTY_PER_MINUTE for v in overtime_vars.values()]

    model.Minimize(sum(cost_terms) + sum(understaff_terms) + sum(overtime_terms))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit_seconds
    status = solver.Solve(model)

    if status == cp_model.INFEASIBLE or status == cp_model.MODEL_INVALID:
        return SolveResult(status="infeasible", objective_value=None)

    status_str = "optimal" if status == cp_model.OPTIMAL else "feasible"

    assignments = [
        Assignment(employee_id=eid, date=vd, shift_template_id=tid)
        for (eid, vd, tid), v in assign_vars.items()
        if solver.Value(v) == 1
    ]

    understaffed_slots = [
        UnderstaffedSlot(
            date=d,
            shift_template_id=tid,
            required=required_headcount[(d, tid)],
            filled=required_headcount[(d, tid)] - solver.Value(slack),
        )
        for (d, tid), slack in understaff_vars.items()
        if solver.Value(slack) > 0
    ]

    overtime_by_employee = {eid: solver.Value(v) for eid, v in overtime_vars.items() if solver.Value(v) > 0}

    return SolveResult(
        status=status_str,
        objective_value=solver.ObjectiveValue(),
        assignments=assignments,
        understaffed_slots=understaffed_slots,
        overtime_minutes_by_employee=overtime_by_employee,
    )
