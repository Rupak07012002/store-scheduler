import enum
import uuid

from sqlalchemy import Boolean, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class ComplianceFlagType(str, enum.Enum):
    OVERTIME_RISK = "overtime_risk"
    INSUFFICIENT_REST = "insufficient_rest"
    UNDERSTAFFED_SLOT = "understaffed_slot"
    OVERSTAFFED_SLOT = "overstaffed_slot"
    TOO_MANY_CONSECUTIVE_DAYS = "too_many_consecutive_days"


class ComplianceFlagSeverity(str, enum.Enum):
    HARD = "hard"  # blocks publish until resolved
    SOFT = "soft"  # informational, doesn't block publish


class ComplianceFlag(Base, TimestampMixin):
    """
    Persisted (not computed on the fly) so the review UI and audit trail
    survive after a flag is resolved - an owner can later see "this run had
    an overtime flag that got fixed before publish", which matters for
    understanding why the schedule looks the way it does.
    """

    __tablename__ = "compliance_flags"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    schedule_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("schedule_runs.id"), nullable=False
    )
    employee_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employees.id"), nullable=True
    )

    flag_type: Mapped[ComplianceFlagType] = mapped_column(Enum(ComplianceFlagType, name="compliance_flag_type"))
    severity: Mapped[ComplianceFlagSeverity] = mapped_column(
        Enum(ComplianceFlagSeverity, name="compliance_flag_severity")
    )
    message: Mapped[str] = mapped_column(String(500), nullable=False)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)

    schedule_run: Mapped["ScheduleRun"] = relationship(back_populates="compliance_flags")
    employee: Mapped["Employee | None"] = relationship()
