import uuid

from pydantic import BaseModel


class StoreBase(BaseModel):
    name: str
    address: str | None = None
    footfall_to_staff_ratio: float | None = None
    min_staff_floor: int | None = None
    avg_transaction_value: float | None = None


class StoreCreate(StoreBase):
    pass


class StoreUpdate(BaseModel):
    name: str | None = None
    address: str | None = None
    footfall_to_staff_ratio: float | None = None
    min_staff_floor: int | None = None
    avg_transaction_value: float | None = None
    is_active: bool | None = None


class StoreRead(StoreBase):
    id: uuid.UUID
    is_active: bool

    class Config:
        from_attributes = True
