import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import require_role, require_roles
from app.db.database import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.driver import DriverAssignmentResponse
from app.services import driver_service

router = APIRouter(prefix="/drivers", tags=["Driver Assignment"])


@router.post(
    "/{driver_id}/assign-bus/{bus_id}",
    response_model=DriverAssignmentResponse,
    status_code=status.HTTP_200_OK,
    summary="Assign Bus to Driver",
    description="Assign a specific active bus to a driver (ADMIN only).",
)
async def assign_bus_endpoint(
    driver_id: uuid.UUID,
    bus_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> DriverAssignmentResponse:
    """Assign bus to driver."""
    return await driver_service.assign_bus_to_driver(db, driver_id, bus_id)


@router.delete(
    "/{driver_id}/unassign-bus",
    response_model=DriverAssignmentResponse,
    status_code=status.HTTP_200_OK,
    summary="Unassign Bus from Driver",
    description="Remove the bus assignment from a driver (ADMIN only).",
)
@router.delete(
    "/{driver_id}/assign-bus",
    response_model=DriverAssignmentResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
async def unassign_bus_endpoint(
    driver_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> DriverAssignmentResponse:
    """Unassign bus from driver."""
    return await driver_service.unassign_bus_from_driver(db, driver_id)


@router.get(
    "/{driver_id}/assignment",
    response_model=DriverAssignmentResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Driver Assignment",
    description="View current bus assignment details for a driver (ADMIN or DRIVER own).",
)
async def get_driver_assignment_endpoint(
    driver_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.DRIVER)),
) -> DriverAssignmentResponse:
    """Get driver assignment."""
    return await driver_service.get_driver_assignment(db, driver_id, current_user)
