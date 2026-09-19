from enum import Enum


class UserRole(str, Enum):
    """Application user roles for SMARTBUS."""

    ADMIN = "ADMIN"
    DRIVER = "DRIVER"
    STUDENT = "STUDENT"
    PARENT = "PARENT"


class TripStatus(str, Enum):
    """Lifecycle status of a bus trip."""

    SCHEDULED = "SCHEDULED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class ParentLinkStatus(str, Enum):
    """Status of parent-child linking request."""

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"

