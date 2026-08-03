import asyncio

from app.settings import settings

_HTTP_CALL_SEMAPHORE: asyncio.Semaphore | None = None


def get_http_call_semaphore() -> asyncio.Semaphore:
    global _HTTP_CALL_SEMAPHORE
    if _HTTP_CALL_SEMAPHORE is None:
        _HTTP_CALL_SEMAPHORE = asyncio.Semaphore(
            settings.http_max_concurrent_requests,
        )
    return _HTTP_CALL_SEMAPHORE


def reset_http_call_semaphore() -> None:
    global _HTTP_CALL_SEMAPHORE
    _HTTP_CALL_SEMAPHORE = None
