import re

with open("app/api/v1/tracking.py", "r") as f:
    content = f.read()

endpoint = """
@router.get("/gps/stop-intelligence", response_model=APIResponse[StopIntelligenceResponse])
async def get_stop_intelligence(
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(require_driver)
):
    from app.services.tracking_service import calculate_stop_intelligence, get_redis_json
    driver_user = await get_db_user_from_auth(db, current_user)
    
    # Get active session
    stmt_assign = select(DriverBusAssignment).where(
        DriverBusAssignment.driver_id == driver_user.id,
        DriverBusAssignment.status == AssignmentStatus.ACTIVE
    )
    res_assign = await db.execute(stmt_assign)
    assignment = res_assign.scalars().first()

    if not assignment:
        return APIResponse(success=True, data={"status": "NO_ACTIVE_TRIP"})
        
    bus_id = assignment.bus_id
    today_date = get_kolkata_now().date()
    
    stmt_session = select(TrackingSession).where(
        TrackingSession.bus_id == bus_id,
        TrackingSession.driver_id == driver_user.id,
        TrackingSession.session_date == today_date,
        TrackingSession.status == SessionStatus.ACTIVE
    ).order_by(TrackingSession.id.asc())
    res_session = await db.execute(stmt_session)
    session = res_session.scalars().first()

    if not session:
        return APIResponse(success=True, data={"status": "NO_ACTIVE_TRIP"})

    redis_key = f"bus:{bus_id}:latest_location"
    latest_loc = await get_redis_json(redis_key)
    
    if not latest_loc or "latitude" not in latest_loc:
        return APIResponse(success=True, data={"status": "GPS_UNAVAILABLE"})
        
    intel = await calculate_stop_intelligence(db, session.id, bus_id, latest_loc["latitude"], latest_loc["longitude"])
    return APIResponse(success=True, data=intel)
"""

if "StopIntelligenceResponse" not in content:
    content = content.replace("GpsBatchIngestResponse", "GpsBatchIngestResponse, StopIntelligenceResponse, StopIntelligenceStopSchema")
    content = content + "\n" + endpoint
    with open("app/api/v1/tracking.py", "w") as f:
        f.write(content)
