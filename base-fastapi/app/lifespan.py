from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from prometheus_fastapi_instrumentator.instrumentation import (
    PrometheusFastApiInstrumentator,
)

from app.api.common.rate_limit import init_rate_limiter
from app.db.lifespan import dispose_engines, setup_database
from app.infra.connectors.concurrency import reset_http_call_semaphore
from app.infra.connectors.http_client_manager import HttpClientManager
from app.infra.otelemetry import setup_opentelemetry, stop_opentelemetry
from app.infra.redis.lifespan import init_redis, shutdown_redis
from app.infra.system_log.mongo import MongoClientSingleton
from app.settings import settings


def setup_prometheus(app: FastAPI) -> None:  # pragma: no cover
    """
    Enables prometheus integration.

    :param app: current application.
    """
    if not settings.metrics_enabled:
        return
    PrometheusFastApiInstrumentator(should_group_status_codes=False).instrument(
        app
    ).expose(app, should_gzip=True, name="prometheus_metrics")


@asynccontextmanager
async def lifespan_setup(
    app: FastAPI,
) -> AsyncGenerator[None, None]:  # pragma: no cover
    """
    Actions to run on application startup.

    This function uses fastAPI app to store data
    in the state, such as db_engine.

    :param app: the fastAPI application.
    :return: function that actually performs actions.
    """

    app.middleware_stack = None
    setup_opentelemetry(app)
    setup_prometheus(app)
    setup_database(app)
    init_redis(app)
    init_rate_limiter(app)

    app.middleware_stack = app.build_middleware_stack()

    yield

    MongoClientSingleton.close()
    stop_opentelemetry(app)
    await shutdown_redis(app)
    await HttpClientManager.close_client()
    reset_http_call_semaphore()
    await dispose_engines()
