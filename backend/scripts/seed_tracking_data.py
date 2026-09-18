import os
import sys
import asyncio
import logging
from datetime import time
from sqlalchemy.future import select

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import async_session_maker
from app.models.user import User, UserRole, UserStatus
from app.models.bus import Bus, BusStatus
from app.models.driver_assignment import DriverBusAssignment, AssignmentStatus
from app.models.route import Route, BoardingPoint, RouteStop, RouteDirection
from app.models.schedule import TripSchedule

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("smartbus.seed_tracking")

async def seed_tracking_data():
    logger.info("Starting Phase 2 Tracking Data Seed Script...")
    
    async with async_session_maker() as db:
        # 1. Seed Users (Admin 1, Drivers 1-3)
        user_specs = [
            ("admin1@sode-edu.in", "Admin One", UserRole.ADMIN, "mock-uid-admin1@sode-edu.in"),
            ("driver1@sode-edu.in", "Driver One", UserRole.DRIVER, "mock-uid-driver1@sode-edu.in"),
            ("driver2@sode-edu.in", "Driver Two", UserRole.DRIVER, "mock-uid-driver2@sode-edu.in"),
            ("driver3@sode-edu.in", "Driver Three", UserRole.DRIVER, "mock-uid-driver3@sode-edu.in"),
        ]
        
        users_by_email = {}
        for email, name, role, uid in user_specs:
            stmt = select(User).where(User.email == email)
            res = await db.execute(stmt)
            usr = res.scalars().first()
            if not usr:
                usr = User(
                    firebase_uid=uid,
                    email=email,
                    full_name=name,
                    role=role,
                    status=UserStatus.ACTIVE,
                    is_email_verified=True
                )
                db.add(usr)
                await db.flush()
                logger.info(f"Created DB user: {email} (id={usr.id})")
            users_by_email[email] = usr

        # 2. Seed Buses (BUS-01, BUS-02, BUS-03)
        bus_specs = [
            ("BUS-01", "KA-20-F-1001", 50),
            ("BUS-02", "KA-20-F-1002", 50),
            ("BUS-03", "KA-20-F-1003", 50),
        ]
        buses_by_number = {}
        for bus_num, reg_num, cap in bus_specs:
            stmt = select(Bus).where(Bus.bus_number == bus_num)
            res = await db.execute(stmt)
            bus = res.scalars().first()
            if not bus:
                bus = Bus(
                    bus_number=bus_num,
                    registration_number=reg_num,
                    capacity=cap,
                    status=BusStatus.IDLE
                )
                db.add(bus)
                await db.flush()
                logger.info(f"Created Bus: {bus_num} (id={bus.id})")
            buses_by_number[bus_num] = bus

        # 3. Driver Assignments (Driver 1 -> BUS-01, Driver 2 -> BUS-02, Driver 3 -> BUS-03)
        assignments_spec = [
            (users_by_email["driver1@sode-edu.in"].id, buses_by_number["BUS-01"].id),
            (users_by_email["driver2@sode-edu.in"].id, buses_by_number["BUS-02"].id),
            (users_by_email["driver3@sode-edu.in"].id, buses_by_number["BUS-03"].id),
        ]
        for drv_id, b_id in assignments_spec:
            stmt = select(DriverBusAssignment).where(
                DriverBusAssignment.driver_id == drv_id,
                DriverBusAssignment.bus_id == b_id,
                DriverBusAssignment.status == AssignmentStatus.ACTIVE
            )
            res = await db.execute(stmt)
            if not res.scalars().first():
                assign = DriverBusAssignment(
                    driver_id=drv_id,
                    bus_id=b_id,
                    status=AssignmentStatus.ACTIVE
                )
                db.add(assign)
                logger.info(f"Assigned Driver {drv_id} -> Bus {b_id}")

        # 4. Routes & Stopping Points
        # BUS-01: Udupi City Route (9 stops)
        # BUS-02: Manipal Express Route (3 stops)
        # BUS-03: Kundapura Coastal Route (4 stops)
        bus01_stops = [
            "Udupi Bus Stand", "Kalsanka", "Gundibail", "Kunjibettu",
            "Indrali", "Manipal Coin Circle", "Tiger Circle", "Perampalli", "SMVITM Campus"
        ]
        bus02_stops = ["Manipal Tiger Circle", "Innanje Cross", "SMVITM Campus"]
        bus03_stops = ["Kundapura Bus Stand", "Saligrama", "Brahmavara", "SMVITM Campus"]

        routes_data = [
            ("BUS-01", "ROUTE-01", "Udupi City Route", bus01_stops),
            ("BUS-02", "ROUTE-02", "Manipal Express Route", bus02_stops),
            ("BUS-03", "ROUTE-03", "Kundapura Coastal Route", bus03_stops),
        ]

        for bus_num, code, r_name, stops_list in routes_data:
            bus = buses_by_number[bus_num]
            stmt_r = select(Route).where(Route.code == code)
            res_r = await db.execute(stmt_r)
            route = res_r.scalars().first()
            if not route:
                route = Route(
                    name=r_name,
                    code=code
                )
                db.add(route)
                await db.flush()
                logger.info(f"Created Route {code}: {r_name}")

                # Create Boarding Points & RouteStops for MORNING & EVENING
                for idx, stop_name in enumerate(stops_list, start=1):
                    stmt_bp = select(BoardingPoint).where(BoardingPoint.name == stop_name)
                    res_bp = await db.execute(stmt_bp)
                    bp = res_bp.scalars().first()
                    if not bp:
                        bp = BoardingPoint(
                            name=stop_name,
                            latitude=0.0,
                            longitude=0.0
                        )
                        db.add(bp)
                        await db.flush()

                    # Morning Stop
                    rs_morning = RouteStop(
                        route_id=route.id,
                        boarding_point_id=bp.id,
                        sequence_order=idx,
                        direction=RouteDirection.MORNING
                    )
                    db.add(rs_morning)

                    # Evening Stop (Reversed Sequence)
                    rev_order = len(stops_list) - idx + 1
                    rs_evening = RouteStop(
                        route_id=route.id,
                        boarding_point_id=bp.id,
                        sequence_order=rev_order,
                        direction=RouteDirection.EVENING
                    )
                    db.add(rs_evening)

            # 5. Schedules for each bus
            # Morning Schedule: 07:35 - 09:10
            # Evening Schedule: 16:45 - 18:30
            m_stmt = select(TripSchedule).where(
                TripSchedule.bus_id == bus.id,
                TripSchedule.direction == RouteDirection.MORNING
            )
            if not (await db.execute(m_stmt)).scalars().first():
                m_sched = TripSchedule(
                    bus_id=bus.id,
                    route_id=route.id,
                    direction=RouteDirection.MORNING,
                    start_time=time(7, 35),
                    end_time=time(9, 10),
                    active=True
                )
                db.add(m_sched)

            e_stmt = select(TripSchedule).where(
                TripSchedule.bus_id == bus.id,
                TripSchedule.direction == RouteDirection.EVENING
            )
            if not (await db.execute(e_stmt)).scalars().first():
                e_sched = TripSchedule(
                    bus_id=bus.id,
                    route_id=route.id,
                    direction=RouteDirection.EVENING,
                    start_time=time(16, 45),
                    end_time=time(18, 30),
                    active=True
                )
                db.add(e_sched)

        await db.commit()
        logger.info("Successfully seeded Phase 2 tracking foundation data!")

if __name__ == "__main__":
    asyncio.run(seed_tracking_data())
