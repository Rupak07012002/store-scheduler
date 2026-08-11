import uuid
from datetime import date, timedelta

import pandas as pd
from sqlalchemy.orm import Session

from app.models.footfall import FootfallRecord
from app.models.shift_template import ShiftTemplate
from app.services.forecasting.holiday_calendar import get_multiplier
from app.services.forecasting.interface import ForecastPoint

RECENT_WINDOW_DAYS = 14
RECENT_WEIGHT = 0.6  # vs. 0.4 weight on the full-history average - a simple, explainable trend nudge


class SeasonalBaselineForecaster:
    """
    Predicts footfall as a blend of:
      - the full-history average transaction count for this store/template/
        day-of-week (captures baseline seasonality), and
      - the same average restricted to the last RECENT_WINDOW_DAYS (captures
        a recent trend), weighted more heavily,
    then applies any holiday multiplier for the target date.

    This is deliberately simple and inspectable (an owner can ask "why did
    it predict 40 customers for Saturday morning?" and get a plain answer:
    "that's what Saturday mornings have recently averaged") rather than a
    black-box model - appropriate given only weeks/months of data exist
    today. See docs/forecasting-and-optimization.md and the documented
    upgrade path to Prophet/gradient boosting once 12+ months of real data
    accumulates.
    """

    def predict_week(self, db: Session, store_id: uuid.UUID, week_start: date) -> list[ForecastPoint]:
        templates = (
            db.query(ShiftTemplate)
            .filter(ShiftTemplate.store_id == store_id, ShiftTemplate.is_active.is_(True))
            .all()
        )
        if not templates:
            return []

        records = db.query(FootfallRecord).filter(FootfallRecord.store_id == store_id).all()
        if not records:
            history = pd.DataFrame(columns=["date", "hour_block", "transaction_count"])
        else:
            history = pd.DataFrame(
                [{"date": r.date, "hour_block": r.hour_block, "transaction_count": r.transaction_count} for r in records]
            )
            history["weekday"] = pd.to_datetime(history["date"]).dt.weekday

        points: list[ForecastPoint] = []
        for offset in range(7):
            target_date = week_start + timedelta(days=offset)
            target_weekday = target_date.weekday()
            recent_cutoff = target_date - timedelta(days=RECENT_WINDOW_DAYS)

            for template in templates:
                if template.day_of_week is not None and template.day_of_week != target_weekday:
                    continue  # this template doesn't run on this day (see ShiftTemplate.day_of_week docstring)

                hour = template.start_time.hour
                same_slot = history[(history["hour_block"] == hour) & (history["weekday"] == target_weekday)] if not history.empty else history

                if same_slot.empty:
                    # Cold start: fall back to this template's overall average across all days.
                    same_template = history[history["hour_block"] == hour] if not history.empty else history
                    predicted = float(same_template["transaction_count"].mean()) if not same_template.empty else 0.0
                else:
                    overall_avg = float(same_slot["transaction_count"].mean())
                    recent = same_slot[pd.to_datetime(same_slot["date"]).dt.date >= recent_cutoff]
                    if recent.empty:
                        predicted = overall_avg
                    else:
                        recent_avg = float(recent["transaction_count"].mean())
                        predicted = RECENT_WEIGHT * recent_avg + (1 - RECENT_WEIGHT) * overall_avg

                predicted *= get_multiplier(db, store_id, target_date)

                points.append(
                    ForecastPoint(
                        date=target_date,
                        shift_template_id=template.id,
                        shift_template_name=template.name,
                        predicted_footfall=round(predicted, 1),
                    )
                )

        return points
