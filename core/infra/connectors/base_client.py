from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Mapping, Self

import httpx
from loguru import logger
from yarl import URL

from core.infra.circuit_breaker import CircuitBreakerConfig, RedisCircuitBreaker
from core.infra.connectors.concurrency import get_http_call_semaphore
from core.infra.connectors.custom_response import CustomResponse
from core.infra.connectors.http_client_manager import HttpClientManager
from core.infra.connectors.safe_logging import redact_sensitive_data, safe_log_body


@dataclass(frozen=True)
class ConnectorConfig:
    base_url: str | None
    timeout_s: float = 10.0
    service_name: str | None = None
    circuit_breaker: CircuitBreakerConfig = field(default_factory=CircuitBreakerConfig)


def _format_log_body(value: Any, max_len: int = 500) -> Any:
    logged = safe_log_body(value)
    if logged is None:
        return None
    logged_str = str(logged)
    if len(logged_str) > max_len:
        return logged_str[:max_len] + f"... [truncated, total {len(logged_str)} chars]"
    return logged


class BaseAsyncHttpConnector:
    source_service: str = "EInvoiceService"

    def __init__(
        self,
        config: ConnectorConfig,
        *,
        client: httpx.AsyncClient | None = None,
        default_headers: Mapping[str, str] | None = None,
    ) -> None:
        self._config = config
        self._default_headers = dict(default_headers or {})
        self._owns_client = False
        self._client = client or HttpClientManager.get_client()
        service_name = (
            config.service_name or URL(config.base_url or "").host or "downstream"
        )
        self._circuit_breaker = RedisCircuitBreaker(
            service_name, config.circuit_breaker
        )

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.aclose()

    def _make_url(self, path_or_url: str) -> str:
        if path_or_url.startswith(("http://", "https://")):
            return path_or_url
        return str(URL(self._config.base_url) / path_or_url.lstrip("/"))  # type: ignore

    async def request(
        self,
        *,
        method: str,
        path_or_url: str,
        body: Any | None = None,
        data: Mapping[str, str] | None = None,
        headers: Mapping[str, str] | None = None,
        params: Mapping[str, Any] | None = None,
        timeout_s: float | None = None,
    ) -> CustomResponse:
        url = self._make_url(path_or_url)
        effective_timeout = timeout_s or self._config.timeout_s

        request_headers = {**self._default_headers, **dict(headers or {})}
        request_kwargs: dict[str, Any] = {
            "method": method.upper(),
            "url": url,
            "headers": request_headers,
            "params": params,
            "timeout": effective_timeout,
        }

        if isinstance(body, (dict, list)):
            request_kwargs["json"] = body
        elif body is not None:
            request_kwargs["content"] = body

        if data:
            request_kwargs["data"] = data

        service = self._config.service_name or "downstream"

        decision = await self._circuit_breaker.allow_request()
        if not decision.allowed:
            logger.warning(
                "Circuit breaker rejected request service={service} mode={mode}",
                service=service,
                mode=decision.mode,
            )
            return CustomResponse(
                response=None,
                execute_time_ms=0,
                source_service=self.source_service,
                is_circuit_open=True,
            )

        logger.info(
            "HTTP request service={service} {method} {url} "
            "headers={headers} params={params} body={body} data={data}",
            service=service,
            method=method.upper(),
            url=url,
            headers=redact_sensitive_data(request_headers),
            params=redact_sensitive_data(params),
            body=_format_log_body(body),
            data=_format_log_body(data),
        )

        try:
            start = time.perf_counter()
            async with get_http_call_semaphore():
                response = await self._client.request(**request_kwargs)
        except (httpx.PoolTimeout, httpx.TimeoutException):
            execute_time_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.warning(
                "HTTP timeout service={service} {method} {url} "
                "duration_ms={execute_time_ms}",
                service=service,
                method=method.upper(),
                url=url,
                execute_time_ms=execute_time_ms,
            )
            await self._circuit_breaker.record_timeout()
            return CustomResponse(
                response=None,
                execute_time_ms=execute_time_ms,
                source_service=self.source_service,
                is_timeout=True,
            )
        except Exception as exc:
            execute_time_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.exception(
                "HTTP request failed service={service} {method} {url} "
                "duration_ms={execute_time_ms} error={error}",
                service=service,
                method=method.upper(),
                url=url,
                execute_time_ms=execute_time_ms,
                error=str(exc),
            )
            raise

        execute_time_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.info(
            "HTTP response service={service} {method} {url} status={status_code} "
            "duration_ms={execute_time_ms} body={body}",
            service=service,
            method=method.upper(),
            url=url,
            status_code=response.status_code,
            execute_time_ms=execute_time_ms,
            body=_format_log_body(response.text),
        )
        result = CustomResponse(
            response=response,
            execute_time_ms=execute_time_ms,
            source_service=self.source_service,
        )
        await self._circuit_breaker.record_success()
        return result
