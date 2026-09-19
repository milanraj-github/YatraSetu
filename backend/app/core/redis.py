import logging
from typing import AsyncGenerator, Optional
import redis.asyncio as aioredis
from redis.asyncio import Redis

from app.core.config import settings

logger = logging.getLogger(__name__)

_redis_client: Optional[Redis] = None


def get_redis_client() -> Redis:
    """Return or initialize the singleton Redis client instance with connection pooling."""
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=2.0,
            socket_timeout=2.0,
        )
    return _redis_client


def set_redis_client(client: Optional[Redis]) -> None:
    """Set or override the global Redis client instance (useful for test isolation)."""
    global _redis_client
    _redis_client = client


async def get_redis() -> AsyncGenerator[Redis, None]:
    """FastAPI dependency for accessing the shared Redis client."""
    client = get_redis_client()
    yield client


async def close_redis() -> None:
    """Gracefully close the Redis client connection pool."""
    global _redis_client
    if _redis_client is not None:
        try:
            await _redis_client.aclose()
        except Exception as exc:
            logger.warning(f"Error closing Redis client: {exc}")
        finally:
            _redis_client = None


async def check_redis_connection() -> bool:
    """Ping Redis to verify reachability for health checks."""
    try:
        client = get_redis_client()
        pong = await client.ping()
        return pong is True
    except Exception as exc:
        logger.warning(f"Redis connectivity health check failed: {exc}")
        return False
