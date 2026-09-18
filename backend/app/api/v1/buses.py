"""
Admin: Bus management endpoints.

GET    /api/v1/buses           — List all buses (Admin, Driver, Student)
POST   /api/v1/buses           — Create a bus (Admin only)
GET    /api/v1/buses/{bus_id}  — Get a single bus (Admin, Driver, Student)
PATCH  /api/v1/buses/{bus_id}  — Update a bus (Admin only)
DELETE /api/v1/buses/{bus_id}  — Soft-delete / mark inactive (Admin only)
"""
import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.dependencies.auth import get_current_user, require_admin
from app.schemas.auth import APIResponse
from app.schemas.management import BusCreate, BusUpdate, BusResponse
from app.models.bus import Bus, BusStatus

logger = logging.getLogger("smartbus.buses")
router = APIRouter(prefix="/buses", tags=["Buses"])


@router.get("", response_model=APIResponse[List[BusResponse]])
async def list_buses(
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    """List all buses. Accessible to all authenticated users."""
    result = await db.execute(select(Bus).order_by(Bus.id))
    buses = result.scalars().all()
    return APIResponse(success=True, data=[BusResponse.model_validate(b) for b in buses])


@router.post("", response_model=APIResponse[BusResponse], status_code=status.HTTP_201_CREATED)
async def create_bus(
    payload: BusCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    """Create a new bus. Admin only."""
    # Check uniqueness
    existing = await db.execute(
        select(Bus).where(
            (Bus.bus_number == payload.bus_number) | (Bus.registration_number == payload.registration_number)
        )
    )
    if existing.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "BUS_ALREADY_EXISTS", "message": "A bus with this bus_number or registration_number already exists."},
        )

    bus = Bus(
        bus_number=payload.bus_number,
        registration_number=payload.registration_number,
        capacity=payload.capacity,
        status=BusStatus.IDLE,
    )
    db.add(bus)
    await db.commit()
    await db.refresh(bus)
    logger.info(f"Bus created: {bus.bus_number} (id={bus.id})")
    return APIResponse(success=True, data=BusResponse.model_validate(bus))


@router.get("/{bus_id}", response_model=APIResponse[BusResponse])
async def get_bus(
    bus_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    """Get a single bus by ID."""
    result = await db.execute(select(Bus).where(Bus.id == bus_id))
    bus = result.scalars().first()
    if not bus:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "BUS_NOT_FOUND", "message": f"Bus with id={bus_id} not found."},
        )
    return APIResponse(success=True, data=BusResponse.model_validate(bus))


@router.patch("/{bus_id}", response_model=APIResponse[BusResponse])
async def update_bus(
    bus_id: int,
    payload: BusUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    """Update bus capacity or status. Admin only."""
    result = await db.execute(select(Bus).where(Bus.id == bus_id))
    bus = result.scalars().first()
    if not bus:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "BUS_NOT_FOUND", "message": f"Bus with id={bus_id} not found."},
        )

    if payload.capacity is not None:
        bus.capacity = payload.capacity
    if payload.status is not None:
        bus.status = BusStatus(payload.status.value)

    await db.commit()
    await db.refresh(bus)
    return APIResponse(success=True, data=BusResponse.model_validate(bus))


@router.delete("/{bus_id}", response_model=APIResponse[BusResponse])
async def deactivate_bus(
    bus_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    """Mark a bus as INACTIVE (soft delete). Admin only."""
    result = await db.execute(select(Bus).where(Bus.id == bus_id))
    bus = result.scalars().first()
    if not bus:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "BUS_NOT_FOUND", "message": f"Bus with id={bus_id} not found."},
        )

    bus.status = BusStatus.INACTIVE
    await db.commit()
    await db.refresh(bus)
    logger.info(f"Bus deactivated: {bus.bus_number} (id={bus.id})")
    return APIResponse(success=True, data=BusResponse.model_validate(bus))
