with open("app/api/v1/drivers.py", "r") as f:
    content = f.read()

imports = """
from app.models.route import Route, RouteStop
from app.models.schedule import TrackingSession
from app.services.scheduler_service import evaluate_scheduled_sessions_for_db, get_kolkata_today
from app.api.v1.tracking import get_db_user_from_auth
from app.schemas.tracking import SessionSummarySchema, RouteSummarySchema, ScheduleSummarySchema, BusSummarySchema
from pydantic import BaseModel
from typing import List, Optional

class TodayScheduleResponse(BaseModel):
    id: int
    bus: BusSummarySchema
    session: SessionSummarySchema
    schedule: ScheduleSummarySchema
    route: RouteSummarySchema
"""

endpoint = """
@router.get("/me/schedules/today", response_model=APIResponse[List[TodayScheduleResponse]])
async def get_my_schedules_today(db: AsyncSession = Depends(get_db), current_user: UserResponse = Depends(get_current_user)):
    if current_user.role != UserRole.DRIVER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "Only drivers can access their schedules."},
        )

    db_driver = await get_db_user_from_auth(db, current_user)
    await evaluate_scheduled_sessions_for_db(db)
    
    today_date = get_kolkata_today()
    
    stmt = select(TrackingSession).options(
        selectinload(TrackingSession.bus),
        selectinload(TrackingSession.schedule),
        selectinload(TrackingSession.route).selectinload(Route.stops).selectinload(RouteStop.boarding_point)
    ).where(
        TrackingSession.driver_id == db_driver.id,
        TrackingSession.session_date == today_date
    ).order_by(TrackingSession.id.asc())
    
    result = await db.execute(stmt)
    sessions = result.scalars().all()
    
    data = []
    for session in sessions:
        data.append(TodayScheduleResponse(
            id=session.id,
            bus=BusSummarySchema.model_validate(session.bus),
            session=SessionSummarySchema.model_validate(session),
            schedule=ScheduleSummarySchema.model_validate(session.schedule),
            route=RouteSummarySchema.model_validate(session.route)
        ))
        
    return APIResponse(success=True, data=data)
"""

# Insert imports after standard imports
parts = content.split("from app.schemas.management import", 1)
new_content = parts[0] + "from app.schemas.management import" + parts[1].split("\n", 1)[0] + "\n" + imports + "\n" + parts[1].split("\n", 1)[1] + "\n" + endpoint

with open("app/api/v1/drivers.py", "w") as f:
    f.write(new_content)
