import asyncio
import hashlib
import math
import time
import uuid
from collections import deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Protocol

from fastapi import FastAPI, Request
from redis.asyncio import Redis
from redis.exceptions import WatchError


class RateLimitConfig(Protocol):
    rate_limit_enabled: bool
    rate_limit_by_ip_enabled: bool
    rate_limit_ip_requests: int
    rate_limit_ip_window_seconds: int
    rate_limit_by_auth_enabled: bool
    rate_limit_auth_requests: int
    rate_limit_auth_window_seconds: int
    rate_limit_trust_proxy_headers: bool
    trusted_proxy_ips: list[str]
    rate_limit_watch_retries: int


@dataclass
class RateLimitResult:
    limit: int
    window_seconds: int
    retry_after_seconds: int
    remaining: int
    reset_at: int
    exceeded: bool


class RateLimitExceeded(Exception):
    def __init__(self, scope: str, result: RateLimitResult) -> None:
        self.scope = scope
        self.result = result

    @property
    def headers(self) -> dict[str, str]:
        return {
            "Retry-After": str(self.result.retry_after_seconds),
            "X-RateLimit-Limit": str(self.result.limit),
            "X-RateLimit-Remaining": str(self.result.remaining),
            "X-RateLimit-Reset": str(self.result.reset_at),
            "X-RateLimit-Scope": self.scope,
        }

    @property
    def extra(self) -> dict[str, int | str]:
        return {
            # "scope": self.scope,
            "limit": self.result.limit,
            "window_seconds": self.result.window_seconds,
            "retry_after_seconds": self.result.retry_after_seconds,
        }


class RedisSlidingWindowRateLimiter:
    def __init__(self, redis_client: Redis, config: RateLimitConfig) -> None:
        self._redis = redis_client
        self.config = config

    async def hit(
        self,
        key: str,
        limit: int,
        window_seconds: int,
    ) -> RateLimitResult:
        _validate_window_config(limit=limit, window_seconds=window_seconds)
        ttl_seconds = _window_ttl_seconds(window_seconds)
        window_ms = window_seconds * 1000

        for attempt in range(max(self.config.rate_limit_watch_retries, 1)):
            now_ms = int(time.time() * 1000)
            await self._redis.zremrangebyscore(key, 0, now_ms - window_ms)

            async with self._redis.pipeline(transaction=True) as pipe:
                try:
                    await pipe.watch(key)

                    request_count = int(await pipe.zcard(key))
                    oldest_score = _redis_oldest_score(
                        await pipe.zrange(key, 0, 0, withscores=True)
                    )
                    exceeded = request_count >= limit

                    if exceeded:
                        retry_after_seconds = _redis_retry_after_seconds(
                            oldest_score=oldest_score,
                            now_ms=now_ms,
                            window_ms=window_ms,
                        )
                        reset_after_seconds = _redis_reset_after_seconds(
                            oldest_score=oldest_score,
                            now_ms=now_ms,
                            window_ms=window_ms,
                        )
                        return _build_sliding_window_result(
                            limit=limit,
                            window_seconds=window_seconds,
                            retry_after_seconds=retry_after_seconds,
                            request_count=request_count,
                            reset_after_seconds=reset_after_seconds,
                            exceeded=True,
                        )

                    pipe.multi()
                    pipe.zadd(key, {uuid.uuid4().hex: now_ms})
                    pipe.expire(key, ttl_seconds)
                    await pipe.execute()

                    request_count += 1
                    if oldest_score is None:
                        oldest_score = now_ms
                    reset_after_seconds = _redis_reset_after_seconds(
                        oldest_score=oldest_score,
                        now_ms=now_ms,
                        window_ms=window_ms,
                    )
                    return _build_sliding_window_result(
                        limit=limit,
                        window_seconds=window_seconds,
                        retry_after_seconds=0,
                        request_count=request_count,
                        reset_after_seconds=reset_after_seconds,
                        exceeded=False,
                    )
                except WatchError:
                    if attempt + 1 >= self.config.rate_limit_watch_retries:
                        raise
                    await asyncio.sleep(min(0.01 * (2**attempt), 0.1))

        raise RuntimeError(
            "Unreachable code in RedisSlidingWindowRateLimiter.hit"
        )  # pragma: no cover


def _validate_window_config(*, limit: int, window_seconds: int) -> None:
    if limit <= 0:
        raise ValueError("rate limit must be greater than 0")
    if window_seconds <= 0:
        raise ValueError("rate limit window_seconds must be greater than 0")


def _window_ttl_seconds(window_seconds: int) -> int:
    return max(window_seconds * 2, 1)


def _trim_window(requests: deque[float], cutoff: float) -> None:
    while requests and requests[0] <= cutoff:
        requests.popleft()


def _window_reset_after_seconds(
    requests: deque[float],
    now: float,
    window_seconds: int,
) -> int:
    if not requests:
        return 0
    return max(math.ceil((requests[0] + window_seconds) - now), 0)


def _redis_oldest_score(entries) -> int | None:
    if not entries:
        return None
    return int(float(entries[0][1]))


def _redis_retry_after_seconds(
    *,
    oldest_score: int | None,
    now_ms: int,
    window_ms: int,
) -> int:
    if oldest_score is None:
        return 1
    return max(math.ceil(((oldest_score + window_ms) - now_ms) / 1000), 1)


