from __future__ import annotations

import time
from dataclasses import dataclass

from loguru import logger

from app.settings import settings
from core.infra.redis.client import RedisCacheClient

MODE_CLOSED = "closed"
MODE_OPEN = "open"
MODE_HALF_OPEN = "half_open"


@dataclass(frozen=True)
class CircuitBreakerConfig:
    """Thresholds controlling the circuit-breaker state transitions.

    enabled: Disable the breaker without removing the integration.
    timeout_threshold: Number of consecutive timeouts needed to open it.
    timeout_window_seconds: Timeout counter is reset after this idle period.
    open_seconds: Time to block all requests before trying recovery.
    half_open_success_threshold: Successful probe requests needed to close it.
    """

    enabled: bool = settings.circuit_breaker_enabled
    timeout_threshold: int = settings.circuit_breaker_timeout_threshold
    timeout_window_seconds: int = settings.circuit_breaker_timeout_window_seconds
    open_seconds: int = settings.circuit_breaker_open_seconds
    half_open_success_threshold: int = (
        settings.circuit_breaker_half_open_success_threshold
    )


@dataclass(frozen=True)
class CircuitBreakerDecision:
    allowed: bool
    mode: str


class RedisCircuitBreaker:
    """Distributed timeout circuit breaker for one downstream service."""

    def __init__(self, service_name: str, config: CircuitBreakerConfig) -> None:
        self._key = f"circuit-breaker:provider:{service_name}"
        self._config = config

    @property
    def redis(self):
        return RedisCacheClient.get_client()

    async def allow_request(self) -> CircuitBreakerDecision:
        # When disabled or Redis is not initialized, keep provider traffic available.
        if not self._is_enabled():
            return CircuitBreakerDecision(allowed=True, mode=MODE_CLOSED)

        try:
            cached_mode = await self.redis.hget(self._key, "mode")
            mode = str(cached_mode) if cached_mode is not None else MODE_CLOSED
            if mode == MODE_CLOSED:
                # Healthy provider: allow all requests.
                return CircuitBreakerDecision(allowed=True, mode=mode)

            if mode == MODE_OPEN:
                cached_open_until_ms = await self.redis.hget(self._key, "open_until_ms")
                open_until_ms = self._as_int(str(cached_open_until_ms))
                if self._now_ms() < open_until_ms:
                    # Provider is still in its cooldown period: block all traffic.
                    return CircuitBreakerDecision(allowed=False, mode=mode)

                # Cooldown finished: start recovery checks with 50% of requests.
                await self._hset_state(
                    mapping={
                        "mode": MODE_HALF_OPEN,
                        "half_open_successes": 0,
                        "half_open_requests": 0,
                    },
                )
                mode = MODE_HALF_OPEN

            # HINCRBY is shared by all instances, so odd requests are admitted (50%).
            request_number = await self.redis.hincrby(
                name=self._key,
                key="half_open_requests",
                amount=1,
            )
            return CircuitBreakerDecision(
                allowed=request_number % 2 == 1,
                mode=mode,
            )
        except Exception as exc:
            # Redis must not become a reason to block the provider.
            logger.warning(
                "Circuit breaker unavailable service={service}: {error}",
                service=self._key,
                error=str(exc),
            )
            return CircuitBreakerDecision(allowed=True, mode="closed")

    async def record_timeout(self) -> None:
        if not self._is_enabled():
            return

        try:

            mode = await self.redis.hget(self._key, "mode") or "closed"
            now_ms = self._now_ms()
            if mode == "half_open":
                # A failed recovery probe immediately returns the breaker to OPEN.
                await self._open(now_ms)
                return

            cached_last_timeout_ms = await self.redis.hget(self._key, "last_timeout_ms")
            last_timeout_ms = self._as_int(str(cached_last_timeout_ms))

            cached_failure_count = await self.redis.hget(self._key, "failure_count")
            failures = self._as_int(str(cached_failure_count))
            if now_ms - last_timeout_ms > self._config.timeout_window_seconds * 1000:
                # The previous timeout is too old to count toward this outage.
                failures = 1
            else:
                failures += 1

            if failures >= self._config.timeout_threshold:
                # Repeated recent timeouts indicate an outage: stop sending traffic.
                await self._open(now_ms, failures)
                return

            # Keep the breaker closed while the timeout threshold has not been reached.
            await self._hset_state(
                mapping={
                    "mode": "closed",
                    "failure_count": failures,
                    "last_timeout_ms": now_ms,
                },
            )
        except Exception as exc:
            logger.warning(
                "Circuit breaker state update failed service={service}: {error}",
                service=self._key,
                error=str(exc),
            )

    async def record_success(self) -> None:
        if not self._is_enabled():
            return

        try:

            mode = await self.redis.hget(self._key, "mode") or MODE_CLOSED
            if mode == MODE_HALF_OPEN:
                # Count only admitted recovery probes; blocked 50% never reach here.
                successes = await self.redis.hincrby(
                    name=self._key,
                    key="half_open_successes",
                    amount=1,
                )
                if successes < self._config.half_open_success_threshold:
                    return

            # A normal response clears timeout history, or completes recovery.
            await self._hset_state(
                mapping={
                    "mode": "closed",
                    "failure_count": 0,
                    "last_timeout_ms": 0,
                    "half_open_successes": 0,
                    "half_open_requests": 0,
                },
            )
        except Exception as exc:
            logger.warning(
                "Circuit breaker state update failed service={service}: {error}",
                service=self._key,
                error=str(exc),
            )

    async def _open(self, now_ms: int, failures: int | None = None) -> None:
        # Store all state needed for every app instance to enforce the same cooldown.
        await self._hset_state(
            mapping={
                "mode": "open",
                "failure_count": failures or self._config.timeout_threshold,
                "last_timeout_ms": now_ms,
                "open_until_ms": now_ms + self._config.open_seconds * 1000,
                "half_open_successes": 0,
                "half_open_requests": 0,
            },
        )

    async def _hset_state(self, *, mapping: dict[str, str | int]) -> None:
        await self.redis.hset(self._key, mapping=mapping)
        await self.redis.expire(self._key, self._state_ttl_seconds())

    def _state_ttl_seconds(self) -> int:
        return (
            max(
                self._config.timeout_window_seconds,
                self._config.open_seconds,
                1,
            )
            * 2
        )

    def _is_enabled(self) -> bool:
        return self._config.enabled and RedisCacheClient.is_enabled()

    @staticmethod
    def _as_int(value: str | None) -> int:
        return int(value or 0)

    @staticmethod
    def _now_ms() -> int:
        return int(time.time() * 1000)
