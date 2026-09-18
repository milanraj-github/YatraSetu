"""
Admin: Driver management and bus assignment endpoints.

GET    /api/v1/drivers                          — List all drivers
GET    /api/v1/drivers/{driver_id}              — Get driver detail + current assignment
POST   /api/v1/drivers/{driver_id}/assign-bus   — Assign a bus to a driver (Admin)
DELETE /api/v1/drivers/{driver_id}/assign-bus   — Remove bus assignment (Admin)
GET    /api/v1/drivers/{driver_id}/assignments  — History of assignments (Admin)
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.dependencies.auth import get_current_user, require_admin
from app.schemas.auth import APIResponse, UserRole
from app.schemas.management import DriverResponse, AssignBusRequest, DriverAssignmentResponse
from app.models.user import User, UserRole as DBUserRole
from app.models.driver_assignment import DriverBusAssignment, AssignmentStatus
from app.models.bus import Bus

logger = logging.getLogger("smartbus.drivers")
router = APIRouter(prefix="/drivers", tags=["Driver Management"])


async def _get_driver_or_404(db: AsyncSession, driver_id: int) -> User:
    result = await db.execute(
        select(User).where(User.id == driver_id, User.role == DBUserRole.DRIVER)
    )
    driver = result.scalars().first()
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "DRIVER_NOT_FOUND", "message": f"Driver with id={driver_id} not found."},
        )
    return driver


@router.get("", response_model=APIResponse[List[DriverResponse]])
async def list_drivers(db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    """List all users with DRIVER role. Admin only."""
    result = await db.execute(
        select(User).where(User.role == DBUserRole.DRIVER).order_by(User.id)
    )
    drivers = result.scalars().all()
    return APIResponse(success=True, data=[DriverResponse.model_validate(d) for d in drivers])


@router.get("/{driver_id}", response_model=APIResponse[dict])
async def get_driver(driver_id: int, db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    """Get a driver's profile and their current active bus assignment."""
    driver = await _get_driver_or_404(db, driver_id)

    # Fetch current active assignment
    result = await db.execute(
        select(DriverBusAssignment).where(
            DriverBusAssignment.driver_id == driver_id,
            DriverBusAssignment.status == AssignmentStatus.ACTIVE,
        )
    )
    assignment = result.scalars().first()

    return APIResponse(
        success=True,
        data={
            "driver": DriverResponse.model_validate(driver),
            "current_assignment": DriverAssignmentResponse.model_validate(assignment) if assignment else None,
        },
    )


@router.post("/{driver_id}/assign-bus", response_model=APIResponse[DriverAssignmentResponse])
async def assign_bus(
    driver_id: int,
    payload: AssignBusRequest,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    """
    Assign a bus to a driver.
    - Deactivates any existing active assignment for this driver.
    - Creates a new ACTIVE assignment.
    Admin only.
    """
    driver = await _get_driver_or_404(db, driver_id)

    # Verify bus exists
    bus_result = await db.execute(select(Bus).where(Bus.id == payload.bus_id))
    bus = bus_result.scalars().first()
    if not bus:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "BUS_NOT_FOUND", "message": f"Bus id={payload.bus_id} not found."},
        )

    # Deactivate existing active assignments for this driver
    existing_result = await db.execute(
        select(DriverBusAssignment).where(
            DriverBusAssignment.driver_id == driver_id,
            DriverBusAssignment.status == AssignmentStatus.ACTIVE,
        )
    )
    for existing in existing_result.scalars().all():
        existing.status = AssignmentStatus.INACTIVE
        logger.info(f"Deactivated old assignment id={existing.id} for driver {driver_id}")

    # Also deactivate any other driver currently assigned to this bus
    conflicting_result = await db.execute(
        select(DriverBusAssignment).where(
            DriverBusAssignment.bus_id == payload.bus_id,
            DriverBusAssignment.status == AssignmentStatus.ACTIVE,
            DriverBusAssignment.driver_id != driver_id,
        )
    )
    for conflicting in conflicting_result.scalars().all():
        conflicting.status = AssignmentStatus.INACTIVE
        logger.info(f"Deactivated conflicting assignment id={conflicting.id} on bus {payload.bus_id}")

    # Create new assignment
    assignment = DriverBusAssignment(
        driver_id=driver_id,
        bus_id=payload.bus_id,
        assigned_until=payload.assigned_until,
        status=AssignmentStatus.ACTIVE,
    )
    db.add(assignment)
    await db.commit()
    await db.refresh(assignment)
    logger.info(f"Driver {driver_id} assigned to bus {payload.bus_id} (assignment id={assignment.id})")
    return APIResponse(success=True, data=DriverAssignmentResponse.model_validate(assignment))


@router.delete("/{driver_id}/assign-bus", response_model=APIResponse[dict])
async def unassign_bus(driver_id: int, db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    """Remove the active bus assignment for a driver. Admin only."""
    driver = await _get_driver_or_404(db, driver_id)

    result = await db.execute(
        select(DriverBusAssignment).where(
            DriverBusAssignment.driver_id == driver_id,
            DriverBusAssignment.status == AssignmentStatus.ACTIVE,
        )
    )
    assignment = result.scalars().first()
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NO_ACTIVE_ASSIGNMENT", "message": f"Driver id={driver_id} has no active bus assignment."},
        )

    assignment.status = AssignmentStatus.INACTIVE
    await db.commit()
    return APIResponse(success=True, data={"message": f"Bus assignment deactivated for driver {driver_id}."})


@router.get("/{driver_id}/assignments", response_model=APIResponse[List[DriverAssignmentResponse]])
async def get_assignment_history(driver_id: int, db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    """Full assignment history for a driver. Admin only."""
    await _get_driver_or_404(db, driver_id)
    result = await db.execute(
        select(DriverBusAssignment)
        .where(DriverBusAssignment.driver_id == driver_id)
        .order_by(DriverBusAssignment.assigned_from.desc())
    )
    assignments = result.scalars().all()
    return APIResponse(success=True, data=[DriverAssignmentResponse.model_validate(a) for a in assignments])
