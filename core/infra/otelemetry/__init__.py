import os
from typing import Any

from fastapi import FastAPI
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.celery import CeleryInstrumentor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.propagate import set_global_textmap
from opentelemetry.sdk.resources import (
    DEPLOYMENT_ENVIRONMENT,
    SERVICE_NAME,
    TELEMETRY_SDK_LANGUAGE,
    Resource,
)
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import (
    ProxyTracerProvider,
    get_tracer_provider,
    set_tracer_provider,
)
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

from app.settings import settings
from core.db.engine_routing import READ_ENGINE, WRITE_ENGINE

_SETUP_PIDS: set[int] = set()


def _instrument_once(instrumentor: Any, **kwargs: Any) -> None:
    if instrumentor.is_instrumented_by_opentelemetry:
        return
    instrumentor.instrument(**kwargs)


def setup_opentelemetry(app: FastAPI | None = None) -> None:
    """
    Enables opentelemetry instrumentation.

    :param app: current application.
    """
    if not settings.opentelemetry_endpoint:
        return

    process_id = os.getpid()
    if process_id in _SETUP_PIDS:
        return

    current_provider = get_tracer_provider()
    if isinstance(current_provider, ProxyTracerProvider):
        tracer_provider = TracerProvider(
            resource=Resource(
                attributes={
                    SERVICE_NAME: getattr(settings, "service_name", "my-app"),
                    TELEMETRY_SDK_LANGUAGE: "python",
                    DEPLOYMENT_ENVIRONMENT: settings.environment,
                },
            ),
        )

        tracer_provider.add_span_processor(
            BatchSpanProcessor(
                OTLPSpanExporter(
                    endpoint=settings.opentelemetry_endpoint,
                    insecure=settings.opentelemetry_insecure,
                ),
            ),
        )
        set_tracer_provider(tracer_provider=tracer_provider)
    else:
        tracer_provider = current_provider

    set_global_textmap(TraceContextTextMapPropagator())
    if app:
        excluded_endpoints: list[str] = []
        for route_name in (
            "health_check",
            "openapi",
            "swagger_ui_html",
            "swagger_ui_redirect",
            "redoc_html",
        ):
            try:
                excluded_endpoints.append(app.url_path_for(route_name))
            except Exception:
                pass
        excluded_endpoints.append("/metrics")

        if not FastAPIInstrumentor().is_instrumented_by_opentelemetry:
            FastAPIInstrumentor().instrument_app(
                app,
                tracer_provider=tracer_provider,
                excluded_urls=",".join(excluded_endpoints),
            )

    _instrument_once(CeleryInstrumentor(), tracer_provider=tracer_provider)
    _instrument_once(
        SQLAlchemyInstrumentor(),
        engines=[WRITE_ENGINE.sync_engine, READ_ENGINE.sync_engine],
        tracer_provider=tracer_provider,
    )
    _SETUP_PIDS.add(process_id)


def stop_opentelemetry(app: FastAPI) -> None:  # pragma: no cover
    """
    Disables opentelemetry instrumentation.

    :param app: current application.
    """
    if not settings.opentelemetry_endpoint:
        return

    FastAPIInstrumentor().uninstrument_app(app)
    provider = get_tracer_provider()
    shutdown = getattr(provider, "shutdown", None)
    if shutdown is not None:
        shutdown()
