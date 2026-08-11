import enum
import uuid
from datetime import date

from sqlalchemy import Boolean, Date, Enum, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class EmploymentType(str, enum.Enum):
    FULL_TIME = "full_time"
    PART_TIME = "part_time"


class Employee(Base, TimestampMixin):
    """
    wage_rate is nullable and UNUSED by the v1 optimizer objective (owner has
    no wage data yet - confirmed). It's present now so that turning on true
    labor-cost minimization later (v1.1) is "populate this column + flip one
    line in the objective function", not a schema migration - see
    docs/scaling-guide.md.
    """

    __tablename__ = "employees"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("stores.id"), nullable=False)

    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    hire_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    employment_type: Mapped[EmploymentType] = mapped_column(
        Enum(EmploymentType, name="employment_type"), default=EmploymentType.PART_TIME
    )
    wage_rate: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    store: Mapped["Store"] = relationship(back_populates="employees")
    availability_windows: Mapped[list["Availability"]] = relationship(back_populates="employee")
    time_off_requests: Mapped[list["TimeOffRequest"]] = relationship(
        back_populates="employee", foreign_keys="TimeOffRequest.employee_id"
    )
    shift_assignments: Mapped[list["ShiftAssignment"]] = relationship(back_populates="employee")
