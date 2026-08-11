import enum
import uuid
from datetime import date

from sqlalchemy import Date, Enum, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class FootfallSource(str, enum.Enum):
    SYNTHETIC = "synthetic"
    SHOPIFY = "shopify"
    CAMERA = "camera"  # reserved for v2 computer-vision pipeline; unused in v1


class FootfallRecord(Base, TimestampMixin):
    """
    One row = observed transaction-count (proxy for footfall) for one store,
    one date, one hour block. `source` distinguishes real data from the v1
    synthetic seed so that a later live-Shopify cutover can run alongside
    (or replace) historical synthetic rows without an ambiguous table.
    """

    __tablename__ = "footfall_records"
    __table_args__ = (UniqueConstraint("store_id", "date", "hour_block", "source", name="uq_footfall_slot"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("stores.id"), nullable=False)

    date: Mapped[date] = mapped_column(Date, nullable=False)
    hour_block: Mapped[int] = mapped_column(Integer, nullable=False)  # 0-23
    transaction_count: Mapped[int] = mapped_column(Integer, nullable=False)
    source: Mapped[FootfallSource] = mapped_column(
        Enum(FootfallSource, name="footfall_source"), default=FootfallSource.SYNTHETIC
    )

    store: Mapped["Store"] = relationship(back_populates="footfall_records")