def _redis_reset_after_seconds(
    *,
    oldest_score: int | None,
    now_ms: int,
    window_ms: int,
) -> int:
    if oldest_score is None:
        return 0
    return max(math.ceil(((oldest_score + window_ms) - now_ms) / 1000), 0)


def _build_sliding_window_result(
    *,
    limit: int,
    window_seconds: int,
    retry_after_seconds: int,
    request_count: int,
    reset_after_seconds: int,
    exceeded: bool,
    remaining: int | None = None,
) -> RateLimitResult:
    if remaining is None:
        remaining = max(limit - request_count, 0)

    return RateLimitResult(
        limit=limit,
        window_seconds=window_seconds,
        retry_after_seconds=retry_after_seconds,
        remaining=remaining,
        reset_at=int(time.time() + reset_after_seconds),
        exceeded=exceeded,
    )


def init_rate_limiter(app: FastAPI, config: RateLimitConfig) -> None:
    """
    Initialize and store the rate limiter backend in app state.
    """
    if not config.rate_limit_enabled:
        app.state.rate_limiter_store = None
        return

    redis_client = getattr(app.state, "redis_client", None)
    if redis_client is None:
        raise RuntimeError("Redis client is required when rate limit is enabled")

    app.state.rate_limiter_store = RedisSlidingWindowRateLimiter(
        redis_client,
        config=config,
    )


def get_rate_limiter_store(request: Request) -> RedisSlidingWindowRateLimiter:
    store = getattr(request.app.state, "rate_limiter_store", None)
    if store is None:
        raise RuntimeError("Rate limiter not initialized")
    return store


def rate_limit(
    *,
    config: RateLimitConfig,
    by_ip: bool | None = None,
    ip_requests: int | None = None,
    ip_window_seconds: int | None = None,
    by_auth: bool | None = None,
    auth_identifier_getter: Callable[[Request], str | None] | None = None,
    auth_requests: int | None = None,
    auth_window_seconds: int | None = None,
    trust_proxy_headers: bool | None = None,
) -> Callable[[Request], Awaitable[None]]:
    """
    Build a FastAPI dependency for per-route rate limits.

    Example:
        dependencies=[Depends(rate_limit(ip_requests=30, ip_window_seconds=60))]
    """

    async def dependency(request: Request) -> None:
        if not config.rate_limit_enabled:
            return

        if _resolve_bool(by_ip, config.rate_limit_by_ip_enabled):
            await _check_ip_limit(
                request=request,
                config=config,
                limit=ip_requests or config.rate_limit_ip_requests,
                window_seconds=(
                    ip_window_seconds or config.rate_limit_ip_window_seconds
                ),
                trust_proxy_headers=_resolve_bool(
                    trust_proxy_headers,
                    config.rate_limit_trust_proxy_headers,
                ),
            )

        if _resolve_bool(by_auth, config.rate_limit_by_auth_enabled):
            identifier = (
                auth_identifier_getter(request) if auth_identifier_getter else None
            )
            if identifier:
                await _check_auth_limit(
                    request=request,
                    config=config,
                    auth_identifier=identifier,
                    limit=auth_requests or config.rate_limit_auth_requests,
                    window_seconds=(
                        auth_window_seconds or config.rate_limit_auth_window_seconds
                    ),
                )

    return dependency


async def _check_ip_limit(
    *,
    request: Request,
    config: RateLimitConfig,
    limit: int,
    window_seconds: int,
    trust_proxy_headers: bool,
) -> None:
    ip_identifier = _get_client_ip(request, config, trust_proxy_headers)
    if not ip_identifier:
        return

    store = get_rate_limiter_store(request)
    key = _build_rate_limit_key("ip", request, ip_identifier)
    result = await store.hit(
        key=key,
        limit=limit,
        window_seconds=window_seconds,
    )
    if result.exceeded:
        raise RateLimitExceeded(scope="ip", result=result)


async def _check_auth_limit(
    *,
    request: Request,
    config: RateLimitConfig,
    auth_identifier: str,
    limit: int,
    window_seconds: int,
) -> None:

    store = get_rate_limiter_store(request)

    key = _build_rate_limit_key("auth", request, auth_identifier)
    result = await store.hit(
        key=key,
        limit=limit,
        window_seconds=window_seconds,
    )
    if result.exceeded:
        raise RateLimitExceeded(scope="auth", result=result)


def _resolve_bool(value: bool | None, default: bool) -> bool:
    return default if value is None else value


def _rate_limit_request_scope(request: Request) -> str:
    route = request.scope.get("route") if hasattr(request, "scope") else None
    route_path = getattr(route, "path", None)
    if not route_path:
        route_path = request.url.path
    return f"{request.method}:{route_path}"


def _get_client_ip(
    request: Request,
    config: RateLimitConfig,
    trust_proxy_headers: bool,
) -> str | None:
    if trust_proxy_headers:
        trusted_proxy_ips = set(config.trusted_proxy_ips)
        if trusted_proxy_ips and (
            request.client is None or request.client.host not in trusted_proxy_ips
        ):
            trust_proxy_headers = False
    if trust_proxy_headers:
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",", maxsplit=1)[0].strip()

        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip.strip()

    return request.client.host if request.client else None


def _build_rate_limit_key(scope: str, request: Request, identifier: str) -> str:
    digest = hashlib.sha256(identifier.encode("utf-8")).hexdigest()[:16]
    return f"rate_limit:{scope}:{_rate_limit_request_scope(request)}:{digest}"
