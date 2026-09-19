from __future__ import annotations
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional
from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.trip import Trip
    from app.models.user import User


class LocationPing(Base):
    """SMARTBUS Location Ping entity representing a single GPS telemetry reading."""

    __tablename__ = "location_pings"
    __table_args__ = (
        CheckConstraint(
            "-90.0 <= latitude AND latitude <= 90.0",
            name="check_location_ping_latitude_range",
        ),
        CheckConstraint(
            "-180.0 <= longitude AND longitude <= 180.0",
            name="check_location_ping_longitude_range",
        ),
        CheckConstraint(
            "accuracy_meters IS NULL OR accuracy_meters >= 0",
            name="check_location_ping_accuracy_non_negative",
        ),
        CheckConstraint(
            "speed_mps IS NULL OR speed_mps >= 0",
            name="check_location_ping_speed_non_negative",
        ),
        CheckConstraint(
            "heading_degrees IS NULL OR (heading_degrees >= 0 AND heading_degrees < 360)",
            name="check_location_ping_heading_range",
        ),
        Index("ix_location_pings_trip_id_recorded_at", "trip_id", "recorded_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    trip_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("trips.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    driver_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    latitude: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    longitude: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    accuracy_meters: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    speed_mps: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    heading_degrees: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    trip: Mapped[Trip] = relationship("Trip")
    driver: Mapped[User] = relationship("User")

    def __repr__(self) -> str:
        return (
            f"<LocationPing id={self.id} trip_id={self.trip_id} "
            f"lat={self.latitude} lon={self.longitude} recorded_at={self.recorded_at}>"
        )
