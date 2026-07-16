import time
from collections import deque
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, Request

from app.api.common.rate_limit import (
    RateLimitExceeded,
    RateLimitResult,
    RedisSlidingWindowRateLimiter,
    _build_sliding_window_result,
    _check_client_id_limit,
    _check_ip_limit,
    _get_client_id_identifier,
    _get_client_ip,
    _rate_limit_request_scope,
    _redis_reset_after_seconds,
    _redis_retry_after_seconds,
    _trim_window,
    _validate_window_config,
    _window_reset_after_seconds,
    _window_ttl_seconds,
    get_rate_limiter_store,
    init_rate_limiter,
    rate_limit,
)


@pytest.fixture
def mock_request():
    request = MagicMock(spec=Request)
    request.headers = {}
    request.client = MagicMock()
    request.client.host = "127.0.0.1"
    request.method = "GET"
    request.url.path = "/test"
    request.scope = {"route": MagicMock(path="/test")}
    request.app = MagicMock(spec=FastAPI)
    request.app.state = MagicMock()
    return request


def test_validate_window_config():
    with pytest.raises(ValueError):
        _validate_window_config(limit=0, window_seconds=10)
    with pytest.raises(ValueError):
        _validate_window_config(limit=10, window_seconds=0)
    _validate_window_config(limit=10, window_seconds=10)


def test_window_ttl_seconds():
    assert _window_ttl_seconds(10) == 20
    assert _window_ttl_seconds(0) == 1


def test_trim_window():
    requests = deque([1.0, 2.0, 3.0, 4.0])
    _trim_window(requests, 2.0)
    assert list(requests) == [3.0, 4.0]


def test_window_reset_after_seconds():
    assert _window_reset_after_seconds(deque(), 10.0, 60) == 0
    assert _window_reset_after_seconds(deque([5.0]), 10.0, 60) == 55


def test_redis_retry_after_seconds():
    assert (
        _redis_retry_after_seconds(oldest_score=None, now_ms=10000, window_ms=60000)
        == 1
    )  # noqa: E501
    assert (
        _redis_retry_after_seconds(oldest_score=5000, now_ms=10000, window_ms=60000)
        == 55
    )  # noqa: E501


def test_redis_reset_after_seconds():
    assert (
        _redis_reset_after_seconds(oldest_score=None, now_ms=10000, window_ms=60000)
        == 0
    )  # noqa: E501
    assert (
        _redis_reset_after_seconds(oldest_score=5000, now_ms=10000, window_ms=60000)
        == 55
    )  # noqa: E501


def test_build_sliding_window_result():
    res = _build_sliding_window_result(
        limit=10,
        window_seconds=60,
        retry_after_seconds=5,
        request_count=5,
        reset_after_seconds=10,
        exceeded=False,
    )
    assert res.remaining == 5
    assert res.exceeded is False

    res_exceeded = _build_sliding_window_result(
        limit=10,
        window_seconds=60,
        retry_after_seconds=5,
        request_count=10,
        reset_after_seconds=10,
        exceeded=True,
    )
    assert res_exceeded.remaining == 0
    assert res_exceeded.exceeded is True


def test_rate_limit_exceeded_exception():
    res = RateLimitResult(10, 60, 5, 0, int(time.time()), True)
    exc = RateLimitExceeded("ip", res)
    assert exc.headers["Retry-After"] == "5"
    assert exc.headers["X-RateLimit-Scope"] == "ip"
    assert exc.extra["limit"] == 10


