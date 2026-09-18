from typing import List, Callable, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.firebase import verify_firebase_id_token
from app.schemas.auth import UserResponse, UserRole
from app.services.auth_service import resolve_user_from_firebase_payload, DomainValidationError

security_scheme = HTTPBearer(auto_error=False)

async def get_current_user(
    auth_credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme)
) -> UserResponse:
    """
    FastAPI dependency to extract Bearer token, verify Firebase ID token,
    and resolve user identity & role without database queries.
    """
    if not auth_credentials or not auth_credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "MISSING_AUTHENTICATION_TOKEN",
                "message": "Authorization Bearer token is required."
            },
            headers={"WWW-Authenticate": "Bearer"}
        )

    token = auth_credentials.credentials
    decoded_token = verify_firebase_id_token(token)

    if not decoded_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "INVALID_OR_EXPIRED_TOKEN",
                "message": "Firebase ID Token verification failed or token expired."
            },
            headers={"WWW-Authenticate": "Bearer"}
        )

    try:
        user = resolve_user_from_firebase_payload(decoded_token)
    except DomainValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": e.code, "message": e.message}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "INTERNAL_SERVER_ERROR", "message": str(e)}
        )

    return user

def require_roles(allowed_roles: List[UserRole]) -> Callable:
    """
    Dependency guard enforcing role-based authorization.
    """
    async def role_checker(current_user: UserResponse = Depends(get_current_user)) -> UserResponse:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "INSUFFICIENT_PERMISSIONS",
                    "message": f"User role '{current_user.role.value}' is not authorized to access this resource."
                }
            )
        return current_user

    return role_checker

require_admin = require_roles([UserRole.ADMIN])
require_driver = require_roles([UserRole.DRIVER])
require_student = require_roles([UserRole.STUDENT])
