"""
Populates the database with a synthetic dataset shaped like real Shopify
data would be, so the whole pipeline (forecast -> optimize -> review ->
publish -> employee portal -> swaps) can be exercised end-to-end before any
real store/POS data is connected.

Per the plan: ~30 employees/store (240 total) and ~100 footfall
observations/store (34 days x 3 shift-template hours = 102/store).

Idempotent: if any Store already exists, this exits without changing
anything - re-run is a no-op rather than creating duplicates. To reseed from
scratch, drop and recreate the database (`docker compose down -v` then
`make migrate seed`).
"""

import random
import sys
from datetime import date, time, timedelta

sys.path.insert(0, ".")

from app.config import settings  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.db import SessionLocal  # noqa: E402
from app.models.availability import Availability  # noqa: E402
from app.models.employee import Employee, EmploymentType  # noqa: E402
from app.models.footfall import FootfallRecord, FootfallSource  # noqa: E402
from app.models.holiday_calendar import HolidayCalendarEntry  # noqa: E402
from app.models.labor_rule_config import LaborRuleConfig  # noqa: E402
from app.models.shift_template import ShiftTemplate  # noqa: E402
from app.models.store import Store  # noqa: E402
from app.models.user import User, UserRole  # noqa: E402

STORE_NAMES = [
    "Downtown Flagship",
    "Riverside Mall",
    "Northgate Plaza",
    "Westfield Commons",
    "Old Town Square",
    "Lakeside Center",
    "Southport Market",
    "Eastview Crossing",
]

FIRST_NAMES = [
    "Alex", "Jordan", "Taylor", "Morgan", "Casey", "Riley", "Jamie", "Avery",
    "Quinn", "Peyton", "Cameron", "Reese", "Skyler", "Rowan", "Emerson", "Hayden",
    "Dakota", "Blake", "Sydney", "Drew", "Elliot", "Finley", "Harper", "Kendall",
    "Logan", "Micah", "Nico", "Parker", "Sage", "Tatum",
]
LAST_NAMES = [
    "Anderson", "Brooks", "Chavez", "Diaz", "Edwards", "Foster", "Garcia",
    "Hughes", "Ibrahim", "Johnson", "Kim", "Lopez", "Martin", "Nguyen",
    "O'Brien", "Patel", "Quinn", "Reyes", "Singh", "Turner",
]

SHIFT_TEMPLATE_DEFS = [
    ("Morning", time(8, 0), time(13, 0)),
    ("Afternoon", time(13, 0), time(18, 0)),
    ("Evening", time(18, 0), time(22, 0)),
]

# Base transaction-count level per template, before day-of-week seasonality.
BASE_LEVEL = {"Morning": 18, "Afternoon": 30, "Evening": 22}
WEEKEND_MULTIPLIER = 1.6  # Sat/Sun busier than weekdays
NOISE_SPREAD = 4  # +/- random jitter


def build_footfall_rows(store_id, rng: random.Random) -> list[FootfallRecord]:
    rows = []
    today = date.today()
    for day_offset in range(settings.synthetic_footfall_days):
        d = today - timedelta(days=day_offset)
        is_weekend = d.weekday() >= 5
        for name, start_time, _ in SHIFT_TEMPLATE_DEFS:
            base = BASE_LEVEL[name] * (WEEKEND_MULTIPLIER if is_weekend else 1.0)
            noisy = max(0, round(base + rng.uniform(-NOISE_SPREAD, NOISE_SPREAD)))
            rows.append(
                FootfallRecord(
                    store_id=store_id,
                    date=d,
                    hour_block=start_time.hour,
                    transaction_count=noisy,
                    source=FootfallSource.SYNTHETIC,
                )
            )
    return rows


def build_availability(employee_id, rng: random.Random) -> list[Availability]:
    """
    Each employee is generally available on a random subset of 4-6 days,
    covering the full store-open window (08:00-22:00) so their availability
    spans all 3 shift templates on those days. This is a synthetic
    simplification - real per-employee time preferences come later via the
    self-service portal (Phase 5).
    """
    num_days = rng.randint(4, 6)
    days = rng.sample(range(7), num_days)
    return [
        Availability(
            employee_id=employee_id,
            day_of_week=d,
            start_time=time(8, 0),
            end_time=time(22, 0),
            is_available=True,
        )
        for d in days
    ]


