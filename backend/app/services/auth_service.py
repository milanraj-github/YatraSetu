import logging
from typing import Optional, Dict, Any
from app.core.config import settings
from app.core.security import normalize_email, is_valid_student_domain
from app.schemas.auth import UserResponse, UserRole

logger = logging.getLogger("smartbus.auth_service")

class DomainValidationError(Exception):
    def __init__(self, message: str, code: str = "STUDENT_EMAIL_DOMAIN_NOT_ALLOWED"):
        self.message = message
        self.code = code
        super().__init__(self.message)

def resolve_user_from_firebase_payload(
    firebase_payload: Dict[str, Any],
    full_name_override: Optional[str] = None
) -> UserResponse:
    """
    Resolves SMARTBUS User identity and role directly from verified Firebase token payload & claims.
    No SQL database required for Phase 1 Authentication.
    """
    firebase_uid = firebase_payload.get("uid")
    raw_email = firebase_payload.get("email", "")
    email = normalize_email(raw_email)
    is_email_verified = bool(firebase_payload.get("email_verified", False))

    if not firebase_uid or not email:
        raise ValueError("Firebase token payload must contain both 'uid' and 'email'.")

    predefined_admins = {
        normalize_email(settings.ADMIN1_EMAIL),
        normalize_email(settings.ADMIN2_EMAIL),
        normalize_email(settings.ADMIN3_EMAIL),
    }
    predefined_drivers = {
        normalize_email(settings.DRIVER1_EMAIL),
        normalize_email(settings.DRIVER2_EMAIL),
        normalize_email(settings.DRIVER3_EMAIL),
    }

    # 1. Check predefined admin accounts
    if email in predefined_admins:
        assigned_role = UserRole.ADMIN
    # 2. Check predefined driver accounts
    elif email in predefined_drivers:
        assigned_role = UserRole.DRIVER
    # 3. Check Firebase Custom Claims (if set via Firebase Admin SDK)
    elif firebase_payload.get("role") in [r.value for r in UserRole]:
        assigned_role = UserRole(firebase_payload.get("role"))
    # 4. Dynamic Student Domain Validation
    else:
        if not is_valid_student_domain(email):
            logger.warning(f"Student registration rejected for unauthorized domain: {email}")
            raise DomainValidationError(
                message=f"Students must use an @{settings.STUDENT_REQUIRED_DOMAIN} email address.",
                code="STUDENT_EMAIL_DOMAIN_NOT_ALLOWED"
            )
        assigned_role = UserRole.STUDENT

    name = full_name_override or firebase_payload.get("name") or email.split("@")[0].capitalize()

    return UserResponse(
        firebase_uid=firebase_uid,
        email=email,
        full_name=name,
        role=assigned_role,
        is_email_verified=is_email_verified
    )
