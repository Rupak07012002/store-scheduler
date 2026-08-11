import uuid
from dataclasses import dataclass
from datetime import date
from typing import Protocol

from sqlalchemy.orm import Session


@dataclass
class ForecastPoint:
    date: date
    shift_template_id: uuid.UUID
    shift_template_name: str
    predicted_footfall: float


class Forecaster(Protocol):
    """
    Swap-in seam: today this is SeasonalBaselineForecaster. Once 12+ months
    of real Shopify data exists, a Prophet/XGBoost implementation can be
    dropped in behind this same interface without touching
    labor_requirements.py, the optimizer, or any API route - see
    docs/scaling-guide.md.
    """

    def predict_week(self, db: Session, store_id: uuid.UUID, week_start: date) -> list[ForecastPoint]: ...
