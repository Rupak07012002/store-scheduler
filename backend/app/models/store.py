import uuid

from sqlalchemy import Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Store(Base, TimestampMixin):
    """
    footfall_to_staff_ratio / min_staff_floor / avg_transaction_value are
    per-store overrides of the app-wide defaults in app.config.Settings.
    NULL means "use the global default" so an owner doesn't have to fill in
    every field for every store on day one.
    """

    __tablename__ = "stores"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)

    footfall_to_staff_ratio: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    min_staff_floor: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Owner-supplied ESTIMATE of average transaction value, used only to
    # render a revenue estimate on the compliance dashboard
    # (avg_transaction_value * predicted_footfall). Not real Shopify revenue.
    avg_transaction_value: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)

    is_active: Mapped[bool] = mapped_column(default=True)

    employees: Mapped[list["Employee"]] = relationship(back_populates="store")
    managers: Mapped[list["User"]] = relationship(back_populates="store", foreign_keys="User.store_id")
    shift_templates: Mapped[list["ShiftTemplate"]] = relationship(back_populates="store")
    footfall_records: Mapped[list["FootfallRecord"]] = relationship(back_populates="store")
    schedule_runs: Mapped[list["ScheduleRun"]] = relationship(back_populates="store")
