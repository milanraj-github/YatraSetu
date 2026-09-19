import asyncio
import json
import sys
from unittest.mock import patch
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from starlette.websockets import WebSocketDisconnect

from app.core.redis import set_redis_client
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

    async def set(
        self,
        key: str,
        value: str,
        ex: int | None = None,
        px: int | None = None,
        nx: bool = False,
        xx: bool = False,
        **kwargs,
    ):
        if not self.is_healthy:
            raise ConnectionError("Simulated Redis connection failure")
        if nx and key in self._store:
            return None
        if xx and key not in self._store:
            return None
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

    async def eval(self, script: str, numkeys: int, *args):
        if not self.is_healthy:
            raise ConnectionError("Simulated Redis connection failure")
        keys = args[:numkeys]
        argv = args[numkeys:]
        key = keys[0]
        data_json = argv[0]
        new_epoch = float(argv[1])
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


class ASGIWebSocketTestSession:
    """In-memory asyncio-native WebSocket test session for ASGI applications."""

    def __init__(self, application, path: str, headers: dict = None, query_params: dict = None):
        self.application = application
        self.path = path
        self.headers = headers or {}
        self.query_params = query_params or {}
        self.incoming_queue = asyncio.Queue()
        self.outgoing_queue = asyncio.Queue()
        self.task = None
        self.close_code = None

    async def __aenter__(self):
        raw_headers = [(k.lower().encode("ascii"), v.encode("ascii")) for k, v in self.headers.items()]
        query_string = "&".join(f"{k}={v}" for k, v in self.query_params.items()).encode("ascii")
        scope = {
            "type": "websocket",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "scheme": "ws",
            "path": self.path,
            "raw_path": self.path.encode("ascii"),
            "query_string": query_string,
            "headers": raw_headers,
            "client": ("127.0.0.1", 50000),
            "server": ("testserver", 80),
            "subprotocols": [],
        }

        async def receive():
            return await self.incoming_queue.get()

        async def send(message):
            if message["type"] == "websocket.close":
                self.close_code = message.get("code", 1000)
            await self.outgoing_queue.put(message)

        self.task = asyncio.create_task(self.application(scope, receive, send))
        await self.incoming_queue.put({"type": "websocket.connect"})

        msg = await self.outgoing_queue.get()
        if msg["type"] == "websocket.close":
            self.close_code = msg.get("code", 1000)
            raise WebSocketDisconnect(code=self.close_code)
        elif msg["type"] == "websocket.accept":
            return self
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.incoming_queue.put({"type": "websocket.disconnect", "code": 1000})
        if self.task:
            try:
                await asyncio.wait_for(self.task, timeout=1.0)
            except Exception:
                self.task.cancel()

    async def receive_json(self, timeout: float = 2.0) -> dict:
        msg = await asyncio.wait_for(self.outgoing_queue.get(), timeout=timeout)
        if msg["type"] == "websocket.close":
            self.close_code = msg.get("code", 1000)
            raise WebSocketDisconnect(code=self.close_code)
        if msg["type"] == "websocket.send":
            text = msg.get("text")
            if text is not None:
                return json.loads(text)
            return msg.get("bytes")
        return msg

    async def send_text(self, text: str):
        await self.incoming_queue.put({"type": "websocket.receive", "text": text})

    async def send_json(self, data: dict):
        await self.incoming_queue.put({"type": "websocket.receive", "text": json.dumps(data)})


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
    set_redis_client(client)
    yield client
    set_redis_client(None)


@pytest_asyncio.fixture(autouse=True)
def auto_mock_redis():
    """Autouse fixture ensuring Redis is safely mocked for all tests by default."""
    client = FakeAsyncRedis()
    set_redis_client(client)
    yield client
    set_redis_client(None)


@pytest_asyncio.fixture
async def async_client():
    """Async HTTP test client fixture."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
