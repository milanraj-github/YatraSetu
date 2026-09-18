import enum
from typing import Optional, Generic, TypeVar
from pydantic import BaseModel, ConfigDict, EmailStr

T = TypeVar("T")

class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    DRIVER = "DRIVER"
    STUDENT = "STUDENT"
    PARENT = "PARENT"

class UserResponse(BaseModel):
    firebase_uid: str
    email: EmailStr
    full_name: str
    role: UserRole
    is_email_verified: bool

    model_config = ConfigDict(from_attributes=True)

class SyncUserRequest(BaseModel):
    full_name: Optional[str] = None
    # Client cannot submit or request role changes. Role is strictly assigned by backend/Firebase claims!

class APIErrorDetail(BaseModel):
    code: str
    message: str

class APIResponse(BaseModel, Generic[T]):
    success: bool
    data: Optional[T] = None
    error: Optional[APIErrorDetail] = None
