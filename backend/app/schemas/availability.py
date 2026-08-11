import uuid
from datetime import date, time

from pydantic import BaseModel


class AvailabilityBase(BaseModel):
    day_of_week: int  # 0=Monday .. 6=Sunday
    start_time: time
    end_time: time
    is_available: bool = True
    effective_from: date | None = None
    effective_until: date | None = None


class AvailabilityCreate(AvailabilityBase):
    pass


class AvailabilityRead(AvailabilityBase):
    id: uuid.UUID
    employee_id: uuid.UUID

    class Config:
        from_attributes = True


class TimeOffRequestCreate(BaseModel):
    start_date: date
    end_date: date
    reason: str | None = None


class TimeOffRequestRead(BaseModel):
    id: uuid.UUID
    employee_id: uuid.UUID
    start_date: date
    end_date: date
    reason: str | None
    status: str

    class Config:
        from_attributes = True
