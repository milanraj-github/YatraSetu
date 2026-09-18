import os
import sys
import pytest
import pytest_asyncio
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport

os.environ["FIREBASE_MOCK_MODE"] = "True"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.core.firebase import clear_mock_firebase_tokens

import asyncio
from app.core.database import engine

@pytest_asyncio.fixture(autouse=True)
async def prepare_test_environment():
    clear_mock_firebase_tokens()
    yield
    clear_mock_firebase_tokens()
    await engine.dispose()

@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


