import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user, require_role, require_roles
from app.db.database import get_db
from app.models.enums import TripStatus, UserRole
from app.models.user import User
from app.schemas.eta import TripETAResponse
from app.schemas.trip import TripCreate, TripResponse
from app.services import eta_service, trip_service

router = APIRouter(prefix="/trips", tags=["Trip Management"])


@router.post(
    "",
    response_model=TripResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Trip",
    description="Schedule a new trip on a route with an assigned bus and driver (ADMIN only).",
)
async def create_trip_endpoint(
    trip_in: TripCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> TripResponse:
    """Create a new scheduled trip."""
    trip = await trip_service.create_trip(db, trip_in)
    return TripResponse.model_validate(trip)


@router.get(
    "",
    response_model=List[TripResponse],
    status_code=status.HTTP_200_OK,
    summary="List Trips",
    description="List trips (ADMIN sees all, DRIVER sees own assigned trips).",
)
async def list_trips_endpoint(
    skip: int = Query(0, ge=0, description="Records to skip"),
    limit: int = Query(100, ge=1, le=500, description="Max records to return"),
    status_filter: Optional[TripStatus] = Query(None, alias="status", description="Filter by trip status"),
    route_id: Optional[uuid.UUID] = Query(None, description="Filter by route ID"),
    bus_id: Optional[uuid.UUID] = Query(None, description="Filter by bus ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.DRIVER)),
) -> List[TripResponse]:
    """List trips."""
    trips = await trip_service.list_trips(
        db,
        current_user=current_user,
        skip=skip,
        limit=limit,
        status_filter=status_filter,
        route_id=route_id,
        bus_id=bus_id,
    )
    return [TripResponse.model_validate(t) for t in trips]


@router.get(
    "/{trip_id}",
    response_model=TripResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Trip by ID",
    description="Retrieve details of a specific trip (ADMIN or assigned DRIVER).",
)
async def get_trip_endpoint(
    trip_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.DRIVER)),
) -> TripResponse:
    """Get trip details."""
    trip = await trip_service.get_trip_by_id(db, trip_id)
    if not trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trip not found",
        )

    # Verify visibility if DRIVER
    if current_user.role == UserRole.DRIVER and trip.driver_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: cannot view another driver's trip",
        )

    return TripResponse.model_validate(trip)


@router.get(
    "/{trip_id}/eta",
    response_model=TripETAResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Trip ETA",
    description="Calculate and retrieve baseline deterministic arrival times for all route stops on an active trip.",
)
async def get_trip_eta_endpoint(
    trip_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TripETAResponse:
    """Get estimated arrival times for route stops of an active trip."""
    return await eta_service.get_trip_eta(db, trip_id, current_user)


@router.post(
    "/{trip_id}/start",
    response_model=TripResponse,
    status_code=status.HTTP_200_OK,
    summary="Start Trip",
    description="Start a scheduled trip (ADMIN or assigned DRIVER operating designated bus).",
)
async def start_trip_endpoint(
    trip_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.DRIVER)),
) -> TripResponse:
    """Start trip."""
    trip = await trip_service.get_trip_by_id(db, trip_id)
    if not trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trip not found",
        )
    started_trip = await trip_service.start_trip(db, trip, current_user)
    return TripResponse.model_validate(started_trip)


@router.post(
    "/{trip_id}/end",
    response_model=TripResponse,
    status_code=status.HTTP_200_OK,
    summary="End Trip",
    description="Complete an in-progress trip (ADMIN or assigned DRIVER operating designated bus).",
)
async def end_trip_endpoint(
    trip_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.DRIVER)),
) -> TripResponse:
    """End trip."""
    trip = await trip_service.get_trip_by_id(db, trip_id)
    if not trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trip not found",
        )
    ended_trip = await trip_service.end_trip(db, trip, current_user)
    return TripResponse.model_validate(ended_trip)


@router.post(
    "/{trip_id}/cancel",
    response_model=TripResponse,
    status_code=status.HTTP_200_OK,
    summary="Cancel Trip",
    description="Cancel a scheduled trip (ADMIN only).",
)
async def cancel_trip_endpoint(
    trip_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> TripResponse:
    """Cancel trip."""
    trip = await trip_service.get_trip_by_id(db, trip_id)
    if not trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trip not found",
        )
    cancelled_trip = await trip_service.cancel_trip(db, trip, current_user)
    return TripResponse.model_validate(cancelled_trip)
