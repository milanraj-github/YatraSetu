import enum
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, Enum, func
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base

class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    DRIVER = "DRIVER"
    STUDENT = "STUDENT"
    PARENT = "PARENT"

class UserStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    firebase_uid: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(128), nullable=False)
    phone_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False, default=UserRole.STUDENT)
    status: Mapped[UserStatus] = mapped_column(Enum(UserStatus), nullable=False, default=UserStatus.ACTIVE)
    is_email_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self) -> str:
        return f"<User id={self.id} email='{self.email}' role='{self.role}'>"
