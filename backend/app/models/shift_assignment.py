import enum
import uuid
from datetime import date

from sqlalchemy import Boolean, Date, Enum, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class AssignmentStatus(str, enum.Enum):
    PROPOSED = "proposed"  # fresh out of the solver
    EDITED = "edited"  # manager changed it before publish
    PUBLISHED = "published"  # visible to the employee


class ShiftAssignment(Base, TimestampMixin):
    """
    One employee working one shift template on one date, within one
    ScheduleRun. `manually_edited` tracks whether a human overrode the
    solver's proposal - a rising manual-edit rate for a store is the
    documented v1 signal that its footfall_to_staff_ratio needs owner
    tuning (see docs/scaling-guide.md's feedback-loop section).
    """

    __tablename__ = "shift_assignments"
    __table_args__ = (
        UniqueConstraint("schedule_run_id", "employee_id", "date", "shift_template_id", name="uq_assignment_slot"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    schedule_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("schedule_runs.id"), nullable=False
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employees.id"), nullable=False
    )
    shift_template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("shift_templates.id"), nullable=False
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)

    status: Mapped[AssignmentStatus] = mapped_column(
        Enum(AssignmentStatus, name="assignment_status"), default=AssignmentStatus.PROPOSED
    )
    manually_edited: Mapped[bool] = mapped_column(Boolean, default=False)

    schedule_run: Mapped["ScheduleRun"] = relationship(back_populates="assignments")
    employee: Mapped["Employee"] = relationship(back_populates="shift_assignments")
    shift_template: Mapped["ShiftTemplate"] = relationship()
