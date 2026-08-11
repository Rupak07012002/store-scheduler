import uuid

from pydantic import BaseModel

from app.models.swap_request import SwapStatus


class SwapRequestCreate(BaseModel):
    source_assignment_id: uuid.UUID
    target_employee_id: uuid.UUID | None = None
    target_assignment_id: uuid.UUID | None = None


class SwapRequestRead(BaseModel):
    id: uuid.UUID
    source_assignment_id: uuid.UUID
    target_employee_id: uuid.UUID | None
    target_assignment_id: uuid.UUID | None
    status: SwapStatus

    class Config:
        from_attributes = True
