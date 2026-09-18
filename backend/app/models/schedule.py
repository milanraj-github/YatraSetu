import enum
from datetime import datetime, time, date
from typing import Optional
from sqlalchemy import String, Time, Date, Boolean, Integer, DateTime, Enum, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base
from app.models.route import RouteDirection

class SessionStatus(str, enum.Enum):
    SCHEDULED = "SCHEDULED"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"

class TripSchedule(Base):
    __tablename__ = "trip_schedules"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    bus_id: Mapped[int] = mapped_column(ForeignKey("buses.id", ondelete="CASCADE"), nullable=False, index=True)
    route_id: Mapped[int] = mapped_column(ForeignKey("routes.id", ondelete="CASCADE"), nullable=False, index=True)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    direction: Mapped[RouteDirection] = mapped_column(Enum(RouteDirection), nullable=False, default=RouteDirection.MORNING)
    days_of_week: Mapped[str] = mapped_column(String(100), nullable=False, default="MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY,SATURDAY")
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    bus = relationship("Bus", foreign_keys=[bus_id])
    route = relationship("Route", foreign_keys=[route_id])

class TrackingSession(Base):
    __tablename__ = "tracking_sessions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    bus_id: Mapped[int] = mapped_column(ForeignKey("buses.id", ondelete="CASCADE"), nullable=False, index=True)
    route_id: Mapped[int] = mapped_column(ForeignKey("routes.id", ondelete="CASCADE"), nullable=False, index=True)
    schedule_id: Mapped[int] = mapped_column(ForeignKey("trip_schedules.id", ondelete="CASCADE"), nullable=False, index=True)
    driver_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    session_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    direction: Mapped[RouteDirection] = mapped_column(Enum(RouteDirection), nullable=False, default=RouteDirection.MORNING)
    status: Mapped[SessionStatus] = mapped_column(Enum(SessionStatus), nullable=False, default=SessionStatus.SCHEDULED)
    
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    bus = relationship("Bus", foreign_keys=[bus_id])
    route = relationship("Route", foreign_keys=[route_id])
    schedule = relationship("TripSchedule", foreign_keys=[schedule_id])
    driver = relationship("User", foreign_keys=[driver_id])

    __table_args__ = (
        UniqueConstraint("bus_id", "session_date", "schedule_id", name="uq_bus_daily_schedule_session"),
    )
