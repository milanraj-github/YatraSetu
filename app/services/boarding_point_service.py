import uuid
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.boarding_point import BoardingPoint
from app.schemas.boarding_point import BoardingPointCreate, BoardingPointUpdate


async def create_boarding_point(
    db: AsyncSession, bp_in: BoardingPointCreate
) -> BoardingPoint:
    """Create a new boarding point."""
    bp = BoardingPoint(
        name=bp_in.name,
        latitude=bp_in.latitude,
        longitude=bp_in.longitude,
        address=bp_in.address,
        is_active=bp_in.is_active,
    )
    db.add(bp)
    await db.commit()
    await db.refresh(bp)
    return bp


async def get_boarding_point_by_id(
    db: AsyncSession, bp_id: uuid.UUID
) -> Optional[BoardingPoint]:
    """Retrieve a boarding point by its UUID."""
    result = await db.execute(
        select(BoardingPoint).where(BoardingPoint.id == bp_id)
    )
    return result.scalar_one_or_none()


async def list_boarding_points(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    is_active: Optional[bool] = None,
) -> List[BoardingPoint]:
    """List boarding points with pagination."""
    query = (
        select(BoardingPoint)
        .order_by(BoardingPoint.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    if is_active is not None:
        query = query.where(BoardingPoint.is_active == is_active)
    result = await db.execute(query)
    return list(result.scalars().all())


async def update_boarding_point(
    db: AsyncSession, bp: BoardingPoint, bp_in: BoardingPointUpdate
) -> BoardingPoint:
    """Update boarding point attributes."""
    update_data = bp_in.model_dump(exclude_unset=True)

    if "name" in update_data and update_data["name"] is not None:
        bp.name = update_data["name"]
    if "latitude" in update_data and update_data["latitude"] is not None:
        bp.latitude = update_data["latitude"]
    if "longitude" in update_data and update_data["longitude"] is not None:
        bp.longitude = update_data["longitude"]
    if "address" in update_data:
        bp.address = update_data["address"]
    if "is_active" in update_data and update_data["is_active"] is not None:
        bp.is_active = update_data["is_active"]

    await db.commit()
    await db.refresh(bp)
    return bp


async def deactivate_boarding_point(
    db: AsyncSession, bp: BoardingPoint
) -> BoardingPoint:
    """Safely deactivate a boarding point."""
    bp.is_active = False
    await db.commit()
    await db.refresh(bp)
    return bp
