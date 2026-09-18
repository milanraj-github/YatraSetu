from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.tracking import router as tracking_router
from app.api.v1.buses import router as buses_router
from app.api.v1.routes import stops_router, routes_router
from app.api.v1.drivers import router as drivers_router
from app.api.v1.schedules import schedules_router, trips_router

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(auth_router)
api_v1_router.include_router(tracking_router)
# Phase 2 — Transport Foundation
api_v1_router.include_router(buses_router)
api_v1_router.include_router(stops_router)
api_v1_router.include_router(routes_router)
api_v1_router.include_router(drivers_router)
api_v1_router.include_router(schedules_router)
api_v1_router.include_router(trips_router)
