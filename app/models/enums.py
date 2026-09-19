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


class DevicePlatform(str, Enum):
    """Supported client platforms for device tokens."""

    ANDROID = "ANDROID"
    IOS = "IOS"
    WEB = "WEB"


class NotificationType(str, Enum):
    """Types of transit and safety notifications."""

    BUS_NEARBY = "BUS_NEARBY"
    BUS_ARRIVED = "BUS_ARRIVED"
    DELAY = "DELAY"
    EMERGENCY = "EMERGENCY"
    ACCIDENT = "ACCIDENT"
    SOS = "SOS"


class NotificationChannel(str, Enum):
    """Channels used for notification dispatch."""

    PUSH = "PUSH"
    EMAIL = "EMAIL"
    BOTH = "BOTH"


class NotificationStatus(str, Enum):
    """Status lifecycle of a notification record."""

    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"