@pytest.mark.asyncio
async def test_redis_rate_limiter():
    mock_redis = AsyncMock()
    mock_pipe = AsyncMock()
    mock_pipe.multi = MagicMock()
    mock_pipe.zadd = MagicMock()
    mock_pipe.expire = MagicMock()

    class AsyncContextManagerMock:
        async def __aenter__(self):
            return mock_pipe

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    mock_redis.pipeline = MagicMock(return_value=AsyncContextManagerMock())

    mock_pipe.zcard.return_value = 1
    mock_pipe.zrange.return_value = [("uuid", time.time() * 1000)]

    limiter = RedisSlidingWindowRateLimiter(mock_redis)

    # Test not exceeded
    res = await limiter.hit("test_key", limit=2, window_seconds=60)
    assert not res.exceeded
    assert res.remaining == 0

    # Test exceeded
    mock_pipe.zcard.return_value = 2
    res_exceeded = await limiter.hit("test_key", limit=2, window_seconds=60)
    assert res_exceeded.exceeded

    # Test oldest_score None (empty zrange)
    mock_pipe.zcard.return_value = 0
    mock_pipe.zrange.return_value = []
    res_empty = await limiter.hit("test_key_empty", limit=2, window_seconds=60)
    assert not res_empty.exceeded

    # Test WatchError retry
    from redis.exceptions import WatchError

    mock_pipe.execute = AsyncMock(side_effect=[WatchError("watch error"), None])
    mock_pipe.zcard.return_value = 0
    mock_pipe.zrange.return_value = []
    res_watch = await limiter.hit("test_key_watch", limit=2, window_seconds=60)
    assert not res_watch.exceeded
    assert mock_pipe.execute.call_count == 2

    # Test WatchError raise (exceed retries)
    with patch("app.api.common.rate_limit.settings") as mock_settings:
        mock_settings.rate_limit_watch_retries = 2
        mock_pipe.execute = AsyncMock(side_effect=WatchError("watch error"))
        with pytest.raises(WatchError):
            await limiter.hit("test_key_watch_fail", limit=2, window_seconds=60)


def test_init_rate_limiter():
    app = MagicMock(spec=FastAPI)
    app.state = MagicMock()

    with patch("app.api.common.rate_limit.settings") as mock_settings:
        mock_settings.rate_limit_enabled = False
        init_rate_limiter(app)
        assert app.state.rate_limiter_store is None

        mock_settings.rate_limit_enabled = True
        app.state.redis_pool = None
        with pytest.raises(RuntimeError):
            init_rate_limiter(app)

        app.state.redis_pool = MagicMock()
        init_rate_limiter(app)
        assert isinstance(app.state.rate_limiter_store, RedisSlidingWindowRateLimiter)


def test_get_rate_limiter_store(mock_request):
    with pytest.raises(RuntimeError):
        mock_request.app.state.rate_limiter_store = None
        get_rate_limiter_store(mock_request)

    store = RedisSlidingWindowRateLimiter(MagicMock())
    mock_request.app.state.rate_limiter_store = store
    assert get_rate_limiter_store(mock_request) == store
def test_get_client_ip(mock_request):
    mock_request.headers = {"x-forwarded-for": "10.0.0.1, 10.0.0.2"}
    assert _get_client_ip(mock_request, trust_proxy_headers=True) == "10.0.0.1"

    mock_request.headers = {"x-real-ip": "10.0.0.3"}
    assert _get_client_ip(mock_request, trust_proxy_headers=True) == "10.0.0.3"

    mock_request.headers = {}
    assert _get_client_ip(mock_request, trust_proxy_headers=False) == "127.0.0.1"

    with patch("app.api.common.rate_limit.settings") as mock_settings:
        # Test untrusted proxy IP
        mock_settings.trusted_proxy_ips = ["192.168.1.1"]
        mock_request.client.host = "10.0.0.5"  # Not in trusted proxy IPs
        mock_request.headers = {"x-forwarded-for": "10.0.0.1"}
        assert _get_client_ip(mock_request, trust_proxy_headers=True) == "10.0.0.5"


