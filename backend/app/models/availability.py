import uuid
from datetime import date, time

from sqlalchemy import Date, ForeignKey, Integer, Time
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Availability(Base, TimestampMixin):
    """
    Recurring weekly availability by default (day_of_week set,
    effective_from/until bound an optional date range). A one-off exception
    (e.g. "unavailable this specific Tuesday") is modeled as a second,
    narrower-dated row rather than a separate exception table - the
    optimizer just needs "is employee E available for template T on date D",
    computed by checking all matching rows.
    """

    __tablename__ = "availabilities"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employees.id"), nullable=False
    )

    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)  # 0=Monday .. 6=Sunday
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    is_available: Mapped[bool] = mapped_column(default=True)  # False = explicit "unavailable" override

    effective_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    effective_until: Mapped[date | None] = mapped_column(Date, nullable=True)

    employee: Mapped["Employee"] = relationship(back_populates="availability_windows")
