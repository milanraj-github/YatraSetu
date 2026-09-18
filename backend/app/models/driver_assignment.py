import enum
from datetime import datetime
from typing import Optional
from sqlalchemy import Integer, DateTime, Enum, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base

class AssignmentStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"

class DriverBusAssignment(Base):
    __tablename__ = "driver_bus_assignments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    driver_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    bus_id: Mapped[int] = mapped_column(ForeignKey("buses.id", ondelete="CASCADE"), nullable=False, index=True)
    
    assigned_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    assigned_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[AssignmentStatus] = mapped_column(Enum(AssignmentStatus), nullable=False, default=AssignmentStatus.ACTIVE)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    driver = relationship("User", foreign_keys=[driver_id])
    bus = relationship("Bus", foreign_keys=[bus_id])

    def __repr__(self) -> str:
        return f"<DriverBusAssignment driver_id={self.driver_id} bus_id={self.bus_id} status='{self.status}'>"
