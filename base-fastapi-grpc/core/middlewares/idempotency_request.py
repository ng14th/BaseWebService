import hashlib

from redis.asyncio import Redis
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

WRITE_METHODS = {"PUT", "POST", "PATCH", "DELETE"}
IDEMPOTENCY_TTL_SECONDS = 10 * 60
IDEMPOTENCY_PREFIX = "idempotency:body:"


class IdempotencyRequestMiddleware(BaseHTTPMiddleware):
    """
    Middleware to prevent duplicated write requests by request body.
    """

    def _get_redis_client(self, request) -> Redis:
        redis_pool = request.app.state.redis_pool
        if redis_pool is None:
            raise RuntimeError("Redis not initialized")
        return Redis(connection_pool=redis_pool, decode_responses=True)

    @staticmethod
    def _build_key(request_body: bytes) -> str:
        digest = hashlib.sha256(request_body).hexdigest()
        return f"{IDEMPOTENCY_PREFIX}{digest}"

    async def dispatch(self, request, call_next):
        if request.method not in WRITE_METHODS:
            return await call_next(request)

        redis_client = self._get_redis_client(request)

        request_body = await request.body()
        if not request_body:
            return await call_next(request)

        key = self._build_key(request_body)
        locked = await redis_client.set(
            key,
            "1",
            nx=True,
            ex=IDEMPOTENCY_TTL_SECONDS,
        )
        if not locked:
            return JSONResponse(
                status_code=409,
                content={
                    "success": False,
                    "message": "Yêu cầu đang được xử lý.",
                    "data": [],
                },
            )

        response = await call_next(request)

        await redis_client.delete(key)
        return response
