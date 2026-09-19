from __future__ import annotations
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional
from sqlalchemy import DateTime, Enum as SQLEnum, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import TripStatus

if TYPE_CHECKING:
    from app.models.bus import Bus
    from app.models.route import Route
    from app.models.user import User


class Trip(Base):
    """SMARTBUS Trip entity representing a scheduled or active route run."""

    __tablename__ = "trips"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    route_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("routes.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    bus_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("buses.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    driver_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    status: Mapped[TripStatus] = mapped_column(
        SQLEnum(TripStatus, name="trip_status_enum", native_enum=True),
        default=TripStatus.SCHEDULED,
        server_default=TripStatus.SCHEDULED.value,
        nullable=False,
        index=True,
    )
    scheduled_start_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    actual_start_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    actual_end_at: Mapped[Optional[datetime]] = mapped_column(
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
    route: Mapped[Route] = relationship("Route")
    bus: Mapped[Bus] = relationship("Bus")
    driver: Mapped[User] = relationship("User")

    def __repr__(self) -> str:
        return (
            f"<Trip id={self.id} route_id={self.route_id} "
            f"bus_id={self.bus_id} driver_id={self.driver_id} status={self.status}>"
        )
