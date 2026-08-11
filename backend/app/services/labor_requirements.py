import math
import uuid
from dataclasses import dataclass
from datetime import date

from app.config import settings
from app.models.store import Store
from app.services.forecasting.interface import ForecastPoint


@dataclass
class HeadcountRequirement:
    date: date
    shift_template_id: uuid.UUID
    shift_template_name: str
    predicted_footfall: float
    required_headcount: int


def translate_to_headcount(forecast_points: list[ForecastPoint], store: Store) -> list[HeadcountRequirement]:
    """
    required_headcount = max(min_staff_floor, ceil(predicted_footfall / ratio)).

    ratio and floor are per-store overrides of the app-wide defaults - see
    Store.footfall_to_staff_ratio / min_staff_floor docstrings. The ratio is
    owner-tunable specifically because it's a business judgment call
    ("how many customers can one staff member handle per hour"), not
    something the model can learn from data alone.
    """
    ratio = float(store.footfall_to_staff_ratio) if store.footfall_to_staff_ratio else settings.default_footfall_to_staff_ratio
    floor = store.min_staff_floor if store.min_staff_floor is not None else settings.default_min_staff_floor

    return [
        HeadcountRequirement(
            date=point.date,
            shift_template_id=point.shift_template_id,
            shift_template_name=point.shift_template_name,
            predicted_footfall=point.predicted_footfall,
            required_headcount=max(floor, math.ceil(point.predicted_footfall / ratio)),
        )
        for point in forecast_points
    ]
