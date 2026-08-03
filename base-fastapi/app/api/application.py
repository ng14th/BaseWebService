import logging
import traceback

import sentry_sdk
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.logging import LoggingIntegration

from app.api.router import api_router
from app.constants.mongo_table import TABLE_LOG_API_CALL
from app.constants.partner import KEY_REQUEST_PARTNER
from app.settings import settings
from core.fastapi_server.lifespan import create_lifespan
from core.logging.log import configure_logging
from core.middlewares.log_request import LogRequestMiddleware
from core.middlewares.request_size import RequestSizeLimitMiddleware
from core.rate_limiter.rate_limit import RateLimitExceeded
from core.schemas.server.exception import ErrorResponseException
from core.schemas.server.response import ApiResponse


def get_app() -> FastAPI:
    """
    Get FastAPI application.

    This is the main constructor of an application.

    :return: application.
    """
    configure_logging()
    if settings.sentry_dsn:
        # Enables sentry integration.
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            traces_sample_rate=settings.sentry_sample_rate,
            environment=settings.environment,
            integrations=[
                FastApiIntegration(transaction_style="endpoint"),
                LoggingIntegration(
                    level=logging.getLevelName(
                        settings.log_level.value,
                    ),
                    event_level=logging.ERROR,
                ),
            ],
        )

    # init app
    app = FastAPI(
        title="my-app",
        lifespan=create_lifespan(settings),
        description="my-app FastAPI service",
        docs_url="/api/docs" if settings.docs_enabled else None,
        redoc_url="/api/redoc" if settings.docs_enabled else None,
        openapi_url="/api/openapi.json" if settings.docs_enabled else None,
    )

    # app.add_middleware(IdempotencyRequestMiddleware)
    app.add_middleware(
        LogRequestMiddleware,
        table=TABLE_LOG_API_CALL,
        request_partner_key=KEY_REQUEST_PARTNER,
    )
    app.add_middleware(
        RequestSizeLimitMiddleware,
        max_body_bytes=settings.max_request_body_bytes,
    )

    # Guards against HTTP Host Header attacks
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.allowed_hosts,
    )

    # Sets all CORS enabled origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            str(origin).rstrip("/") for origin in settings.backend_cors_origins
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add exception handler for generic exceptions.
    @app.exception_handler(Exception)
    async def generic_exception_handler(
        request: Request,
        exception: Exception,
    ):
        request.state.traceback = traceback.format_exc()
        return ApiResponse(
            status_code=500,
            message="Internal server error",
            data=[],
        )

    @app.exception_handler(ErrorResponseException)
    async def error_response_exception_handler(
        request: Request,
        exception: ErrorResponseException,
    ):
        if getattr(exception, "traceback", None):
            request.state.traceback = exception.traceback

        return ApiResponse(
            status_code=exception.status_code,
            message=exception.message,
            data=exception.data,
            extra=exception.extra,
        )

    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_exception_handler(
        request: Request,
        exception: RateLimitExceeded,
    ):
        return ApiResponse(
            status_code=429,
            message="Too many requests",
            data=[],
            extra=exception.extra,
            headers=exception.headers,
        )

    @app.get("/")
    async def root():
        return {"message": "my-app service is running"}

    # Main router for the API.
    app.include_router(router=api_router, prefix="/api")

    return app
