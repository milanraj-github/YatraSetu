from __future__ import annotations
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from geoalchemy2 import Geography
from sqlalchemy import Boolean, CheckConstraint, DateTime, Float, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.route_stop import RouteStop



class BoardingPoint(Base):
    """SMARTBUS Boarding Point database entity."""

    __tablename__ = "boarding_points"
    __table_args__ = (
        CheckConstraint(
            "latitude >= -90.0 AND latitude <= 90.0",
            name="check_boarding_point_latitude_range",
        ),
        CheckConstraint(
            "longitude >= -180.0 AND longitude <= 180.0",
            name="check_boarding_point_longitude_range",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    latitude: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    longitude: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    address: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )

    @property
    def location(self) -> str:
        """PostGIS WKT Point representation with SRID 4326 (longitude X, latitude Y)."""
        return f"SRID=4326;POINT({self.longitude} {self.latitude})"


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

    # Relationship to route stops
    route_stops: Mapped[List[RouteStop]] = relationship(
        "RouteStop",
        back_populates="boarding_point",
    )

    def __repr__(self) -> str:
        return f"<BoardingPoint id={self.id} name={self.name} lat={self.latitude} lng={self.longitude}>"
