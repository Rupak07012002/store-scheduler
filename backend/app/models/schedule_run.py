import enum
import uuid
from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, Enum, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class ScheduleRunStatus(str, enum.Enum):
    DRAFT = "draft"
    UNDER_REVIEW = "under_review"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class SolverStatus(str, enum.Enum):
    OPTIMAL = "optimal"
    FEASIBLE = "feasible"  # solved within time limit but not proven optimal
    INFEASIBLE = "infeasible"  # coverage slack had to absorb unmet demand


class ScheduleRun(Base, TimestampMixin):
    """
    The aggregate root for one optimizer pass: one store, one week.
    forecast_snapshot stores the predicted-footfall/required-headcount
    numbers the optimizer solved against, as JSON, so the manager review UI
    can show "why" a draft looks the way it does without re-running the
    forecaster (and so that number stays fixed for audit purposes even if
    the live forecast changes later).
    """

    __tablename__ = "schedule_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("stores.id"), nullable=False)

    week_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[ScheduleRunStatus] = mapped_column(
        Enum(ScheduleRunStatus, name="schedule_run_status"), default=ScheduleRunStatus.DRAFT
    )
    solver_status: Mapped[SolverStatus | None] = mapped_column(
        Enum(SolverStatus, name="solver_status"), nullable=True
    )
    objective_value: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    forecast_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)

    generated_by: Mapped[str] = mapped_column(String(50), default="system")  # "system" or a User id string
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    store: Mapped["Store"] = relationship(back_populates="schedule_runs")
    assignments: Mapped[list["ShiftAssignment"]] = relationship(back_populates="schedule_run")
    compliance_flags: Mapped[list["ComplianceFlag"]] = relationship(back_populates="schedule_run")
