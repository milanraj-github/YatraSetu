import enum
from datetime import datetime
from sqlalchemy import ForeignKey, String, DateTime, Enum, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base

class RelationshipType(str, enum.Enum):
    FATHER = "FATHER"
    MOTHER = "MOTHER"
    GUARDIAN = "GUARDIAN"
    OTHER = "OTHER"

class RelationshipStatus(str, enum.Enum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    REJECTED = "REJECTED"
    REVOKED = "REVOKED"

class ParentStudentRelationship(Base):
    __tablename__ = "parent_student_relationships"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    parent_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    relationship_type: Mapped[RelationshipType] = mapped_column(Enum(RelationshipType, name="relationshiptype", create_type=True), nullable=False)
    status: Mapped[RelationshipStatus] = mapped_column(Enum(RelationshipStatus, name="relationshipstatus", create_type=True), nullable=False, default=RelationshipStatus.PENDING)
    
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    parent = relationship("User", foreign_keys=[parent_id], backref="student_relationships")
    student = relationship("User", foreign_keys=[student_id], backref="parent_relationships")

    def __repr__(self) -> str:
        return f"<ParentStudentRelationship id={self.id} parent={self.parent_id} student={self.student_id} status={self.status}>"
