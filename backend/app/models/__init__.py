"""
Import every model module here so Base.metadata is fully populated for
Alembic autogeneration and for app startup - a model that isn't imported
anywhere is invisible to `alembic revision --autogenerate`.
"""

from app.models.availability import Availability
from app.models.base import Base
from app.models.compliance_flag import ComplianceFlag
from app.models.employee import Employee
from app.models.footfall import FootfallRecord
from app.models.holiday_calendar import HolidayCalendarEntry
from app.models.labor_rule_config import LaborRuleConfig
from app.models.schedule_run import ScheduleRun
from app.models.shift_assignment import ShiftAssignment
from app.models.shift_template import ShiftTemplate
from app.models.store import Store
from app.models.swap_request import SwapRequest
from app.models.time_off import TimeOffRequest
from app.models.user import User

__all__ = [
    "Base",
    "User",
    "Store",
    "Employee",
    "Availability",
    "TimeOffRequest",
    "ShiftTemplate",
    "FootfallRecord",
    "LaborRuleConfig",
    "HolidayCalendarEntry",
    "ScheduleRun",
    "ShiftAssignment",
    "SwapRequest",
    "ComplianceFlag",
]
