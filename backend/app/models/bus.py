import enum
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, Enum, func
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base

class BusStatus(str, enum.Enum):
    IDLE = "IDLE"
    IN_TRIP = "IN_TRIP"
    MAINTENANCE = "MAINTENANCE"
    INACTIVE = "INACTIVE"

class Bus(Base):
    __tablename__ = "buses"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    bus_number: Mapped[str] = mapped_column(String(30), unique=True, index=True, nullable=False)
    registration_number: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    status: Mapped[BusStatus] = mapped_column(Enum(BusStatus), nullable=False, default=BusStatus.IDLE)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self) -> str:
        return f"<Bus id={self.id} bus_number='{self.bus_number}' status='{self.status}'>"
