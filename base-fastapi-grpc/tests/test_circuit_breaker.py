from unittest.mock import patch

import pytest

from core.infra.circuit_breaker import (
    MODE_CLOSED,
    MODE_HALF_OPEN,
    MODE_OPEN,
    CircuitBreakerConfig,
    RedisCircuitBreaker,
)


class FakeRedis:
    def __init__(
        self,
        *,
        hget_values=None,
        hget_error: Exception | None = None,
        hincrby_value: int = 1,
    ) -> None:
        self._hget_values = list(hget_values or [])
        self._hget_error = hget_error
        self._hincrby_value = hincrby_value
        self.hsets = []
        self.expires = []

    async def hget(self, *args):
        if self._hget_error is not None:
            raise self._hget_error
        if self._hget_values:
            return self._hget_values.pop(0)
        return None

    async def hincrby(self, **kwargs):
        return self._hincrby_value

    async def hset(self, key, *, mapping):
        self.hsets.append((key, mapping))

    async def expire(self, key, ttl):
        self.expires.append((key, ttl))


def _breaker(fake_redis, config: CircuitBreakerConfig | None = None):
    breaker = RedisCircuitBreaker(
        "svc",
        config or CircuitBreakerConfig(timeout_threshold=3),
    )
    enabled = patch("core.infra.circuit_breaker.RedisCacheClient.is_enabled")
    client = patch("core.infra.circuit_breaker.RedisCacheClient.get_client")
    enabled_mock = enabled.start()
    client_mock = client.start()
    enabled_mock.return_value = True
    client_mock.return_value = fake_redis
    return breaker, enabled, client


def _stop(*patches) -> None:
    for item in patches:
        item.stop()


@pytest.mark.asyncio
async def test_disabled_breaker_allows_and_skips_state_changes():
    breaker = RedisCircuitBreaker(
        "svc",
        CircuitBreakerConfig(enabled=False),
    )

    decision = await breaker.allow_request()
    await breaker.record_timeout()
    await breaker.record_success()

    assert decision.allowed is True
    assert decision.mode == MODE_CLOSED


@pytest.mark.asyncio
async def test_allow_request_closed_mode():
    fake_redis = FakeRedis(hget_values=[None])
    breaker, enabled, client = _breaker(fake_redis)
    try:
        decision = await breaker.allow_request()
    finally:
        _stop(enabled, client)

    assert decision.allowed is True
    assert decision.mode == MODE_CLOSED


@pytest.mark.asyncio
async def test_allow_request_open_mode_before_cooldown_finishes():
    fake_redis = FakeRedis(hget_values=[MODE_OPEN, 2_000])
    breaker, enabled, client = _breaker(fake_redis)
    try:
        with patch.object(breaker, "_now_ms", return_value=1_000):
            decision = await breaker.allow_request()
    finally:
        _stop(enabled, client)

    assert decision.allowed is False
    assert decision.mode == MODE_OPEN


@pytest.mark.asyncio
async def test_allow_request_open_mode_moves_to_half_open():
    fake_redis = FakeRedis(hget_values=[MODE_OPEN, 500], hincrby_value=1)
    breaker, enabled, client = _breaker(fake_redis)
    try:
        with patch.object(breaker, "_now_ms", return_value=1_000):
            decision = await breaker.allow_request()
    finally:
        _stop(enabled, client)

    assert decision.allowed is True
    assert decision.mode == MODE_HALF_OPEN
    assert fake_redis.hsets[0][1]["mode"] == MODE_HALF_OPEN


@pytest.mark.asyncio
async def test_allow_request_half_open_blocks_even_probe():
    fake_redis = FakeRedis(hget_values=[MODE_HALF_OPEN], hincrby_value=2)
    breaker, enabled, client = _breaker(fake_redis)
    try:
        decision = await breaker.allow_request()
    finally:
        _stop(enabled, client)

    assert decision.allowed is False
    assert decision.mode == MODE_HALF_OPEN


