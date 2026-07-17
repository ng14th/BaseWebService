from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, Request
from redis.asyncio import ConnectionPool

from core.infra.redis.client import RedisCacheClient, init_redis, shutdown_redis_client
from core.infra.redis.dependency import get_redis_pool
from app.settings import settings


def test_redis_cache_client_bind_pool():
    pool = MagicMock(spec=ConnectionPool)
    RedisCacheClient.bind_pool(pool)
    assert RedisCacheClient.is_enabled() is True
    assert RedisCacheClient._pool is pool
    assert RedisCacheClient._client is None

    RedisCacheClient.bind_pool(None)
    assert RedisCacheClient.is_enabled() is False


@pytest.mark.asyncio
async def test_redis_cache_client_get_and_close():
    RedisCacheClient.bind_pool(None)
    with pytest.raises(RuntimeError):
        RedisCacheClient.get_client()

    pool = AsyncMock(spec=ConnectionPool)
    pool.connection_kwargs = {}
    RedisCacheClient.bind_pool(pool)

    # First get creates client
    client1 = RedisCacheClient.get_client()
    # Second get returns same client
    client2 = RedisCacheClient.get_client()
    assert client1 is client2

    # Mock aclose on the client
    client1.aclose = AsyncMock()

    # Close should clean up both
    await shutdown_redis_client()
    assert RedisCacheClient._client is None
    assert RedisCacheClient._pool is None
    client1.aclose.assert_awaited_once()
    pool.disconnect.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_redis_pool():
    request = MagicMock(spec=Request)
    app = MagicMock()
    pool = MagicMock(spec=ConnectionPool)
    app.state.redis_pool = pool
    request.app = app

    gen = await get_redis_pool(request)
    assert gen is pool
