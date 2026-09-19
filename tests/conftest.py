import asyncio
import sys
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.db.database import engine
from app.main import app


@pytest_asyncio.fixture(scope="session", autouse=True)
def setup_windows_asyncio():
    """Configure appropriate event loop policy on Windows for asyncpg."""
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


@pytest_asyncio.fixture(autouse=True)
async def cleanup_db_pool():
    """Clean up engine pool connections between async tests."""
    yield
    await engine.dispose()


@pytest_asyncio.fixture
async def async_client():
    """Async HTTP test client fixture."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
