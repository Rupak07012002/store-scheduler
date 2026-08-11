import uuid
from datetime import date

from pydantic import BaseModel


class LaborRuleConfigBase(BaseModel):
    max_hours_before_overtime: float
    overtime_multiplier: float
    min_rest_hours_between_shifts: float
    required_break_minutes: int
    max_consecutive_days: int
    effective_from: date


class LaborRuleConfigCreate(LaborRuleConfigBase):
    store_id: uuid.UUID | None = None  # NULL = global default


class LaborRuleConfigRead(LaborRuleConfigBase):
    id: uuid.UUID
    store_id: uuid.UUID | None

    class Config:
        from_attributes = True
