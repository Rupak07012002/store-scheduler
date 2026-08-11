import enum
import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class TimeOffStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"


class TimeOffRequest(Base, TimestampMixin):
    """
    Kept as its own table (not folded into Availability) because it has a
    distinct approval workflow and audit trail - blurring the two would make
    it unclear whether a "no" answer came from a recurring schedule or a
    one-off denied request when reviewing history.
    """

    __tablename__ = "time_off_requests"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employees.id"), nullable=False
    )

    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[TimeOffStatus] = mapped_column(
        Enum(TimeOffStatus, name="time_off_status"), default=TimeOffStatus.PENDING
    )

    resolved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    employee: Mapped["Employee"] = relationship(back_populates="time_off_requests", foreign_keys=[employee_id])
