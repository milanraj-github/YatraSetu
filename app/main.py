from fastapi import FastAPI
from pydantic import BaseModel

from app.api.v1.auth import router as auth_router
from app.api.v1.boarding_points import router as boarding_points_router
from app.api.v1.buses import router as buses_router
from app.api.v1.drivers import router as drivers_router
from app.api.v1.gps import router as gps_router
from app.api.v1.health import router as health_router
from app.api.v1.parent_links import router as parent_links_router
from app.api.v1.parents import router as parents_router
from app.api.v1.rbac import router as rbac_router
from app.api.v1.routes import router as routes_router
from app.api.v1.trips import router as trips_router
from app.api.v1.ws import router as ws_router
from app.core.config import settings


class RootResponse(BaseModel):
    """Schema for root endpoint response."""

    message: str


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Campus Bus Tracking, Safety & Emergency Backend API",
    debug=settings.DEBUG,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Include v1 routers with versioned prefix
app.include_router(health_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(rbac_router, prefix="/api/v1")
app.include_router(buses_router, prefix="/api/v1")
app.include_router(routes_router, prefix="/api/v1")
app.include_router(boarding_points_router, prefix="/api/v1")
app.include_router(drivers_router, prefix="/api/v1")
app.include_router(trips_router, prefix="/api/v1")
app.include_router(gps_router, prefix="/api/v1")
app.include_router(ws_router, prefix="/api/v1")
app.include_router(parent_links_router, prefix="/api/v1")
app.include_router(parents_router, prefix="/api/v1")



@app.get(
    "/",
    response_model=RootResponse,
    tags=["Root"],
    summary="Root Endpoint",
    description="Root welcome endpoint verifying server status.",
)
async def root() -> RootResponse:
    """Root endpoint welcoming and verifying server status."""
    return RootResponse(message="SMARTBUS Backend is running")
