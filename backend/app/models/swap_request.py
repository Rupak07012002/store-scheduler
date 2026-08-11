import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class SwapStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    CANCELLED = "cancelled"


class SwapRequest(Base, TimestampMixin):
    """
    A trade between two PUBLISHED ShiftAssignments (swaps against an
    unpublished draft don't make sense - the employee has nothing to trade
    yet). target_assignment_id is nullable to support an "open swap" where
    any willing employee can claim the source shift; v1 ships the direct
    employee-to-employee case only (see plan's noted assumption: no
    skill/role differentiation on who can swap with whom in v1).
    """

    __tablename__ = "swap_requests"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_assignment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("shift_assignments.id"), nullable=False
    )
    target_employee_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employees.id"), nullable=True
    )
    target_assignment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("shift_assignments.id"), nullable=True
    )

    status: Mapped[SwapStatus] = mapped_column(Enum(SwapStatus, name="swap_status"), default=SwapStatus.PENDING)
    resolved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    source_assignment: Mapped["ShiftAssignment"] = relationship(foreign_keys=[source_assignment_id])
    target_assignment: Mapped["ShiftAssignment | None"] = relationship(foreign_keys=[target_assignment_id])
    target_employee: Mapped["Employee | None"] = relationship(foreign_keys=[target_employee_id])