@pytest.mark.asyncio
async def test_allow_request_fails_open_when_redis_errors():
    fake_redis = FakeRedis(hget_error=RuntimeError("redis down"))
    breaker, enabled, client = _breaker(fake_redis)
    try:
        decision = await breaker.allow_request()
    finally:
        _stop(enabled, client)

    assert decision.allowed is True
    assert decision.mode == MODE_CLOSED


@pytest.mark.asyncio
async def test_record_timeout_half_open_reopens():
    fake_redis = FakeRedis(hget_values=[MODE_HALF_OPEN])
    breaker, enabled, client = _breaker(fake_redis)
    try:
        with patch.object(breaker, "_now_ms", return_value=1_000):
            await breaker.record_timeout()
    finally:
        _stop(enabled, client)

    assert fake_redis.hsets[0][1]["mode"] == MODE_OPEN
    assert fake_redis.expires[0][1] == 120


@pytest.mark.asyncio
async def test_record_timeout_keeps_closed_below_threshold():
    fake_redis = FakeRedis(hget_values=[MODE_CLOSED, 0, 0])
    breaker, enabled, client = _breaker(fake_redis)
    try:
        with patch.object(breaker, "_now_ms", return_value=100_000):
            await breaker.record_timeout()
    finally:
        _stop(enabled, client)

    assert fake_redis.hsets[0][1]["mode"] == MODE_CLOSED
    assert fake_redis.hsets[0][1]["failure_count"] == 1


@pytest.mark.asyncio
async def test_record_timeout_opens_at_threshold():
    fake_redis = FakeRedis(hget_values=[MODE_CLOSED, 900, 2])
    breaker, enabled, client = _breaker(fake_redis)
    try:
        with patch.object(breaker, "_now_ms", return_value=1_000):
            await breaker.record_timeout()
    finally:
        _stop(enabled, client)

    assert fake_redis.hsets[0][1]["mode"] == MODE_OPEN
    assert fake_redis.hsets[0][1]["failure_count"] == 3


@pytest.mark.asyncio
async def test_record_timeout_swallows_redis_error():
    fake_redis = FakeRedis(hget_error=RuntimeError("redis down"))
    breaker, enabled, client = _breaker(fake_redis)
    try:
        await breaker.record_timeout()
    finally:
        _stop(enabled, client)


@pytest.mark.asyncio
async def test_record_success_closed_clears_state():
    fake_redis = FakeRedis(hget_values=[MODE_CLOSED])
    breaker, enabled, client = _breaker(fake_redis)
    try:
        await breaker.record_success()
    finally:
        _stop(enabled, client)

    assert fake_redis.hsets[0][1]["failure_count"] == 0


@pytest.mark.asyncio
async def test_record_success_half_open_waits_for_enough_successes():
    fake_redis = FakeRedis(hget_values=[MODE_HALF_OPEN], hincrby_value=1)
    breaker, enabled, client = _breaker(
        fake_redis,
        CircuitBreakerConfig(half_open_success_threshold=2),
    )
    try:
        await breaker.record_success()
    finally:
        _stop(enabled, client)

    assert fake_redis.hsets == []


@pytest.mark.asyncio
async def test_record_success_half_open_closes_after_threshold():
    fake_redis = FakeRedis(hget_values=[MODE_HALF_OPEN], hincrby_value=2)
    breaker, enabled, client = _breaker(
        fake_redis,
        CircuitBreakerConfig(half_open_success_threshold=2),
    )
    try:
        await breaker.record_success()
    finally:
        _stop(enabled, client)

    assert fake_redis.hsets[0][1]["mode"] == MODE_CLOSED


@pytest.mark.asyncio
async def test_record_success_swallows_redis_error():
    fake_redis = FakeRedis(hget_error=RuntimeError("redis down"))
    breaker, enabled, client = _breaker(fake_redis)
    try:
        await breaker.record_success()
    finally:
        _stop(enabled, client)


def test_helpers():
    breaker = RedisCircuitBreaker(
        "svc",
        CircuitBreakerConfig(timeout_window_seconds=1, open_seconds=2),
    )

    assert breaker._as_int(None) == 0
    assert breaker._as_int("3") == 3
    assert breaker._state_ttl_seconds() == 4
    assert breaker._now_ms() > 0
