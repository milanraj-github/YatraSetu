import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import require_role
from app.db.database import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.bus import BusCreate, BusResponse, BusUpdate
from app.services import bus_service

router = APIRouter(prefix="/buses", tags=["Bus Management"])


@router.post(
    "",
    response_model=BusResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Bus",
    description="Register a new bus in the system (ADMIN only).",
)
async def create_bus_endpoint(
    bus_in: BusCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> BusResponse:
    """Create a new bus record."""
    bus = await bus_service.create_bus(db, bus_in)
    return BusResponse.model_validate(bus)


@router.get(
    "",
    response_model=List[BusResponse],
    status_code=status.HTTP_200_OK,
    summary="List Buses",
    description="Retrieve a paginated list of buses (ADMIN only).",
)
async def list_buses_endpoint(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=500, description="Max number of records to return"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> List[BusResponse]:
    """List buses with pagination."""
    buses = await bus_service.list_buses(db, skip=skip, limit=limit, is_active=is_active)
    return [BusResponse.model_validate(b) for b in buses]


@router.get(
    "/{bus_id}",
    response_model=BusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Bus by ID",
    description="Fetch details of a specific bus (ADMIN only).",
)
async def get_bus_endpoint(
    bus_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> BusResponse:
    """Get bus details by ID."""
    bus = await bus_service.get_bus_by_id(db, bus_id)
    if not bus:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bus not found",
        )
    return BusResponse.model_validate(bus)


@router.patch(
    "/{bus_id}",
    response_model=BusResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Bus",
    description="Update bus attributes (ADMIN only).",
)
async def update_bus_endpoint(
    bus_id: uuid.UUID,
    bus_in: BusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> BusResponse:
    """Update bus attributes."""
    bus = await bus_service.get_bus_by_id(db, bus_id)
    if not bus:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bus not found",
        )
    updated_bus = await bus_service.update_bus(db, bus, bus_in)
    return BusResponse.model_validate(updated_bus)


@router.delete(
    "/{bus_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deactivate Bus",
    description="Safely deactivate a bus (sets is_active = false) (ADMIN only).",
)
async def deactivate_bus_endpoint(
    bus_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> Response:
    """Deactivate a bus."""
    bus = await bus_service.get_bus_by_id(db, bus_id)
    if not bus:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bus not found",
        )
    await bus_service.deactivate_bus(db, bus)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
