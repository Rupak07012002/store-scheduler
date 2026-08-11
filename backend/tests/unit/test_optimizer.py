"""
Unit tests for the CP-SAT optimizer (Phase 3 acceptance criteria from the
plan): removing availability actually zeroes out the variable, a too-short
rest window gets blocked, max-consecutive-days is respected, and a 30-
employee store solves within the configured time limit.

These construct plain (unpersisted) model objects directly - no DB needed,
since solve_schedule() takes plain Python data in and out.
"""

import time as time_module
import uuid
from datetime import date, time, timedelta

from app.models.employee import Employee
from app.models.labor_rule_config import LaborRuleConfig
from app.models.shift_template import ShiftTemplate
from app.services.optimization.availability_index import AvailabilityIndex
from app.services.optimization.cp_sat_model import solve_schedule

WEEK_START = date(2026, 8, 17)  # a Monday


def make_employee(name: str = "Test Employee") -> Employee:
    return Employee(id=uuid.uuid4(), store_id=uuid.uuid4(), full_name=name, wage_rate=None, is_active=True)


def make_template(name: str, start: time, end: time, day_of_week: int | None = None) -> ShiftTemplate:
    return ShiftTemplate(id=uuid.uuid4(), store_id=uuid.uuid4(), name=name, start_time=start, end_time=end, day_of_week=day_of_week)


def make_labor_rules(**overrides) -> LaborRuleConfig:
    defaults = dict(
        max_hours_before_overtime=40.0,
        overtime_multiplier=1.5,
        min_rest_hours_between_shifts=10.0,
        required_break_minutes=30,
        max_consecutive_days=6,
        effective_from=WEEK_START,
    )
    defaults.update(overrides)
    return LaborRuleConfig(id=uuid.uuid4(), store_id=None, **defaults)


def test_unavailable_employee_never_assigned():
    employee = make_employee()
    template = make_template("Morning", time(8, 0), time(13, 0))
    index = AvailabilityIndex()  # empty - nobody is available anywhere

    required = {(WEEK_START, template.id): 1}
    result = solve_schedule(
        employees=[employee],
        week_start=WEEK_START,
        templates=[template],
        required_headcount=required,
        availability_index=index,
        labor_rules=make_labor_rules(),
        time_limit_seconds=5,
    )

    assert result.assignments == []
    assert len(result.understaffed_slots) == 1
    assert result.understaffed_slots[0].filled == 0


class _AlwaysAvailable(AvailabilityIndex):
    def is_available(self, employee_id, target_date, template) -> bool:
        return True


def test_insufficient_rest_blocks_back_to_back_shifts():
    employee = make_employee()
    evening = make_template("Evening", time(18, 0), time(22, 0))
    morning = make_template("Morning", time(8, 0), time(13, 0))
    day0, day1 = WEEK_START, WEEK_START + timedelta(days=1)

    # gap between 22:00 day0 and 08:00 day1 is 10 hours; requiring 12h rest should block it.
    required = {(day0, evening.id): 1, (day1, morning.id): 1}
    result = solve_schedule(
        employees=[employee],
        week_start=WEEK_START,
        templates=[evening, morning],
        required_headcount=required,
        availability_index=_AlwaysAvailable(),
        labor_rules=make_labor_rules(min_rest_hours_between_shifts=12.0),
        time_limit_seconds=5,
    )

    assigned_slots = {(a.date, a.shift_template_id) for a in result.assignments}
    assert not ({(day0, evening.id), (day1, morning.id)} <= assigned_slots), (
        "Employee should not be assigned both shifts when the rest gap is below the configured minimum"
    )


def test_max_consecutive_days_forces_gaps():
    employee = make_employee()
    template = make_template("Morning", time(8, 0), time(13, 0))
    required = {(WEEK_START + timedelta(days=i), template.id): 1 for i in range(7)}

    result = solve_schedule(
        employees=[employee],
        week_start=WEEK_START,
        templates=[template],
        required_headcount=required,
        availability_index=_AlwaysAvailable(),
        labor_rules=make_labor_rules(max_consecutive_days=3),
        time_limit_seconds=5,
    )

    assigned_dates = {a.date for a in result.assignments}
    for i in range(4):  # every possible 4-consecutive-calendar-day window in the 7-day span
        window = {WEEK_START + timedelta(days=i + j) for j in range(4)}
        assert not window.issubset(assigned_dates), f"4 consecutive worked days found in window starting {WEEK_START + timedelta(days=i)}"

    # With only one employee covering 7 required days and a 3-consecutive-day cap,
    # at least one day must go unstaffed.
    assert len(result.understaffed_slots) >= 1


def test_solves_within_time_limit_for_30_employees():
    employees = [make_employee(f"Employee {i}") for i in range(30)]
    templates = [
        make_template("Morning", time(8, 0), time(13, 0)),
        make_template("Afternoon", time(13, 0), time(18, 0)),
        make_template("Evening", time(18, 0), time(22, 0)),
    ]
    required = {
        (WEEK_START + timedelta(days=d), t.id): 3 for d in range(7) for t in templates
    }

    started = time_module.monotonic()
    result = solve_schedule(
        employees=employees,
        week_start=WEEK_START,
        templates=templates,
        required_headcount=required,
        availability_index=_AlwaysAvailable(),
        labor_rules=make_labor_rules(),
        time_limit_seconds=45,
    )
    elapsed = time_module.monotonic() - started

    assert result.status in ("optimal", "feasible")
    assert elapsed < 45, f"Solve took {elapsed:.1f}s, expected well under the 45s time limit for this problem size"
