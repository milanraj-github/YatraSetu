from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    """Schema for health-check endpoint response."""

    status: str
    service: str


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Service Health Check",
    description="Check the operational status of the SMARTBUS backend service.",
)
async def health_check() -> HealthResponse:
    """Return the health status of the backend service."""
    return HealthResponse(
        status="healthy",
        service="smartbus-backend",
    )
