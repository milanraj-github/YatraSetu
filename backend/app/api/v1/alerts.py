from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.sql import func

from app.core.database import get_db
from app.dependencies.auth import require_admin
from app.schemas.auth import APIResponse, UserResponse
from app.schemas.alert import AlertResponse, AlertUpdate
from app.models.alert import Alert, AlertStatus

router = APIRouter(prefix="/alerts", tags=["Alerts"])

@router.get("", response_model=APIResponse[List[AlertResponse]])
async def list_alerts(
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
    status: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    alert_type: Optional[str] = Query(None),
    bus_id: Optional[int] = Query(None),
    limit: int = Query(100, le=500)
):
    stmt = select(Alert).order_by(desc(Alert.created_at)).limit(limit)
    if status:
        stmt = stmt.where(Alert.status == status)
    if severity:
        stmt = stmt.where(Alert.severity == severity)
    if alert_type:
        stmt = stmt.where(Alert.type == alert_type)
    if bus_id:
        stmt = stmt.where(Alert.bus_id == bus_id)
        
    result = await db.execute(stmt)
    alerts = result.scalars().all()
    return APIResponse(success=True, data=[AlertResponse.model_validate(a) for a in alerts])

@router.patch("/{alert_id}", response_model=APIResponse[AlertResponse])
async def update_alert(
    alert_id: int,
    payload: AlertUpdate,
    db: AsyncSession = Depends(get_db),
    admin_user: UserResponse = Depends(require_admin)
):
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalars().first()
    if not alert:
        raise HTTPException(status_code=404, detail={"message": "Alert not found"})
        
    if payload.status == AlertStatus.RESOLVED and alert.status != AlertStatus.RESOLVED:
        alert.status = AlertStatus.RESOLVED
        alert.resolved_at = func.now()
        # Find admin ID
        from app.models.user import User
        res_admin = await db.execute(select(User).where(User.firebase_uid == admin_user.firebase_uid))
        admin = res_admin.scalars().first()
        if admin:
            alert.resolved_by = admin.id
            
    elif payload.status == AlertStatus.ACTIVE:
        alert.status = AlertStatus.ACTIVE
        alert.resolved_at = None
        alert.resolved_by = None
        
    await db.commit()
    await db.refresh(alert)
    return APIResponse(success=True, data=AlertResponse.model_validate(alert))
