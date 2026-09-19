from __future__ import annotations
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.boarding_point import BoardingPoint
    from app.models.route import Route


class RouteStop(Base):
    """SMARTBUS RouteStop association entity ordering BoardingPoints within a Route."""

    __tablename__ = "route_stops"
    __table_args__ = (
        UniqueConstraint(
            "route_id",
            "stop_order",
            name="uq_route_stops_route_stop_order",
        ),
        UniqueConstraint(
            "route_id",
            "boarding_point_id",
            name="uq_route_stops_route_boarding_point",
        ),
        CheckConstraint(
            "stop_order > 0",
            name="check_route_stop_order_positive",
        ),
        CheckConstraint(
            "scheduled_arrival_offset_minutes >= 0",
            name="check_scheduled_arrival_offset_non_negative",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    route_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("routes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    boarding_point_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("boarding_points.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    stop_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    scheduled_arrival_offset_minutes: Mapped[Optional[int]] = mapped_column(
        Integer,
        default=0,
        server_default="0",
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    route: Mapped[Route] = relationship(
        "Route",
        back_populates="route_stops",
    )
    boarding_point: Mapped[BoardingPoint] = relationship(
        "BoardingPoint",
        back_populates="route_stops",
    )

    def __repr__(self) -> str:
        return (
            f"<RouteStop id={self.id} route_id={self.route_id} "
            f"bp_id={self.boarding_point_id} order={self.stop_order}>"
        )
