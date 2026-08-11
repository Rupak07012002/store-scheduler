import uuid
from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.exceptions import ForbiddenError, NotFoundError
from app.db import get_db
from app.models.store import Store
from app.models.user import User, UserRole
from app.schemas.forecast import HeadcountRequirementRead
from app.services.forecasting.seasonal_baseline import SeasonalBaselineForecaster
from app.services.labor_requirements import translate_to_headcount

router = APIRouter(prefix="/forecasts", tags=["forecasts"])

_forecaster = SeasonalBaselineForecaster()


def _next_monday(from_date: date) -> date:
    return from_date + timedelta(days=(7 - from_date.weekday()) % 7 or 7)


@router.get("/{store_id}", response_model=list[HeadcountRequirementRead])
def get_forecast(
    store_id: uuid.UUID,
    week_start: date | None = Query(None, description="Defaults to next Monday"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[HeadcountRequirementRead]:
    if current_user.role != UserRole.OWNER and current_user.store_id != store_id:
        raise ForbiddenError("Not scoped to this store")

    store = db.get(Store, store_id)
    if store is None:
        raise NotFoundError("Store not found")

    target_week_start = week_start or _next_monday(date.today())
    forecast_points = _forecaster.predict_week(db, store_id, target_week_start)
    requirements = translate_to_headcount(forecast_points, store)

    return [
        HeadcountRequirementRead(
            date=r.date,
            shift_template_id=r.shift_template_id,
            shift_template_name=r.shift_template_name,
            predicted_footfall=r.predicted_footfall,
            required_headcount=r.required_headcount,
        )
        for r in requirements
    ]
