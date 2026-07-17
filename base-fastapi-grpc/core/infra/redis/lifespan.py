from fastapi import FastAPI
from loguru import logger
from redis.asyncio import ConnectionPool

from core.infra.redis.client import RedisCacheClient
from app.settings import settings


def init_redis(app: FastAPI) -> None:  # pragma: no cover
    """
    Creates connection pool for redis.

    :param app: current fastapi application.
    """
    app.state.redis_pool = ConnectionPool.from_url(
        str(settings.redis_url),
        decode_responses=True,
    )
    RedisCacheClient.bind_pool(app.state.redis_pool)
    logger.info("Redis initialized")


async def shutdown_redis(app: FastAPI) -> None:  # pragma: no cover
    """
    Closes redis connection pool.

    :param app: current FastAPI app.
    """
    await RedisCacheClient.close()
