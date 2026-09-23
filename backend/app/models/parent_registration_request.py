import enum
from datetime import datetime
from sqlalchemy import String, DateTime, Enum, func
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base
from app.models.parent_student_relationship import RelationshipType

class ParentRequestStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    COMPLETED = "COMPLETED"

class ParentRegistrationRequest(Base):
    __tablename__ = "parent_registration_requests"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    student_email: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    relationship_type: Mapped[RelationshipType] = mapped_column(Enum(RelationshipType, name="relationshiptype", create_type=False), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    status: Mapped[ParentRequestStatus] = mapped_column(Enum(ParentRequestStatus, name="parentrequeststatus", create_type=True), nullable=False, default=ParentRequestStatus.PENDING)
    
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self) -> str:
        return f"<ParentRegistrationRequest id={self.id} student_email='{self.student_email}' status={self.status}>"
