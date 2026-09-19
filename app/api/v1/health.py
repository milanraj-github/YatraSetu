import logging
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import check_redis_connection
from app.db.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    """Schema for general health-check response."""

    status: str
    service: str


class DatabaseHealthResponse(BaseModel):
    """Schema for database health-check response."""

    status: str
    database: str


class RedisHealthResponse(BaseModel):
    """Schema for Redis health-check response."""

    status: str
    service: str


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Service Health Check",
    description="Check the operational status of the SMARTBUS backend service.",
)
async def health_check() -> HealthResponse:
    """Return the general health status of the backend service."""
    return HealthResponse(
        status="healthy",
        service="smartbus-backend",
    )


@router.get(
    "/health/db",
    response_model=DatabaseHealthResponse,
    summary="Database Health Check",
    description="Check connectivity to the PostgreSQL database by executing SELECT 1.",
)
async def database_health_check(
    db: AsyncSession = Depends(get_db),
) -> DatabaseHealthResponse:
    """Execute SELECT 1 to verify database reachability."""
    try:
        result = await db.execute(text("SELECT 1"))
        scalar = result.scalar()
        if scalar != 1:
            raise ValueError("Unexpected query result from database")
        return DatabaseHealthResponse(
            status="healthy",
            database="connected",
        )
    except Exception as exc:
        logger.error(f"Database health check failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service unavailable",
        )


@router.get(
    "/health/redis",
    response_model=RedisHealthResponse,
    summary="Redis Health Check",
    description="Check connectivity to the Redis server by executing PING.",
)
async def redis_health_check() -> RedisHealthResponse:
    """Ping Redis to verify reachability."""
    is_healthy = await check_redis_connection()
    if not is_healthy:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis service unavailable",
        )
    return RedisHealthResponse(
        status="ok",
        service="redis",
    )
