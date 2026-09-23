import enum
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, DateTime, Enum, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.models.base import Base

class AlertType(str, enum.Enum):
    GPS_STALE = "GPS_STALE"
    GPS_DISCONNECTED = "GPS_DISCONNECTED"
    ROUTE_DEVIATION = "ROUTE_DEVIATION"
    TRIP_ISSUE = "TRIP_ISSUE"
    BUS_ISSUE = "BUS_ISSUE"
    SCHEDULE_ISSUE = "SCHEDULE_ISSUE"
    SYSTEM = "SYSTEM"

class AlertSeverity(str, enum.Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"

class AlertStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    RESOLVED = "RESOLVED"

class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    type: Mapped[AlertType] = mapped_column(Enum(AlertType), nullable=False)
    severity: Mapped[AlertSeverity] = mapped_column(Enum(AlertSeverity), nullable=False)
    status: Mapped[AlertStatus] = mapped_column(Enum(AlertStatus), nullable=False, default=AlertStatus.ACTIVE)
    
    bus_id: Mapped[Optional[int]] = mapped_column(ForeignKey("buses.id", ondelete="CASCADE"), nullable=True, index=True)
    driver_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    route_id: Mapped[Optional[int]] = mapped_column(ForeignKey("routes.id", ondelete="CASCADE"), nullable=True, index=True)
    trip_id: Mapped[Optional[int]] = mapped_column(ForeignKey("tracking_sessions.id", ondelete="CASCADE"), nullable=True, index=True)
    
    description: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="SYSTEM")
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    bus = relationship("Bus", foreign_keys=[bus_id])
    driver = relationship("User", foreign_keys=[driver_id])
    route = relationship("Route", foreign_keys=[route_id])
    trip = relationship("TrackingSession", foreign_keys=[trip_id])
    resolver = relationship("User", foreign_keys=[resolved_by])
