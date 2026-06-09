from collections.abc import AsyncGenerator
from typing import Any

from redis.asyncio import Redis, from_url

from app.core.config import settings

redis_client: Redis | None = None


async def init_redis() -> None:
    global redis_client
    redis_client = await from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
    )


async def close_redis() -> None:
    global redis_client
    if redis_client is not None:
        await redis_client.close()
        redis_client = None


async def get_redis() -> AsyncGenerator[Redis, None]:
    if redis_client is None:
        await init_redis()
    try:
        yield redis_client
    finally:
        pass
