from typing import Any, Optional
from fastapi import Depends, HTTPException, WebSocket, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.firebase import verify_firebase_token
from app.db.database import get_db
from app.models.enums import UserRole
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_firebase_user(
    auth_header: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> dict[str, Any]:
    """Extract and verify Firebase ID token from the Authorization header."""
    if not auth_header or not auth_header.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header with Bearer token is required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = auth_header.credentials
    decoded = verify_firebase_token(token)
    uid = decoded.get("uid")
    if not uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload: missing UID",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {
        "uid": uid,
        "email": decoded.get("email"),
        "decoded": decoded,
    }


async def get_current_user(
    firebase_identity: dict[str, Any] = Depends(get_current_firebase_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Resolve the authenticated Firebase identity to a SMARTBUS User entity in PostgreSQL."""
    firebase_uid = firebase_identity["uid"]

    result = await db.execute(
        select(User).where(User.firebase_uid == firebase_uid)
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in system",
        )

    return user


async def get_websocket_user(
    websocket: WebSocket,
    db: AsyncSession,
) -> User:
    """Authenticate and resolve the current user for a WebSocket connection."""
    auth_header = websocket.headers.get("authorization") or websocket.headers.get("Authorization")
    token = None
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
    elif "token" in websocket.query_params:
        token = websocket.query_params["token"]

    if not token:
        raise HTTPException(
            status_code=status.WS_1008_POLICY_VIOLATION,
            detail="Missing authentication token",
        )

    try:
        decoded = verify_firebase_token(token)
        uid = decoded.get("uid")
        if not uid:
            raise HTTPException(
                status_code=status.WS_1008_POLICY_VIOLATION,
                detail="Invalid token payload",
            )
    except Exception:
        raise HTTPException(
            status_code=status.WS_1008_POLICY_VIOLATION,
            detail="Token verification failed",
        )

    result = await db.execute(select(User).where(User.firebase_uid == uid))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.WS_1008_POLICY_VIOLATION,
            detail="User not found in system",
        )

    return user


class RoleChecker:
    """FastAPI authorization dependency verifying that the authenticated user possesses an allowed role."""

    def __init__(self, *allowed_roles: UserRole):
        self.allowed_roles = allowed_roles

    async def __call__(self, current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access forbidden: requires one of {[r.value for r in self.allowed_roles]} permissions",
            )
        return current_user


def require_role(role: UserRole) -> RoleChecker:
    """Helper returning a dependency that enforces a single required role."""
    return RoleChecker(role)


def require_roles(*roles: UserRole) -> RoleChecker:
    """Helper returning a dependency that permits any of multiple specified roles."""
    return RoleChecker(*roles)
