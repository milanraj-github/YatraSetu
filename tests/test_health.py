import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_root_endpoint(async_client: AsyncClient):
    """Test GET / returns 200 and expected welcome message."""
    response = await async_client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "SMARTBUS Backend is running"}


@pytest.mark.asyncio
async def test_health_endpoint(async_client: AsyncClient):
    """Test GET /api/v1/health returns 200 and expected health payload."""
    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "service": "smartbus-backend",
    }
