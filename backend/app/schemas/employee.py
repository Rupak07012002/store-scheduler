import uuid
from datetime import date

from pydantic import BaseModel

from app.models.employee import EmploymentType


class EmployeeBase(BaseModel):
    full_name: str
    email: str | None = None
    phone: str | None = None
    hire_date: date | None = None
    employment_type: EmploymentType = EmploymentType.PART_TIME
    wage_rate: float | None = None


class EmployeeCreate(EmployeeBase):
    store_id: uuid.UUID


class EmployeeUpdate(BaseModel):
    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    employment_type: EmploymentType | None = None
    wage_rate: float | None = None
    is_active: bool | None = None


class EmployeeRead(EmployeeBase):
    id: uuid.UUID
    store_id: uuid.UUID
    is_active: bool

    class Config:
        from_attributes = True
