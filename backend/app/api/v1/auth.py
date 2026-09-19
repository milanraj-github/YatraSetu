from typing import Any
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_firebase_user, get_current_user
from app.db.database import get_db
from app.models.user import User
from app.schemas.parent_child import ParentLinkRequestResponse, ParentRegisterRequest
from app.schemas.user import UserResponse
from app.services import parent_child_service

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get Current User Profile",
    description="Fetch the profile of the currently authenticated Firebase user.",
)
async def get_me(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Return profile of the authenticated user."""
    return UserResponse.model_validate(current_user)


@router.post(
    "/register-parent",
    response_model=ParentLinkRequestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register Parent and Initiate Student Link",
    description="Register a parent user profile and send a pending linking request to the specified student email.",
)
async def register_parent_endpoint(
    parent_in: ParentRegisterRequest,
    db: AsyncSession = Depends(get_db),
    firebase_identity: dict[str, Any] = Depends(get_current_firebase_user),
) -> ParentLinkRequestResponse:
    """Register parent profile and create pending link request."""
    return await parent_child_service.register_parent_and_create_link_request(
        db=db,
        firebase_identity=firebase_identity,
        parent_in=parent_in,
    )

