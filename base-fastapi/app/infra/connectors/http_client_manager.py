import httpx
from loguru import logger

from app.settings import settings


class HttpClientManager:
    _client: httpx.AsyncClient | None = None

    @classmethod
    def get_client(cls) -> httpx.AsyncClient:
        if cls._client is None:
            logger.info("Initializing global HTTP client pool")
            limits = httpx.Limits(
                max_connections=settings.http_max_connections,
                max_keepalive_connections=settings.http_max_keepalive_connections,
            )
            cls._client = httpx.AsyncClient(
                limits=limits,
                timeout=httpx.Timeout(
                    connect=5.0,
                    read=10.0,
                    write=5.0,
                    pool=settings.http_pool_timeout_seconds,
                ),
            )
        return cls._client

    @classmethod
    async def close_client(cls) -> None:
        if cls._client is not None:
            logger.info("Closing global HTTP client pool")
            await cls._client.aclose()
            cls._client = None
