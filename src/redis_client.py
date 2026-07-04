from functools import lru_cache

from redis import asyncio as redis

from .config import get_settings


@lru_cache
def get_redis_pool() -> redis.Redis:
    settings = get_settings()
    # protocol=2 (RESP2): redis-py defaults to attempting a RESP3 handshake
    # (HELLO), which Redis <6 doesn't understand — pin RESP2 for broad compatibility.
    return redis.from_url(settings.redis_url, decode_responses=True, protocol=2)
