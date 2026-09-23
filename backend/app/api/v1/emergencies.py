from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.sql import func

from app.core.database import get_db
from app.dependencies.auth import require_admin
from app.schemas.auth import APIResponse, UserResponse
from app.schemas.emergency import EmergencyResponse, EmergencyUpdate
from app.models.emergency import Emergency, EmergencyStatus

router = APIRouter(prefix="/emergencies", tags=["Emergencies"])

@router.get("", response_model=APIResponse[List[EmergencyResponse]])
async def list_emergencies(
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
    status: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    emergency_type: Optional[str] = Query(None),
    bus_id: Optional[int] = Query(None),
    driver_id: Optional[int] = Query(None),
    limit: int = Query(100, le=500)
):
    stmt = select(Emergency).order_by(desc(Emergency.created_at)).limit(limit)
    if status:
        stmt = stmt.where(Emergency.status == status)
    if severity:
        stmt = stmt.where(Emergency.severity == severity)
    if emergency_type:
        stmt = stmt.where(Emergency.type == emergency_type)
    if bus_id:
        stmt = stmt.where(Emergency.bus_id == bus_id)
    if driver_id:
        stmt = stmt.where(Emergency.driver_id == driver_id)
        
    result = await db.execute(stmt)
    emergencies = result.scalars().all()
    return APIResponse(success=True, data=[EmergencyResponse.model_validate(e) for e in emergencies])

@router.patch("/{emergency_id}", response_model=APIResponse[EmergencyResponse])
async def update_emergency(
    emergency_id: int,
    payload: EmergencyUpdate,
    db: AsyncSession = Depends(get_db),
    admin_user: UserResponse = Depends(require_admin)
):
    result = await db.execute(select(Emergency).where(Emergency.id == emergency_id))
    emergency = result.scalars().first()
    if not emergency:
        raise HTTPException(status_code=404, detail={"message": "Emergency not found"})
        
    from app.models.user import User
    res_admin = await db.execute(select(User).where(User.firebase_uid == admin_user.firebase_uid))
    admin = res_admin.scalars().first()
    admin_id = admin.id if admin else None

    # Handle transitions safely
    if payload.status == EmergencyStatus.ACKNOWLEDGED and emergency.status == EmergencyStatus.ACTIVE:
        emergency.status = EmergencyStatus.ACKNOWLEDGED
        emergency.acknowledged_at = func.now()
        if admin_id:
            emergency.acknowledged_by = admin_id
            
    elif payload.status == EmergencyStatus.RESOLVED and emergency.status != EmergencyStatus.RESOLVED:
        emergency.status = EmergencyStatus.RESOLVED
        emergency.resolved_at = func.now()
        if admin_id:
            emergency.resolved_by = admin_id
            
    await db.commit()
    await db.refresh(emergency)
    return APIResponse(success=True, data=EmergencyResponse.model_validate(emergency))
