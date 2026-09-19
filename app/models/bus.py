from __future__ import annotations
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List
from sqlalchemy import Boolean, CheckConstraint, DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class Bus(Base):
    """SMARTBUS Bus database entity."""

    __tablename__ = "buses"
    __table_args__ = (
        CheckConstraint("capacity > 0", name="check_bus_capacity_positive"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    bus_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
    )
    registration_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
    )
    capacity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
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

    # Relationship to assigned drivers (User entities)
    drivers: Mapped[List[User]] = relationship(
        "User",
        back_populates="assigned_bus",
        foreign_keys="[User.assigned_bus_id]",
    )

    def __repr__(self) -> str:
        return (
            f"<Bus id={self.id} number={self.bus_number} "
            f"reg={self.registration_number} active={self.is_active}>"
        )
