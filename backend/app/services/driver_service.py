import uuid
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.bus import Bus
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.driver import DriverAssignmentResponse


async def assign_bus_to_driver(
    db: AsyncSession, driver_id: uuid.UUID, bus_id: uuid.UUID
) -> DriverAssignmentResponse:
    """Assign a bus to a driver after verifying roles and active status."""
    # 1. Verify driver exists and has DRIVER role
    res_driver = await db.execute(
        select(User)
        .where(User.id == driver_id)
        .options(selectinload(User.assigned_bus))
    )
    driver = res_driver.scalar_one_or_none()
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Driver not found",
        )
    if driver.role != UserRole.DRIVER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User is not a driver (role is {driver.role.value})",
        )

    # 2. Verify bus exists and is active
    res_bus = await db.execute(select(Bus).where(Bus.id == bus_id))
    bus = res_bus.scalar_one_or_none()
    if not bus:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bus not found",
        )
    if not bus.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot assign an inactive bus",
        )

    # 3. Assign bus
    driver.assigned_bus_id = bus.id
    driver.assigned_bus = bus
    await db.commit()
    await db.refresh(driver, attribute_names=["assigned_bus"])

    return DriverAssignmentResponse(
        driver_id=driver.id,
        driver_name=driver.full_name,
        driver_email=driver.email,
        assigned_bus_id=bus.id,
        assigned_bus_number=bus.bus_number,
        assigned_bus_registration=bus.registration_number,
    )


async def unassign_bus_from_driver(
    db: AsyncSession, driver_id: uuid.UUID
) -> DriverAssignmentResponse:
    """Unassign currently assigned bus from a driver."""
    res_driver = await db.execute(
        select(User)
        .where(User.id == driver_id)
        .options(selectinload(User.assigned_bus))
    )
    driver = res_driver.scalar_one_or_none()
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Driver not found",
        )
    if driver.role != UserRole.DRIVER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User is not a driver (role is {driver.role.value})",
        )
    if driver.assigned_bus_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Driver has no assigned bus",
        )

    driver.assigned_bus_id = None
    driver.assigned_bus = None
    await db.commit()
    await db.refresh(driver)

    return DriverAssignmentResponse(
        driver_id=driver.id,
        driver_name=driver.full_name,
        driver_email=driver.email,
        assigned_bus_id=None,
        assigned_bus_number=None,
        assigned_bus_registration=None,
    )


async def get_driver_assignment(
    db: AsyncSession, driver_id: uuid.UUID, current_user: User
) -> DriverAssignmentResponse:
    """Retrieve assignment details for a driver."""
    if current_user.role == UserRole.DRIVER and current_user.id != driver_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Drivers can only view their own assignment",
        )

    res_driver = await db.execute(
        select(User)
        .where(User.id == driver_id)
        .options(selectinload(User.assigned_bus))
    )
    driver = res_driver.scalar_one_or_none()
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Driver not found",
        )
    if driver.role != UserRole.DRIVER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User is not a driver (role is {driver.role.value})",
        )

    bus = driver.assigned_bus
    return DriverAssignmentResponse(
        driver_id=driver.id,
        driver_name=driver.full_name,
        driver_email=driver.email,
        assigned_bus_id=bus.id if bus else None,
        assigned_bus_number=bus.bus_number if bus else None,
        assigned_bus_registration=bus.registration_number if bus else None,
    )
