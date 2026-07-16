from loguru import logger
from redis.asyncio import ConnectionPool, Redis

from app.settings import settings


class RedisCacheClient:
    """
    Process-level Redis accessor for code paths without FastAPI Request.
    """

    _pool: ConnectionPool | None = None
    _client: Redis | None = None

    @classmethod
    def bind_pool(cls, pool: ConnectionPool | None) -> None:
        cls._pool = pool
        cls._client = None

    @classmethod
    def is_enabled(cls) -> bool:
        return cls._pool is not None

    @classmethod
    def get_client(cls) -> Redis:
        if cls._pool is None:
            raise RuntimeError("Redis not initialized")
        if cls._client is None:
            cls._client = Redis(connection_pool=cls._pool)
        return cls._client

    @classmethod
    async def close(cls) -> None:
        if cls._client is not None:
            await cls._client.aclose()
            cls._client = None
        if cls._pool is not None:
            await cls._pool.disconnect()
            cls._pool = None


def init_redis() -> None:  # pragma: no cover
    """
    Creates connection pool for redis.

    :param app: current fastapi application.
    """
    if not settings.redis_url:
        RedisCacheClient.bind_pool(None)
        return

    RedisCacheClient.bind_pool(
        ConnectionPool.from_url(
            str(settings.redis_url),
            decode_responses=True,
        ),
    )
    logger.info("Redis initialized")


async def shutdown_redis_client() -> None:
    await RedisCacheClient.close()
