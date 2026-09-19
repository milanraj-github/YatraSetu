from typing import Any, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.firebase import verify_firebase_token
from app.db.database import get_db
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
    """Resolve the authenticated Firebase identity to a SMARTBUS User entity."""
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
