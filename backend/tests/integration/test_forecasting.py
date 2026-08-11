"""
Verifies the seasonal-baseline forecaster recovers seeded day-of-week
seasonality (Phase 2 acceptance criterion from the plan). Runs against the
real Postgres instance (via `make test` / `docker compose exec backend
pytest`) since the models use Postgres-specific column types - see
docs/architecture.md for why this is an integration test, not a pure unit
test with an in-memory DB.
"""

from datetime import date, time, timedelta

import pytest

from app.db import SessionLocal
from app.models.footfall import FootfallRecord, FootfallSource
from app.models.shift_template import ShiftTemplate
from app.models.store import Store
from app.services.forecasting.seasonal_baseline import SeasonalBaselineForecaster


@pytest.fixture
def db_session():
    session = SessionLocal()
    yield session
    session.rollback()
    session.close()


def test_forecaster_recovers_weekend_seasonality(db_session):
    store = Store(name="Test Store - Forecasting", footfall_to_staff_ratio=25.0, min_staff_floor=1)
    db_session.add(store)
    db_session.flush()

    template = ShiftTemplate(store_id=store.id, name="Afternoon", start_time=time(13, 0), end_time=time(18, 0))
    db_session.add(template)
    db_session.flush()

    today = date.today()
    for day_offset in range(28):
        d = today - timedelta(days=day_offset)
        is_weekend = d.weekday() >= 5
        count = 60 if is_weekend else 20  # deliberately large, unambiguous gap
        db_session.add(
            FootfallRecord(
                store_id=store.id,
                date=d,
                hour_block=13,
                transaction_count=count,
                source=FootfallSource.SYNTHETIC,
            )
        )
    db_session.flush()

    forecaster = SeasonalBaselineForecaster()
    next_monday = today + timedelta(days=(7 - today.weekday()) % 7 or 7)
    points = forecaster.predict_week(db_session, store.id, next_monday)

    by_weekday = {(next_monday + timedelta(days=i)).weekday(): p.predicted_footfall for i, p in enumerate(points)}

    weekday_predictions = [v for wd, v in by_weekday.items() if wd < 5]
    weekend_predictions = [v for wd, v in by_weekday.items() if wd >= 5]

    assert min(weekend_predictions) > max(weekday_predictions), (
        f"Expected weekend predictions to exceed weekday predictions: "
        f"weekday={weekday_predictions} weekend={weekend_predictions}"
    )

    db_session.rollback()
