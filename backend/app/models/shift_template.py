import uuid
from datetime import time

from sqlalchemy import Boolean, ForeignKey, Integer, String, Time
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class ShiftTemplate(Base, TimestampMixin):
    """
    Fixed, store-defined shift slots (e.g. "Morning" 08:00-13:00) rather than
    arbitrary continuous time blocks. This bounds the CP-SAT variable count
    to employees x days x templates and matches how an owner actually reasons
    about a schedule ("who's on Morning Tuesday") - see
    docs/forecasting-and-optimization.md for the full justification.

    day_of_week=NULL means the template applies every day; set it to
    constrain a template to specific days (e.g. a weekend-only extra shift).
    """

    __tablename__ = "shift_templates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("stores.id"), nullable=False)

    name: Mapped[str] = mapped_column(String(100), nullable=False)  # "Morning" / "Afternoon" / "Evening"
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    day_of_week: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 0=Monday .. 6=Sunday, NULL=all days
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    store: Mapped["Store"] = relationship(back_populates="shift_templates")
