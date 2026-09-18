from app.core.config import settings

def normalize_email(email: str) -> str:
    """Normalizes email to lowercase and strips surrounding whitespace."""
    if not email:
        return ""
    return email.strip().lower()

def is_valid_student_domain(email: str) -> bool:
    """
    Enforces student email domain restriction.
    Email MUST end with @sode-edu.in (or domain specified in settings).
    Strict exact domain check, avoiding unsafe substring matches.
    """
    normalized = normalize_email(email)
    required_domain = settings.STUDENT_REQUIRED_DOMAIN.strip().lower()
    domain_suffix = f"@{required_domain}"
    
    return normalized.endswith(domain_suffix)
