from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.grpc import (
    GrpcAioInstrumentorClient,
    GrpcAioInstrumentorServer,
)
from opentelemetry.sdk.resources import DEPLOYMENT_ENVIRONMENT, SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import set_tracer_provider

from app.settings import settings

_tracer_provider: TracerProvider | None = None


def setup_opentelemetry() -> bool:
    global _tracer_provider
    if not settings.opentelemetry_endpoint or _tracer_provider is not None:
        return False

    _tracer_provider = TracerProvider(
        resource=Resource(
            attributes={
                SERVICE_NAME: getattr(settings, "service_name", "my-app-grpc-server"),
                DEPLOYMENT_ENVIRONMENT: settings.environment,
            }
        )
    )
    _tracer_provider.add_span_processor(
        BatchSpanProcessor(
            OTLPSpanExporter(
                endpoint=settings.opentelemetry_endpoint,
                insecure=settings.opentelemetry_insecure,
            )
        )
    )
    set_tracer_provider(_tracer_provider)
    GrpcAioInstrumentorServer().instrument()
    GrpcAioInstrumentorClient().instrument()
    return True


def shutdown_opentelemetry() -> None:
    global _tracer_provider
    if _tracer_provider is None:
        return
    _tracer_provider.shutdown()
    GrpcAioInstrumentorServer().uninstrument()
    GrpcAioInstrumentorClient().uninstrument()
    _tracer_provider = None
