from typing import Optional
import enum
from datetime import datetime
from sqlalchemy import String, Float, Integer, DateTime, Enum, ForeignKey, UniqueConstraint, func, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base

class RouteDirection(str, enum.Enum):
    MORNING = "MORNING"
    EVENING = "EVENING"

class Route(Base):
    __tablename__ = "routes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    code: Mapped[str] = mapped_column(String(30), unique=True, index=True, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # List of {"lat": float, "lng": float}
    route_geometry: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)


    stops = relationship("RouteStop", back_populates="route", cascade="all, delete-orphan", order_by="RouteStop.sequence_order")

class BoardingPoint(Base):
    __tablename__ = "boarding_points"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    longitude: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    radius_meters: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # List of {"lat": float, "lng": float}
    route_geometry: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)


class RouteStop(Base):
    __tablename__ = "route_stops"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    route_id: Mapped[int] = mapped_column(ForeignKey("routes.id", ondelete="CASCADE"), nullable=False, index=True)
    boarding_point_id: Mapped[int] = mapped_column(ForeignKey("boarding_points.id", ondelete="CASCADE"), nullable=False, index=True)
    sequence_order: Mapped[int] = mapped_column(Integer, nullable=False)
    direction: Mapped[RouteDirection] = mapped_column(Enum(RouteDirection), nullable=False, default=RouteDirection.MORNING)

    route = relationship("Route", back_populates="stops")
    boarding_point = relationship("BoardingPoint")


    @property
    def name(self) -> str:
        return self.boarding_point.name if self.boarding_point else ""

    @property
    def latitude(self) -> float:
        return self.boarding_point.latitude if self.boarding_point else 0.0

    @property
    def longitude(self) -> float:
        return self.boarding_point.longitude if self.boarding_point else 0.0

    __table_args__ = (
        UniqueConstraint("route_id", "sequence_order", "direction", name="uq_route_sequence_direction"),
    )
