import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class HolidayCalendarEntry(Base, TimestampMixin):
    """
    Owner-tunable multiplier applied to the seasonal-baseline forecast on
    known high/low-traffic dates (e.g. 1.5x on Black Friday). store_id=NULL
    applies to all stores. This is deliberately a manual table, not a
    fetched holiday API, since retail traffic multipliers are business-
    specific judgment calls, not a fact you look up.
    """

    __tablename__ = "holiday_calendar_entries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stores.id"), nullable=True
    )

    date: Mapped[date] = mapped_column(Date, nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    expected_footfall_multiplier: Mapped[float] = mapped_column(Numeric(4, 2), nullable=False, default=1.0)

    store: Mapped["Store | None"] = relationship()
