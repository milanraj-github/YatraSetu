import uuid
from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import require_role
from app.db.database import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.gps import LiveLocationResponse
from app.schemas.parent_child import ParentChildResponse
from app.services import parent_child_service

router = APIRouter(prefix="/parent", tags=["Parent Portal"])


@router.get(
    "/children",
    response_model=List[ParentChildResponse],
    status_code=status.HTTP_200_OK,
    summary="List Parent's Approved Children",
    description="Retrieve all approved linked children for the authenticated parent.",
)
async def list_parent_children_endpoint(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.PARENT)),
) -> List[ParentChildResponse]:
    """Retrieve approved linked children for parent."""
    return await parent_child_service.get_parent_children(db, current_user)


@router.get(
    "/children/{student_id}/live",
    response_model=LiveLocationResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Approved Child's Live Bus Location",
    description="Retrieve the current live GPS location for an approved child's active in-progress bus trip.",
)
async def get_child_live_location_endpoint(
    student_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.PARENT)),
) -> LiveLocationResponse:
    """Retrieve live location for an approved child's active trip."""
    return await parent_child_service.get_child_live_location(db, student_id, current_user)
