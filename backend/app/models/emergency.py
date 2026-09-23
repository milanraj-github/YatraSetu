import enum
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, Float, DateTime, Enum, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.models.base import Base

class EmergencyType(str, enum.Enum):
    MANUAL_SOS = "MANUAL_SOS"
    AUTOMATIC_ACCIDENT = "AUTOMATIC_ACCIDENT"

class EmergencySeverity(str, enum.Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"

class EmergencyStatus(str, enum.Enum):
    POTENTIAL = "POTENTIAL"
    ACTIVE = "ACTIVE"
    ESCALATED = "ESCALATED"
    DRIVER_CONFIRMED_SAFE = "DRIVER_CONFIRMED_SAFE"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"

class Emergency(Base):
    __tablename__ = "emergencies"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    type: Mapped[EmergencyType] = mapped_column(Enum(EmergencyType), nullable=False)
    severity: Mapped[EmergencySeverity] = mapped_column(Enum(EmergencySeverity), nullable=False, default=EmergencySeverity.CRITICAL)
    status: Mapped[EmergencyStatus] = mapped_column(Enum(EmergencyStatus), nullable=False, default=EmergencyStatus.ACTIVE)
    
    bus_id: Mapped[Optional[int]] = mapped_column(ForeignKey("buses.id", ondelete="CASCADE"), nullable=True, index=True)
    driver_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    trip_id: Mapped[Optional[int]] = mapped_column(ForeignKey("tracking_sessions.id", ondelete="CASCADE"), nullable=True, index=True)
    route_id: Mapped[Optional[int]] = mapped_column(ForeignKey("routes.id", ondelete="CASCADE"), nullable=True, index=True)
    
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    accuracy: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    bus = relationship("Bus", foreign_keys=[bus_id])
    driver = relationship("User", foreign_keys=[driver_id])
    trip = relationship("TrackingSession", foreign_keys=[trip_id])
    route = relationship("Route", foreign_keys=[route_id])
    acknowledger = relationship("User", foreign_keys=[acknowledged_by])
    resolver = relationship("User", foreign_keys=[resolved_by])
