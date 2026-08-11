import uuid
from datetime import date

from pydantic import BaseModel


class HeadcountRequirementRead(BaseModel):
    date: date
    shift_template_id: uuid.UUID
    shift_template_name: str
    predicted_footfall: float
    required_headcount: int
