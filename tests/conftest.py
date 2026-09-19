import asyncio
import json
import sys
from unittest.mock import patch
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.db.database import engine
from app.main import app


class FakeAsyncRedis:
    """In-memory Redis client implementation for unit & integration testing."""

    def __init__(self):
        self._store = {}
        self.is_healthy = True

    async def ping(self):
        if not self.is_healthy:
            raise ConnectionError("Simulated Redis connection failure")
        return True

    async def get(self, key: str):
        if not self.is_healthy:
            raise ConnectionError("Simulated Redis connection failure")
        return self._store.get(key)

    async def set(self, key: str, value: str):
        if not self.is_healthy:
            raise ConnectionError("Simulated Redis connection failure")
        self._store[key] = value
        return True

    async def delete(self, *keys: str):
        if not self.is_healthy:
            raise ConnectionError("Simulated Redis connection failure")
        count = 0
        for k in keys:
            if k in self._store:
                del self._store[k]
                count += 1
        return count

    async def eval(self, script: str, numkeys: int, key: str, data_json: str, new_epoch_str: str):
        if not self.is_healthy:
            raise ConnectionError("Simulated Redis connection failure")
        new_epoch = float(new_epoch_str)
        current = self._store.get(key)
        if current:
            current_obj = json.loads(current)
            current_epoch = float(current_obj.get("recorded_at_epoch", 0))
            if new_epoch >= current_epoch:
                self._store[key] = data_json
                return 1
            else:
                return 0
        else:
            self._store[key] = data_json
            return 1

    async def aclose(self):
        self._store.clear()


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


@pytest.fixture
def fake_redis():
    """Fixture providing a fresh in-memory Redis test client."""
    client = FakeAsyncRedis()
    with patch("app.core.redis.get_redis_client", return_value=client), \
         patch("app.services.gps_service.get_redis_client", return_value=client):
        yield client


@pytest_asyncio.fixture(autouse=True)
def auto_mock_redis():
    """Autouse fixture ensuring Redis is safely mocked for all tests by default."""
    client = FakeAsyncRedis()
    with patch("app.core.redis.get_redis_client", return_value=client), \
         patch("app.services.gps_service.get_redis_client", return_value=client):
        yield client


@pytest_asyncio.fixture
async def async_client():
    """Async HTTP test client fixture."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
