import uuid
from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import require_role
from app.db.database import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.parent_child import ParentLinkRequestResponse
from app.services import parent_child_service

router = APIRouter(prefix="/parent-links", tags=["Parent-Child Linking"])


@router.get(
    "",
    response_model=List[ParentLinkRequestResponse],
    status_code=status.HTTP_200_OK,
    summary="List Student's Parent Link Requests",
    description="Retrieve all parent link requests received by the authenticated student.",
)
async def list_student_parent_requests_endpoint(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.STUDENT)),
) -> List[ParentLinkRequestResponse]:
    """Retrieve parent link requests for the authenticated student."""
    return await parent_child_service.get_student_parent_requests(db, current_user)


@router.post(
    "/{request_id}/approve",
    response_model=ParentLinkRequestResponse,
    status_code=status.HTTP_200_OK,
    summary="Approve Parent Link Request",
    description="Approve a pending parent-child linking request (Referenced STUDENT only).",
)
async def approve_parent_link_request_endpoint(
    request_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.STUDENT)),
) -> ParentLinkRequestResponse:
    """Approve parent linking request."""
    return await parent_child_service.approve_parent_link_request(db, request_id, current_user)


@router.post(
    "/{request_id}/reject",
    response_model=ParentLinkRequestResponse,
    status_code=status.HTTP_200_OK,
    summary="Reject Parent Link Request",
    description="Reject a pending parent-child linking request (Referenced STUDENT only).",
)
async def reject_parent_link_request_endpoint(
    request_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.STUDENT)),
) -> ParentLinkRequestResponse:
    """Reject parent linking request."""
    return await parent_child_service.reject_parent_link_request(db, request_id, current_user)
