"""Schemas package for request/response serialization."""
from app.schemas.bus import BusBase, BusCreate, BusResponse, BusUpdate
from app.schemas.user import (
    STUDENT_EMAIL_DOMAIN,
    UserBase,
    UserCreate,
    UserResponse,
    validate_student_domain,
)

__all__ = [
    "STUDENT_EMAIL_DOMAIN",
    "UserBase",
    "UserCreate",
    "UserResponse",
    "validate_student_domain",
    "BusBase",
    "BusCreate",
    "BusUpdate",
    "BusResponse",
]