def test_get_client_id_identifier(mock_request):
    mock_request.headers = {"x-client-id": "client_abc"}
    assert (
        _get_client_id_identifier(request=mock_request, client_id_header="X-Client-ID")
        == "client_abc"
    )  # noqa: E501

    mock_request.headers = {}
    assert (
        _get_client_id_identifier(request=mock_request, client_id_header="X-Client-ID")
        is None
    )  # noqa: E501

    # Test max length limit
    with patch("app.api.common.rate_limit.settings") as mock_settings:
        mock_settings.rate_limit_max_identifier_length = 5
        mock_request.headers = {"x-client-id": "too_long_identifier"}
        assert (
            _get_client_id_identifier(
                request=mock_request, client_id_header="X-Client-ID"
            )
            is None
        )


def test_rate_limit_request_scope(mock_request):
    assert _rate_limit_request_scope(mock_request) == "GET:/test"
    del mock_request.scope["route"]
    assert _rate_limit_request_scope(mock_request) == "GET:/test"


@pytest.mark.asyncio
async def test_check_ip_limit(mock_request):
    mock_request.app.state.rate_limiter_store = AsyncMock()
    mock_request.app.state.rate_limiter_store.hit.return_value = RateLimitResult(
        10, 60, 0, 9, int(time.time()), False
    )  # noqa: E501

    await _check_ip_limit(
        request=mock_request, limit=10, window_seconds=60, trust_proxy_headers=False
    )  # noqa: E501

    mock_request.app.state.rate_limiter_store.hit.return_value = RateLimitResult(
        10, 60, 5, 0, int(time.time()), True
    )  # noqa: E501
    with pytest.raises(RateLimitExceeded):
        await _check_ip_limit(
            request=mock_request, limit=10, window_seconds=60, trust_proxy_headers=False
        )  # noqa: E501

    # Missing IP returns early
    mock_request.client = None
    await _check_ip_limit(
        request=mock_request, limit=10, window_seconds=60, trust_proxy_headers=False
    )  # noqa: E501


@pytest.mark.asyncio
async def test_check_client_id_limit(mock_request):
    mock_request.headers = {"x-client-id": "client_abc"}
    mock_request.app.state.rate_limiter_store = AsyncMock()
    mock_request.app.state.rate_limiter_store.hit.return_value = RateLimitResult(
        10, 60, 0, 9, int(time.time()), False
    )  # noqa: E501

    await _check_client_id_limit(
        request=mock_request,
        limit=10,
        window_seconds=60,
        client_id_header="X-Client-ID",
    )  # noqa: E501

    mock_request.app.state.rate_limiter_store.hit.return_value = RateLimitResult(
        10, 60, 5, 0, int(time.time()), True
    )  # noqa: E501
    with pytest.raises(RateLimitExceeded):
        await _check_client_id_limit(
            request=mock_request,
            limit=10,
            window_seconds=60,
            client_id_header="X-Client-ID",
        )  # noqa: E501

    # Missing Client ID returns early
    mock_request.headers = {}
    await _check_client_id_limit(
        request=mock_request,
        limit=10,
        window_seconds=60,
        client_id_header="X-Client-ID",
    )  # noqa: E501


@pytest.mark.asyncio
async def test_rate_limit_dependency(mock_request):
    with patch("app.api.common.rate_limit.settings") as mock_settings:
        mock_settings.rate_limit_enabled = False
        dep = rate_limit()
        await dep(mock_request)

        mock_settings.rate_limit_enabled = True
        mock_settings.rate_limit_by_ip_enabled = True
        mock_settings.rate_limit_ip_requests = 10
        mock_settings.rate_limit_ip_window_seconds = 60
        mock_settings.rate_limit_trust_proxy_headers = False
        mock_settings.rate_limit_by_client_id_enabled = True
        mock_settings.rate_limit_client_id_requests = 10
        mock_settings.rate_limit_client_id_window_seconds = 60
        mock_settings.rate_limit_client_id_header = "x-client-id"

        mock_request.headers = {"x-client-id": "abc"}
        mock_request.app.state.rate_limiter_store = AsyncMock()
        mock_request.app.state.rate_limiter_store.hit.return_value = RateLimitResult(
            10, 60, 0, 9, int(time.time()), False
        )  # noqa: E501

        dep = rate_limit()
        await dep(mock_request)