def main() -> None:
    db = SessionLocal()
    try:
        if db.query(Store).first() is not None:
            print("Database already has stores - seed script is idempotent, exiting without changes.")
            return

        rng = random.Random(settings.seed_random_seed)

        print(f"Creating owner account: {settings.seed_owner_email}")
        owner = User(
            email=settings.seed_owner_email,
            hashed_password=hash_password(settings.seed_owner_password),
            full_name="Owner",
            role=UserRole.OWNER,
        )
        db.add(owner)

        db.add(
            LaborRuleConfig(
                store_id=None,
                max_hours_before_overtime=settings.default_max_hours_before_overtime,
                overtime_multiplier=settings.default_overtime_multiplier,
                min_rest_hours_between_shifts=settings.default_min_rest_hours_between_shifts,
                required_break_minutes=settings.default_required_break_minutes,
                max_consecutive_days=settings.default_max_consecutive_days,
                effective_from=date.today(),
            )
        )

        db.add_all(
            [
                HolidayCalendarEntry(store_id=None, date=date(date.today().year, 11, 28), label="Black Friday", expected_footfall_multiplier=2.2),
                HolidayCalendarEntry(store_id=None, date=date(date.today().year, 12, 24), label="Christmas Eve", expected_footfall_multiplier=1.8),
                HolidayCalendarEntry(store_id=None, date=date(date.today().year, 1, 1), label="New Year's Day", expected_footfall_multiplier=0.4),
            ]
        )

        total_employees = 0
        total_footfall = 0

        for store_name in STORE_NAMES:
            store = Store(
                name=store_name,
                address=f"{store_name} location",
                footfall_to_staff_ratio=settings.default_footfall_to_staff_ratio,
                min_staff_floor=settings.default_min_staff_floor,
                avg_transaction_value=settings.default_avg_transaction_value,
            )
            db.add(store)
            db.flush()  # need store.id before FKs below

            for name, start_time, end_time in SHIFT_TEMPLATE_DEFS:
                db.add(ShiftTemplate(store_id=store.id, name=name, start_time=start_time, end_time=end_time, day_of_week=None))

            manager_email = f"manager.{store_name.lower().replace(' ', '-')}@example.com"
            db.add(
                User(
                    email=manager_email,
                    hashed_password=hash_password(settings.seed_manager_password),
                    full_name=f"{store_name} Manager",
                    role=UserRole.STORE_MANAGER,
                    store_id=store.id,
                )
            )

            footfall_rows = build_footfall_rows(store.id, rng)
            db.add_all(footfall_rows)
            total_footfall += len(footfall_rows)

            for i in range(settings.synthetic_employees_per_store):
                employee = Employee(
                    store_id=store.id,
                    full_name=f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}",
                    employment_type=rng.choice([EmploymentType.FULL_TIME, EmploymentType.PART_TIME]),
                    hire_date=date.today() - timedelta(days=rng.randint(30, 1500)),
                    wage_rate=None,  # no wage data yet - confirmed with owner, see docs/scaling-guide.md
                )
                db.add(employee)
                db.flush()  # need employee.id for availability rows
                db.add_all(build_availability(employee.id, rng))
                total_employees += 1

                if i == 0:
                    # One demo employee login per store, so the employee
                    # portal can be exercised without creating 240 accounts.
                    db.add(
                        User(
                            email=f"employee.{store_name.lower().replace(' ', '-')}@example.com",
                            hashed_password=hash_password(settings.seed_manager_password),
                            full_name=employee.full_name,
                            role=UserRole.EMPLOYEE,
                            store_id=store.id,
                            linked_employee_id=employee.id,
                        )
                    )

        db.commit()

        print(f"Seeded {len(STORE_NAMES)} stores, {total_employees} employees, {total_footfall} footfall records.")
        print()
        print("Login credentials:")
        print(f"  Owner:    {settings.seed_owner_email} / {settings.seed_owner_password}")
        print(f"  Managers: manager.<store-slug>@example.com / {settings.seed_manager_password}")
        print(f"  Employees (1 demo login/store): employee.<store-slug>@example.com / {settings.seed_manager_password}")
        print("  Change these via seed_owner_password / seed_manager_password before any real deployment.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
