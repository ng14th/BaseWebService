from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from prometheus_fastapi_instrumentator.instrumentation import (
    PrometheusFastApiInstrumentator,
)
from pydantic_settings import BaseSettings

from core.db.lifespan import dispose_engines, setup_database
from core.infra.connectors.concurrency import reset_http_call_semaphore
from core.infra.connectors.http_client_manager import HttpClientManager
from core.infra.otelemetry import setup_opentelemetry, stop_opentelemetry
from core.infra.redis.lifespan import init_redis, shutdown_redis_client
from core.infra.system_log.mongo import MongoClientSingleton
from core.rate_limiter.rate_limit import init_rate_limiter


def setup_prometheus(
    app: FastAPI,
    settings: BaseSettings,
) -> None:  # pragma: no cover
    """
    Enables prometheus integration.

    :param app: current application.
    """
    metrics_enabled = getattr(settings, "metrics_enabled", False)
    if not metrics_enabled:
        return
    PrometheusFastApiInstrumentator(should_group_status_codes=False).instrument(
        app
    ).expose(app, should_gzip=True, name="prometheus_metrics")


def create_lifespan(settings: BaseSettings):
    @asynccontextmanager
    async def lifespan(
        app: FastAPI,
    ) -> AsyncGenerator[None, None]:  # pragma: no cover
        """
        Actions to run on application startup.

        This function uses fastAPI app to store data
        in the state, such as db_engine.

        :param app: the fastAPI application.
        :return: function that actually performs actions.
        """

        setup_database(app)
        init_redis(app)
        init_rate_limiter(app)
        await HttpClientManager.initialize()
        
        try:
            yield
        finally:
            MongoClientSingleton.close()
            stop_opentelemetry(app)
            await shutdown_redis_client(app)
            await HttpClientManager.close_client()
            reset_http_call_semaphore()
            await dispose_engines()

    return lifespan
