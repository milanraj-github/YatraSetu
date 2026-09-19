import uuid
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bus import Bus
from app.schemas.bus import BusCreate, BusUpdate


async def create_bus(db: AsyncSession, bus_in: BusCreate) -> Bus:
    """Create a new bus in the system after validating uniqueness constraints."""
    # Check bus_number uniqueness
    res_num = await db.execute(select(Bus).where(Bus.bus_number == bus_in.bus_number))
    if res_num.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Bus with number '{bus_in.bus_number}' already exists",
        )

    # Check registration_number uniqueness
    res_reg = await db.execute(
        select(Bus).where(Bus.registration_number == bus_in.registration_number)
    )
    if res_reg.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Bus with registration number '{bus_in.registration_number}' already exists",
        )

    bus = Bus(
        bus_number=bus_in.bus_number,
        registration_number=bus_in.registration_number,
        capacity=bus_in.capacity,
        is_active=bus_in.is_active,
    )
    db.add(bus)
    await db.commit()
    await db.refresh(bus)
    return bus


async def get_bus_by_id(db: AsyncSession, bus_id: uuid.UUID) -> Optional[Bus]:
    """Retrieve a single bus by its UUID."""
    result = await db.execute(select(Bus).where(Bus.id == bus_id))
    return result.scalar_one_or_none()


async def list_buses(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    is_active: Optional[bool] = None,
) -> List[Bus]:
    """List buses with pagination and optional active status filtering."""
    query = select(Bus).order_by(Bus.created_at.desc()).offset(skip).limit(limit)
    if is_active is not None:
        query = query.where(Bus.is_active == is_active)
    result = await db.execute(query)
    return list(result.scalars().all())


async def update_bus(db: AsyncSession, bus: Bus, bus_in: BusUpdate) -> Bus:
    """Update an existing bus entity with uniqueness conflict verification."""
    update_data = bus_in.model_dump(exclude_unset=True)

    if "bus_number" in update_data and update_data["bus_number"] != bus.bus_number:
        res = await db.execute(
            select(Bus).where(
                Bus.bus_number == update_data["bus_number"],
                Bus.id != bus.id,
            )
        )
        if res.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Bus with number '{update_data['bus_number']}' already exists",
            )
        bus.bus_number = update_data["bus_number"]

    if (
        "registration_number" in update_data
        and update_data["registration_number"] != bus.registration_number
    ):
        res = await db.execute(
            select(Bus).where(
                Bus.registration_number == update_data["registration_number"],
                Bus.id != bus.id,
            )
        )
        if res.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Bus with registration number '{update_data['registration_number']}' already exists",
            )
        bus.registration_number = update_data["registration_number"]

    if "capacity" in update_data and update_data["capacity"] is not None:
        bus.capacity = update_data["capacity"]

    if "is_active" in update_data and update_data["is_active"] is not None:
        bus.is_active = update_data["is_active"]

    await db.commit()
    await db.refresh(bus)
    return bus


async def deactivate_bus(db: AsyncSession, bus: Bus) -> Bus:
    """Safely deactivate a bus by setting is_active = False."""
    bus.is_active = False
    await db.commit()
    await db.refresh(bus)
    return bus
