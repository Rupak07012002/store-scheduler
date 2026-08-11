import uuid
from datetime import date

from pydantic import BaseModel

from app.models.schedule_run import ScheduleRunStatus, SolverStatus
from app.models.shift_assignment import AssignmentStatus


class ShiftAssignmentRead(BaseModel):
    id: uuid.UUID
    employee_id: uuid.UUID
    shift_template_id: uuid.UUID
    date: date
    status: AssignmentStatus
    manually_edited: bool

    class Config:
        from_attributes = True


class ScheduleRunRead(BaseModel):
    id: uuid.UUID
    store_id: uuid.UUID
    week_start_date: date
    status: ScheduleRunStatus
    solver_status: SolverStatus | None
    objective_value: float | None
    generated_by: str
    assignments: list[ShiftAssignmentRead] = []

    class Config:
        from_attributes = True


class GenerateScheduleRequest(BaseModel):
    store_id: uuid.UUID
    week_start: date
