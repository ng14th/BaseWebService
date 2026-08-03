import httpx
from loguru import logger

from app.settings import settings


class HttpClientManager:
    _client: httpx.AsyncClient | None = None

    @classmethod
    def _create_client(cls) -> httpx.AsyncClient:
        logger.info("Initializing global HTTP client pool")
        return httpx.AsyncClient(
            limits=httpx.Limits(
                max_connections=settings.http_max_connections,
                max_keepalive_connections=settings.http_max_keepalive_connections,
            ),
            timeout=httpx.Timeout(
                connect=5.0,
                read=10.0,
                write=5.0,
                pool=settings.http_pool_timeout_seconds,
            ),
            trust_env=False,
        )

    @classmethod
    async def initialize(cls) -> None:
        if cls._client is None:
            cls._client = cls._create_client()

    @classmethod
    def get_client(cls) -> httpx.AsyncClient:
        if cls._client is None:
            cls._client = cls._create_client()

        return cls._client

    @classmethod
    async def close_client(cls) -> None:
        if cls._client is not None:
            logger.info("Closing global HTTP client pool")
            await cls._client.aclose()
            cls._client = None
