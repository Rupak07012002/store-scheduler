import uuid
from datetime import date

from pydantic import BaseModel

from app.models.compliance_flag import ComplianceFlagSeverity, ComplianceFlagType


class ComplianceFlagRead(BaseModel):
    id: uuid.UUID
    employee_id: uuid.UUID | None
    flag_type: ComplianceFlagType
    severity: ComplianceFlagSeverity
    message: str
    resolved: bool

    class Config:
        from_attributes = True


class AddAssignmentRequest(BaseModel):
    employee_id: uuid.UUID
    shift_template_id: uuid.UUID
    date: date
