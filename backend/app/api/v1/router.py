from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.tracking import router as tracking_router
from app.api.v1.alerts import router as alerts_router
from app.api.v1.emergencies import router as emergencies_router
from app.api.v1.analytics import router as analytics_router
from app.api.v1.buses import router as buses_router
from app.api.v1.routes import stops_router, routes_router
from app.api.v1.drivers import router as drivers_router
from app.api.v1.schedules import schedules_router, trips_router
from app.api.v1.notifications import router as notifications_router
from app.api.v1.students import router as students_router
from app.api.v1.parents import router as parents_router
from app.api.v1.parents_public import router as parents_public_router
from app.api.v1.parents_me import router as parents_me_router

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(auth_router)
api_v1_router.include_router(tracking_router)
api_v1_router.include_router(alerts_router)
api_v1_router.include_router(emergencies_router)
api_v1_router.include_router(analytics_router)
# Phase 2 — Transport Foundation
api_v1_router.include_router(buses_router)
api_v1_router.include_router(stops_router)
api_v1_router.include_router(routes_router)
api_v1_router.include_router(drivers_router)
api_v1_router.include_router(schedules_router)
api_v1_router.include_router(trips_router)
api_v1_router.include_router(notifications_router)
api_v1_router.include_router(students_router)
api_v1_router.include_router(parents_router)
api_v1_router.include_router(parents_public_router)

api_v1_router.include_router(parents_me_router)
