from __future__ import annotations
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional
from sqlalchemy import DateTime, Enum as SQLEnum, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import ParentLinkStatus

if TYPE_CHECKING:
    from app.models.user import User


class ParentLinkRequest(Base):
    """Request initiated by a parent to link with a student account."""

    __tablename__ = "parent_link_requests"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    parent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[ParentLinkStatus] = mapped_column(
        SQLEnum(ParentLinkStatus, name="parent_link_status_enum", native_enum=True),
        default=ParentLinkStatus.PENDING,
        server_default=ParentLinkStatus.PENDING.value,
        nullable=False,
        index=True,
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    parent: Mapped[User] = relationship("User", foreign_keys=[parent_id])
    student: Mapped[User] = relationship("User", foreign_keys=[student_id])

    def __repr__(self) -> str:
        return (
            f"<ParentLinkRequest id={self.id} parent_id={self.parent_id} "
            f"student_id={self.student_id} status={self.status}>"
        )


class ParentChildren(Base):
    """Approved parent-child relationship entity."""

    __tablename__ = "parent_children"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    parent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("parent_id", "student_id", name="uq_parent_children_parent_student"),
    )

    # Relationships
    parent: Mapped[User] = relationship("User", foreign_keys=[parent_id])
    student: Mapped[User] = relationship("User", foreign_keys=[student_id])

    def __repr__(self) -> str:
        return f"<ParentChildren id={self.id} parent_id={self.parent_id} student_id={self.student_id}>"
