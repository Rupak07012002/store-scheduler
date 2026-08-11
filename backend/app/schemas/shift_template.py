import uuid
from datetime import time

from pydantic import BaseModel


class ShiftTemplateBase(BaseModel):
    name: str
    start_time: time
    end_time: time
    day_of_week: int | None = None  # NULL = applies every day


class ShiftTemplateCreate(ShiftTemplateBase):
    pass


class ShiftTemplateRead(ShiftTemplateBase):
    id: uuid.UUID
    store_id: uuid.UUID
    is_active: bool

    class Config:
        from_attributes = True
