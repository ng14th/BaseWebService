from __future__ import annotations

from starlette.responses import JSONResponse


class RequestTooLarge(Exception):
    pass


class RequestSizeLimitMiddleware:
    def __init__(self, app, max_body_bytes: int) -> None:
        self.app = app
        self.max_body_bytes = max_body_bytes

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        content_length = _content_length(scope.get("headers", []))
        if content_length is not None and content_length > self.max_body_bytes:
            await _too_large_response(scope, receive, send)
            return

        received_bytes = 0

        async def limited_receive():
            nonlocal received_bytes
            message = await receive()
            if message["type"] == "http.request":
                received_bytes += len(message.get("body", b""))
                if received_bytes > self.max_body_bytes:
                    raise RequestTooLarge
            return message

        try:
            await self.app(scope, limited_receive, send)
        except RequestTooLarge:
            await _too_large_response(scope, receive, send)


def _content_length(headers) -> int | None:
    for key, value in headers:
        if key.lower() == b"content-length":
            try:
                return int(value)
            except ValueError:
                return None
    return None


async def _too_large_response(scope, receive, send) -> None:
    await JSONResponse(
        status_code=413,
        content={
            "success": False,
            "status_code": 413,
            "message": "Request body is too large",
            "data": [],
            "extra": {},
        },
    )(scope, receive, send)
