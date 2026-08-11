import enum
import uuid

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class UserRole(str, enum.Enum):
    OWNER = "owner"  # sees all stores
    STORE_MANAGER = "store_manager"  # scoped to exactly one store
    EMPLOYEE = "employee"  # scoped to their own linked Employee record


class User(Base, TimestampMixin):
    """
    Auth identity, separate from Employee. An Employee doesn't need a login
    to exist in the schedule (e.g. before they've activated an account), and
    a StoreManager/Owner may not correspond to any Employee row at all.
    """

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, name="user_role"), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True)

    # One manager = one store (confirmed with owner: no multi-store managers in v1).
    # Null for OWNER (all-store scope) and optionally null for EMPLOYEE until linked.
    store_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stores.id"), nullable=True
    )
    linked_employee_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employees.id"), nullable=True
    )

    store: Mapped["Store | None"] = relationship(back_populates="managers", foreign_keys=[store_id])
    employee: Mapped["Employee | None"] = relationship(foreign_keys=[linked_employee_id])
