import json
import logging
from typing import Dict, Any, Optional
import redis.asyncio as aioredis
from app.core.config import settings

logger = logging.getLogger("smartbus.redis")

_redis_client: Optional[aioredis.Redis] = None
_mock_redis_storage: Dict[str, str] = {}

def get_redis_client() -> Optional[aioredis.Redis]:
    global _redis_client
    if settings.REDIS_MOCK_MODE:
        return None
    if _redis_client is None:
        try:
            _redis_client = aioredis.from_url(
                settings.get_redis_url(),
                decode_responses=True
            )
            logger.info("Connected to Redis server.")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            _redis_client = None
    return _redis_client

async def set_redis_json(key: str, data: Dict[str, Any], ttl: Optional[int] = None) -> None:
    client = get_redis_client()
    json_str = json.dumps(data)
    if client:
        try:
            await client.set(key, json_str, ex=ttl)
            return
        except Exception as e:
            logger.error(f"Redis set failed for key '{key}': {e}")
    # Mock fallback
    _mock_redis_storage[key] = json_str

async def get_redis_json(key: str) -> Optional[Dict[str, Any]]:
    client = get_redis_client()
    if client:
        try:
            val = await client.get(key)
            if val:
                return json.loads(val)
            return None
        except Exception as e:
            logger.error(f"Redis get failed for key '{key}': {e}")
    # Mock fallback
    val = _mock_redis_storage.get(key)
    if val:
        return json.loads(val)
    return None

async def delete_redis_key(key: str) -> None:
    client = get_redis_client()
    if client:
        try:
            await client.delete(key)
        except Exception as e:
            logger.error(f"Redis delete failed for key '{key}': {e}")
    _mock_redis_storage.pop(key, None)

def clear_mock_redis() -> None:
    _mock_redis_storage.clear()
