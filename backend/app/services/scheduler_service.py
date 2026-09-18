import logging
from datetime import datetime, date, time
from typing import Optional, List
import pytz
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.core.config import settings
from app.core.database import async_session_maker
from app.models.bus import Bus, BusStatus
from app.models.driver_assignment import DriverBusAssignment, AssignmentStatus
from app.models.schedule import TripSchedule, TrackingSession, SessionStatus
from app.models.route import RouteDirection

logger = logging.getLogger("smartbus.scheduler")

def get_kolkata_now() -> datetime:
    tz = pytz.timezone(settings.TIMEZONE)
    return datetime.now(tz)

def get_kolkata_today() -> date:
    return get_kolkata_now().date()

async def evaluate_scheduled_sessions_for_db(db: AsyncSession, target_datetime: Optional[datetime] = None) -> List[TrackingSession]:
    """
    Idempotent evaluation of trip schedules against Asia/Kolkata local time.
    Handles automatic creation, activation (07:35 / 16:45), and completion (09:10 / 18:30).
    Robust against missed events / server restarts.
    """
    now = target_datetime or get_kolkata_now()
    today_date = now.date()
    current_time = now.time()
    weekday_str = now.strftime("%A").upper()  # MONDAY, TUESDAY...

    logger.debug(f"Evaluating schedules for Asia/Kolkata time: {now.isoformat()} ({weekday_str})")

    # Fetch all active schedules
    stmt_schedules = select(TripSchedule).where(TripSchedule.active == True)
    res_schedules = await db.execute(stmt_schedules)
    schedules = res_schedules.scalars().all()

    processed_sessions = []

    for sched in schedules:
        # Check if today is an operating day for this schedule
        op_days = [d.strip().upper() for d in sched.days_of_week.split(",")]
        if weekday_str not in op_days:
            continue

        # Find active driver assignment for this bus
        stmt_assignment = select(DriverBusAssignment).where(
            DriverBusAssignment.bus_id == sched.bus_id,
            DriverBusAssignment.status == AssignmentStatus.ACTIVE
        )
        res_assign = await db.execute(stmt_assignment)
        assignment = res_assign.scalars().first()

        if not assignment:
            logger.warning(f"No active driver assigned for Bus ID {sched.bus_id}. Skipping session creation.")
            continue

        driver_id = assignment.driver_id

        # Query existing tracking session for today and schedule
        stmt_session = select(TrackingSession).where(
            TrackingSession.bus_id == sched.bus_id,
            TrackingSession.session_date == today_date,
            TrackingSession.schedule_id == sched.id
        )
        res_session = await db.execute(stmt_session)
        session = res_session.scalars().first()

        # Always set session status to ACTIVE for 24/7 unconstrained tracking
        is_during = True
        is_past = False
        is_before = False

        if not session:
            # Create new daily instance
            if is_during:
                initial_status = SessionStatus.ACTIVE
                started_at = now
                ended_at = None
            elif is_past:
                initial_status = SessionStatus.COMPLETED
                started_at = datetime.combine(today_date, sched.start_time)
                ended_at = datetime.combine(today_date, sched.end_time)
            else:
                initial_status = SessionStatus.SCHEDULED
                started_at = None
                ended_at = None

            session = TrackingSession(
                bus_id=sched.bus_id,
                route_id=sched.route_id,
                schedule_id=sched.id,
                driver_id=driver_id,
                session_date=today_date,
                direction=sched.direction,
                status=initial_status,
                started_at=started_at,
                ended_at=ended_at
            )
            db.add(session)
            await db.commit()
            await db.refresh(session)
            logger.info(f"Created new tracking session ID {session.id} for Bus {sched.bus_id} ({sched.direction.value}) with status {initial_status.value}")
        else:
            # Transition existing session idempotently
            updated = False
            if session.status == SessionStatus.SCHEDULED and is_during:
                session.status = SessionStatus.ACTIVE
                session.started_at = now
                updated = True
                logger.info(f"Activated session ID {session.id} for Bus {sched.bus_id}")

            elif session.status in (SessionStatus.SCHEDULED, SessionStatus.ACTIVE) and is_past:
                session.status = SessionStatus.COMPLETED
                if not session.ended_at:
                    session.ended_at = now
                updated = True
                logger.info(f"Completed session ID {session.id} for Bus {sched.bus_id}")

            if updated:
                await db.commit()
                await db.refresh(session)

        # Update Bus status accordingly
        stmt_bus = select(Bus).where(Bus.id == sched.bus_id)
        res_bus = await db.execute(stmt_bus)
        bus = res_bus.scalars().first()
        if bus:
            if session.status == SessionStatus.ACTIVE and bus.status != BusStatus.IN_TRIP:
                bus.status = BusStatus.IN_TRIP
                await db.commit()
            elif session.status == SessionStatus.COMPLETED and bus.status == BusStatus.IN_TRIP:
                bus.status = BusStatus.IDLE
                await db.commit()

        processed_sessions.append(session)

    return processed_sessions

_scheduler: Optional[AsyncIOScheduler] = None

def start_background_scheduler():
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler()
        
        async def scheduled_job():
            async with async_session_maker() as db:
                try:
                    await evaluate_scheduled_sessions_for_db(db)
                except Exception as e:
                    logger.error(f"Error in automatic scheduler job: {e}")

        _scheduler.add_job(scheduled_job, 'interval', seconds=30, id='smartbus_session_scheduler')
        _scheduler.start()
        logger.info("Asia/Kolkata Automatic Session Scheduler started (30s interval).")

def stop_background_scheduler():
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown()
        _scheduler = None
        logger.info("Automatic Session Scheduler stopped.")
