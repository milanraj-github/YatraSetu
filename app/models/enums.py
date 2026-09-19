from enum import Enum


class UserRole(str, Enum):
    """Application user roles for SMARTBUS."""

    ADMIN = "ADMIN"
    DRIVER = "DRIVER"
    STUDENT = "STUDENT"
    PARENT = "PARENT"
