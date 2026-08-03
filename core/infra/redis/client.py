from redis.asyncio import ConnectionPool, Redis


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
            cls._client = Redis(connection_pool=cls._pool, decode_responses=True)
        return cls._client

    @classmethod
    async def close(cls) -> None:
        if cls._client is not None:
            await cls._client.aclose()
            cls._client = None
        if cls._pool is not None:
            await cls._pool.disconnect()
            cls._pool = None
