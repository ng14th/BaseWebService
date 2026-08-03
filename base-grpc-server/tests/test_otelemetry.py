from core.grpc_server import otelemetry
from app.settings import settings


class FakeTracerProvider:
    def __init__(self, *, resource):
        self.resource = resource
        self.processors = []
        self.shutdown_called = False

    def add_span_processor(self, processor):
        self.processors.append(processor)

    def shutdown(self):
        self.shutdown_called = True


class FakeInstrumentor:
    instances = []

    def __init__(self):
        self.instrument_called = False
        self.uninstrument_called = False
        self.instances.append(self)

    def instrument(self):
        self.instrument_called = True

    def uninstrument(self):
        self.uninstrument_called = True


def setup_function():
    otelemetry._tracer_provider = None
    FakeInstrumentor.instances = []


def test_setup_opentelemetry_returns_false_without_endpoint(monkeypatch):
    monkeypatch.setattr(settings, "opentelemetry_endpoint", None)

    assert otelemetry.setup_opentelemetry() is False


def test_shutdown_opentelemetry_noops_without_provider():
    otelemetry.shutdown_opentelemetry()
    assert otelemetry._tracer_provider is None


def test_setup_and_shutdown_opentelemetry(monkeypatch):
    monkeypatch.setattr(settings, "opentelemetry_endpoint", "http://otel")
    monkeypatch.setattr(settings, "opentelemetry_insecure", True)
    monkeypatch.setattr(otelemetry, "TracerProvider", FakeTracerProvider)
    monkeypatch.setattr(otelemetry, "OTLPSpanExporter", lambda **kwargs: kwargs)
    monkeypatch.setattr(otelemetry, "BatchSpanProcessor", lambda exporter: exporter)
    monkeypatch.setattr(otelemetry, "set_tracer_provider", lambda provider: None)
    monkeypatch.setattr(otelemetry, "GrpcAioInstrumentorServer", FakeInstrumentor)
    monkeypatch.setattr(otelemetry, "GrpcAioInstrumentorClient", FakeInstrumentor)

    assert otelemetry.setup_opentelemetry() is True
    provider = otelemetry._tracer_provider
    assert provider.processors == [
        {
            "endpoint": "http://otel",
            "insecure": True,
        }
    ]
    assert all(item.instrument_called for item in FakeInstrumentor.instances)

    assert otelemetry.setup_opentelemetry() is False
    otelemetry.shutdown_opentelemetry()

    assert provider.shutdown_called is True
    assert all(item.uninstrument_called for item in FakeInstrumentor.instances[-2:])
    assert otelemetry._tracer_provider is None
