import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import require_role
from app.db.database import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.boarding_point import (
    BoardingPointCreate,
    BoardingPointResponse,
    BoardingPointUpdate,
)
from app.services import boarding_point_service

router = APIRouter(prefix="/boarding-points", tags=["Boarding Point Management"])


@router.post(
    "",
    response_model=BoardingPointResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Boarding Point",
    description="Register a new boarding point / bus stop (ADMIN only).",
)
async def create_boarding_point_endpoint(
    bp_in: BoardingPointCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> BoardingPointResponse:
    """Create a new boarding point."""
    bp = await boarding_point_service.create_boarding_point(db, bp_in)
    return BoardingPointResponse.model_validate(bp)


@router.get(
    "",
    response_model=List[BoardingPointResponse],
    status_code=status.HTTP_200_OK,
    summary="List Boarding Points",
    description="Retrieve a paginated list of boarding points (ADMIN only).",
)
async def list_boarding_points_endpoint(
    skip: int = Query(0, ge=0, description="Records to skip"),
    limit: int = Query(100, ge=1, le=500, description="Max records to return"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> List[BoardingPointResponse]:
    """List boarding points."""
    bps = await boarding_point_service.list_boarding_points(
        db, skip=skip, limit=limit, is_active=is_active
    )
    return [BoardingPointResponse.model_validate(b) for b in bps]


@router.get(
    "/{boarding_point_id}",
    response_model=BoardingPointResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Boarding Point by ID",
    description="Retrieve details of a specific boarding point (ADMIN only).",
)
async def get_boarding_point_endpoint(
    boarding_point_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> BoardingPointResponse:
    """Get boarding point by ID."""
    bp = await boarding_point_service.get_boarding_point_by_id(db, boarding_point_id)
    if not bp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Boarding point not found",
        )
    return BoardingPointResponse.model_validate(bp)


@router.patch(
    "/{boarding_point_id}",
    response_model=BoardingPointResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Boarding Point",
    description="Update boarding point details (ADMIN only).",
)
async def update_boarding_point_endpoint(
    boarding_point_id: uuid.UUID,
    bp_in: BoardingPointUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> BoardingPointResponse:
    """Update boarding point attributes."""
    bp = await boarding_point_service.get_boarding_point_by_id(db, boarding_point_id)
    if not bp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Boarding point not found",
        )
    updated_bp = await boarding_point_service.update_boarding_point(db, bp, bp_in)
    return BoardingPointResponse.model_validate(updated_bp)


@router.delete(
    "/{boarding_point_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deactivate Boarding Point",
    description="Safely deactivate a boarding point (sets is_active = false) (ADMIN only).",
)
async def deactivate_boarding_point_endpoint(
    boarding_point_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> Response:
    """Deactivate boarding point."""
    bp = await boarding_point_service.get_boarding_point_by_id(db, boarding_point_id)
    if not bp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Boarding point not found",
        )
    await boarding_point_service.deactivate_boarding_point(db, bp)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
