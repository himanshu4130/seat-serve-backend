import uuid
from datetime import datetime, timezone
from enum import StrEnum

from sqlalchemy import DateTime, Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.core.permissions import Role


class StaffStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INVITED = "INVITED"
    DISABLED = "DISABLED"


class StaffBusinessRole(Base):
    """A user's role on one specific business. A user can hold different roles
    across different businesses — this is the actual multi-tenant RBAC fabric;
    SUPER_ADMIN is deliberately not modeled here (see User.is_platform_admin).

    Also doubles as the StaffMember record the frontend's staff management UI
    needs: `user_id` is nullable because an invite can be created for an email
    address before that person has ever signed in via Supabase. The first
    Supabase-authenticated request from a matching email links `user_id` and
    flips status INVITED -> ACTIVE (see `get_current_user`).
    """

    __tablename__ = "staff_business_roles"
    __table_args__ = (UniqueConstraint("email", "business_id", name="uq_email_business"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    business_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("businesses.id"), index=True)
    role: Mapped[Role] = mapped_column(Enum(Role, native_enum=False))
    status: Mapped[StaffStatus] = mapped_column(Enum(StaffStatus, native_enum=False), default=StaffStatus.ACTIVE)
    # Captured at invite time; kept in sync with the linked User's own name/phone
    # once accepted so this row stays the single read model for "who is staff here".
    name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str] = mapped_column(String(320), index=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    last_active_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    business = relationship("Business", back_populates="staff_roles")
