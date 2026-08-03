from fastapi import FastAPI
from loguru import logger
from redis.asyncio import ConnectionPool

from app.settings import settings
from core.infra.redis.client import RedisCacheClient


def init_redis(app: FastAPI | None = None) -> None:  # pragma: no cover
    """
    Creates connection pool for redis.

    :param app: current fastapi application.
    """
    if not settings.redis_url:
        RedisCacheClient.bind_pool(None)
        if app:
            app.state.redis_pool = None
            app.state.redis_client = None
        return

    redis_pool = ConnectionPool.from_url(
        str(settings.redis_url),
        decode_responses=True,
    )
    RedisCacheClient.bind_pool(redis_pool)
    logger.info("Redis initialized")
    if app:
        app.state.redis_pool = redis_pool
        app.state.redis_client = RedisCacheClient.get_client()


async def shutdown_redis_client(app: FastAPI | None = None) -> None:
    if app:
        app.state.redis_pool = None
        app.state.redis_client = None
    await RedisCacheClient.close()
