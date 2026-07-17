from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from core.rate_limiter.rate_limit import RateLimitExceeded, RateLimitResult
from app.api.application import get_app
from core.schemas.server.exception import ErrorResponseException
from app.settings import settings


def test_health_check() -> None:
    with TestClient(get_app()) as client:
        response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert response.json()["data"] == {"status": "healthy"}


def test_app_initializes_sentry(monkeypatch) -> None:
    monkeypatch.setattr(settings, "sentry_dsn", "https://key@example.com/1")
    with patch("app.api.application.sentry_sdk.init") as init:
        get_app()
    init.assert_called_once()


@pytest.mark.asyncio
async def test_exception_handlers() -> None:
    app = get_app()
    request = MagicMock()
    request.state = SimpleNamespace()

    generic = app.exception_handlers[Exception]
    try:
        raise RuntimeError("boom")
    except RuntimeError as error:
        generic_response = await generic(request, error)
    assert generic_response.status_code == 500
    assert request.state.traceback

    error_handler = app.exception_handlers[ErrorResponseException]
    error_response = await error_handler(
        request,
        ErrorResponseException(
            status_code=422,
            message="Invalid request",
            traceback="internal-only",
        ),
    )
    assert error_response.status_code == 422
    assert request.state.traceback == "internal-only"

    rate_limit_handler = app.exception_handlers[RateLimitExceeded]
    rate_limit_response = await rate_limit_handler(
        request,
        RateLimitExceeded(
            "ip",
            RateLimitResult(
                limit=10,
                window_seconds=60,
                retry_after_seconds=1,
                remaining=0,
                reset_at=1,
                exceeded=True,
            ),
        ),
    )
    assert rate_limit_response.status_code == 429
