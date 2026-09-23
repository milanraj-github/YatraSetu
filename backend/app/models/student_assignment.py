import enum
from datetime import datetime
from typing import Optional
from sqlalchemy import Integer, DateTime, Enum, ForeignKey, func, Index, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base

class StudentAssignmentStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"

class StudentBusAssignment(Base):
    __tablename__ = "student_bus_assignments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    bus_id: Mapped[int] = mapped_column(ForeignKey("buses.id", ondelete="CASCADE"), nullable=False, index=True)
    
    assigned_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    assigned_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[StudentAssignmentStatus] = mapped_column(Enum(StudentAssignmentStatus), nullable=False, default=StudentAssignmentStatus.ACTIVE)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    student = relationship("User", foreign_keys=[student_id])
    bus = relationship("Bus", foreign_keys=[bus_id])

    __table_args__ = (
        Index("ix_student_bus_active", "student_id", postgresql_where=text("status = 'ACTIVE'"), unique=True),
    )

    def __repr__(self) -> str:
        return f"<StudentBusAssignment student_id={self.student_id} bus_id={self.bus_id} status='{self.status}'>"
