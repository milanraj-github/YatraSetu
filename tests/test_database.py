import pytest
from httpx import AsyncClient
from sqlalchemy import text

from app.db.base import Base
from app.db.database import async_session_factory


@pytest.mark.asyncio
async def test_database_health_endpoint(async_client: AsyncClient):
    """Test GET /api/v1/health/db returns 200 and database connected."""
    response = await async_client.get("/api/v1/health/db")
    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "database": "connected",
    }


@pytest.mark.asyncio
async def test_direct_database_query():
    """Test direct SQL execution via AsyncSession."""
    async with async_session_factory() as session:
        result = await session.execute(text("SELECT 1"))
        scalar = result.scalar()
        assert scalar == 1


@pytest.mark.asyncio
async def test_alembic_version_table_exists():
    """Verify that Alembic migration tracking table exists in PostgreSQL."""
    async with async_session_factory() as session:
        result = await session.execute(
            text(
                "SELECT EXISTS ("
                "  SELECT FROM information_schema.tables "
                "  WHERE table_schema = 'public' AND table_name = 'alembic_version'"
                ");"
            )
        )
        exists = result.scalar()
        assert exists is True


def test_declarative_base_initialized():
    """Verify that Base is a valid DeclarativeBase with clean metadata."""
    assert hasattr(Base, "metadata")
    assert hasattr(Base, "registry")
