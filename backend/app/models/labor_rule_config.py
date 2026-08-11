import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class LaborRuleConfig(Base, TimestampMixin):
    """
    Configurable labor rules (never hardcoded - owner operates in a single
    US region today but rules like overtime threshold can change law-side or
    by owner policy). store_id=NULL means a global default; a store-specific
    row overrides it. `effective_from` makes rule changes versioned so a
    historical ScheduleRun stays auditable against the rules that were
    active at the time it was generated, even if rules change later.
    """

    __tablename__ = "labor_rule_configs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stores.id"), nullable=True
    )

    max_hours_before_overtime: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    overtime_multiplier: Mapped[float] = mapped_column(Numeric(4, 2), nullable=False)
    min_rest_hours_between_shifts: Mapped[float] = mapped_column(Numeric(4, 2), nullable=False)
    required_break_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    max_consecutive_days: Mapped[int] = mapped_column(Integer, nullable=False)

    effective_from: Mapped[date] = mapped_column(Date, nullable=False)

    store: Mapped["Store | None"] = relationship()
