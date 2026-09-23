from datetime import date, timedelta, datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.dependencies.auth import require_admin
from app.schemas.auth import APIResponse
from app.schemas.analytics import (
    AnalyticsSummaryResponse, TripAnalytics, AlertAnalytics, EmergencyAnalytics,
    BusUtilization, DriverOperations, RoutePerformance, DailyTrend
)
from app.models.schedule import TrackingSession, SessionStatus
from app.models.alert import Alert, AlertStatus
from app.models.emergency import Emergency, EmergencyStatus
from app.models.bus import Bus
from app.models.route import Route
from app.models.user import User

router = APIRouter(prefix="/analytics", tags=["Analytics"])

@router.get("/summary", response_model=APIResponse[AnalyticsSummaryResponse])
async def get_analytics_summary(
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
    start_date: date = Query(...),
    end_date: date = Query(...)
):
    # Base conditions
    trip_cond = and_(TrackingSession.session_date >= start_date, TrackingSession.session_date <= end_date)
    # created_at is datetime, cast to date or compare with datetime boundaries
    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())
    alert_cond = and_(Alert.created_at >= start_dt, Alert.created_at <= end_dt)
    emg_cond = and_(Emergency.created_at >= start_dt, Emergency.created_at <= end_dt)

    # 1. Fetch Trips (eager load bus, driver, route)
    # We fetch these to build the cross-aggregations easily in python since they are bounded by date.
    stmt_trips = select(TrackingSession).options(
        selectinload(TrackingSession.bus),
        selectinload(TrackingSession.driver),
        selectinload(TrackingSession.route)
    ).where(trip_cond)
    res_trips = await db.execute(stmt_trips)
    trips = res_trips.scalars().all()

    # 2. Fetch Alerts (eager route, bus)
    stmt_alerts = select(Alert).options(
        selectinload(Alert.bus),
        selectinload(Alert.route)
    ).where(alert_cond)
    res_alerts = await db.execute(stmt_alerts)
    alerts = res_alerts.scalars().all()

    # 3. Fetch Emergencies (eager route, driver, bus)
    stmt_emg = select(Emergency).options(
        selectinload(Emergency.bus),
        selectinload(Emergency.driver),
        selectinload(Emergency.route)
    ).where(emg_cond)
    res_emg = await db.execute(stmt_emg)
    emergencies = res_emg.scalars().all()

    # ---------------------------------------------------------
    # AGGREGATE TRIPS
    # ---------------------------------------------------------
    trip_trend = {}
    bus_stats = {}
    driver_stats = {}
    route_stats = {}
    
    trip_total = len(trips)
    trip_completed = 0
    trip_cancelled = 0
    trip_active = 0
    trip_scheduled = 0

    for t in trips:
        d_str = t.session_date.isoformat()
        trip_trend[d_str] = trip_trend.get(d_str, 0) + 1

        if t.status == SessionStatus.COMPLETED: trip_completed += 1
        elif t.status == SessionStatus.CANCELLED: trip_cancelled += 1
        elif t.status == SessionStatus.ACTIVE: trip_active += 1
        elif t.status == SessionStatus.SCHEDULED: trip_scheduled += 1

        # Bus Agg
        if t.bus:
            b_id = t.bus.id
            if b_id not in bus_stats:
                bus_stats[b_id] = {"id": b_id, "num": t.bus.bus_number, "trips": 0, "completed": 0, "cancelled": 0, "active": 0}
            bus_stats[b_id]["trips"] += 1
            if t.status == SessionStatus.COMPLETED: bus_stats[b_id]["completed"] += 1
            elif t.status == SessionStatus.CANCELLED: bus_stats[b_id]["cancelled"] += 1
            elif t.status == SessionStatus.ACTIVE: bus_stats[b_id]["active"] += 1
            
        # Driver Agg
        if t.driver:
            d_id = t.driver.id
            if d_id not in driver_stats:
                driver_stats[d_id] = {"id": d_id, "name": t.driver.full_name, "trips": 0, "completed": 0, "cancelled": 0, "emg": 0}
            driver_stats[d_id]["trips"] += 1
            if t.status == SessionStatus.COMPLETED: driver_stats[d_id]["completed"] += 1
            elif t.status == SessionStatus.CANCELLED: driver_stats[d_id]["cancelled"] += 1

        # Route Agg
        if t.route:
            r_id = t.route.id
            if r_id not in route_stats:
                route_stats[r_id] = {"id": r_id, "name": t.route.name, "trips": 0, "completed": 0, "cancelled": 0, "alerts": 0, "emg": 0}
            route_stats[r_id]["trips"] += 1
            if t.status == SessionStatus.COMPLETED: route_stats[r_id]["completed"] += 1
            elif t.status == SessionStatus.CANCELLED: route_stats[r_id]["cancelled"] += 1

    # ---------------------------------------------------------
    # AGGREGATE ALERTS
    # ---------------------------------------------------------
    alert_trend = {}
    alert_by_type = {}
    alert_active = 0
    alert_resolved = 0
    
    for a in alerts:
        d_str = a.created_at.date().isoformat()
        alert_trend[d_str] = alert_trend.get(d_str, 0) + 1
        
        typ = a.type.value
        alert_by_type[typ] = alert_by_type.get(typ, 0) + 1
        
        if a.status == AlertStatus.ACTIVE: alert_active += 1
        elif a.status == AlertStatus.RESOLVED: alert_resolved += 1

        if a.route_id and a.route_id in route_stats:
            route_stats[a.route_id]["alerts"] += 1

    # ---------------------------------------------------------
    # AGGREGATE EMERGENCIES
    # ---------------------------------------------------------
    emg_trend = {}
    emg_by_type = {}
    emg_active = 0
    emg_ack = 0
    emg_resolved = 0
    
    for e in emergencies:
        d_str = e.created_at.date().isoformat()
        emg_trend[d_str] = emg_trend.get(d_str, 0) + 1
        
        typ = e.type.value
        emg_by_type[typ] = emg_by_type.get(typ, 0) + 1
        
        if e.status == EmergencyStatus.ACTIVE: emg_active += 1
        elif e.status == EmergencyStatus.ACKNOWLEDGED: emg_ack += 1
        elif e.status == EmergencyStatus.RESOLVED: emg_resolved += 1

        if e.route_id and e.route_id in route_stats:
            route_stats[e.route_id]["emg"] += 1
        if e.driver_id and e.driver_id in driver_stats:
            driver_stats[e.driver_id]["emg"] += 1

    # Format lists
    trip_trend_list = [{"date": k, "count": v} for k, v in sorted(trip_trend.items())]
    alert_trend_list = [{"date": k, "count": v} for k, v in sorted(alert_trend.items())]
    emg_trend_list = [{"date": k, "count": v} for k, v in sorted(emg_trend.items())]

    buses_res = [
        BusUtilization(bus_id=v["id"], bus_number=v["num"], trips=v["trips"], completed=v["completed"], cancelled=v["cancelled"], active=v["active"])
        for v in bus_stats.values()
    ]
    drivers_res = [
        DriverOperations(driver_id=v["id"], driver_name=v["name"], trips=v["trips"], completed=v["completed"], cancelled=v["cancelled"], emergencies=v["emg"])
        for v in driver_stats.values()
    ]
    routes_res = [
        RoutePerformance(route_id=v["id"], route_name=v["name"], trips=v["trips"], completed=v["completed"], cancelled=v["cancelled"], alerts=v["alerts"], emergencies=v["emg"])
        for v in route_stats.values()
    ]

    return APIResponse(success=True, data=AnalyticsSummaryResponse(
        trips=TripAnalytics(total=trip_total, completed=trip_completed, cancelled=trip_cancelled, active=trip_active, scheduled=trip_scheduled, trend=trip_trend_list),
        alerts=AlertAnalytics(total=len(alerts), active=alert_active, resolved=alert_resolved, by_type=alert_by_type, trend=alert_trend_list),
        emergencies=EmergencyAnalytics(total=len(emergencies), active=emg_active, acknowledged=emg_ack, resolved=emg_resolved, by_type=emg_by_type, trend=emg_trend_list),
        buses=buses_res,
        drivers=drivers_res,
        routes=routes_res
    ))
