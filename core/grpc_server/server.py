import asyncio
import signal

import grpc.aio
from loguru import logger
from opentelemetry.instrumentation.grpc import aio_server_interceptor

from core.grpc_server.otelemetry import setup_opentelemetry, shutdown_opentelemetry
from core.logging.log import configure_logging
from core.grpc_server.generated.health import health_pb2_grpc
from core.grpc_server.servicers.health import HealthServicer
from app.settings import settings


class GrpcServer:
    def __init__(self, host: str | None = None, port: int | None = None) -> None:
        server_options = [
            ("grpc.keepalive_permit_without_calls", 1),
            ("grpc.http2.min_recv_ping_interval_without_data_ms", 10000),
            ("grpc.http2.max_ping_strikes", 0),
        ]
        interceptors = (
            [aio_server_interceptor()] if settings.opentelemetry_endpoint else []
        )
        self._server = grpc.aio.server(
            options=server_options,
            interceptors=interceptors,
        )
        self._host = host or settings.grpc_host
        self._port = self._server.add_insecure_port(
            f"{self._host}:{port if port is not None else settings.grpc_port}"
        )
        health_pb2_grpc.add_HealthServiceServicer_to_server(
            HealthServicer(), self._server
        )

    @property
    def address(self) -> str:
        return f"{self._host}:{self._port}"

    async def start(self) -> None:
        await self._server.start()
        logger.info("gRPC server started on {}", self.address)

    async def stop(self) -> None:
        await self._server.stop(settings.grpc_shutdown_grace_seconds)
        logger.info("gRPC server stopped")

    async def serve(self, stop_event: asyncio.Event | None = None) -> None:
        await self.start()
        registered_signals: list[signal.Signals] = []
        if stop_event is None:
            stop_event = asyncio.Event()
            loop = asyncio.get_running_loop()
            for sig in (signal.SIGINT, signal.SIGTERM):
                try:
                    loop.add_signal_handler(sig, stop_event.set)
                    registered_signals.append(sig)
                except NotImplementedError:  # pragma: no cover
                    pass
        try:
            await stop_event.wait()
        finally:
            for sig in registered_signals:
                asyncio.get_running_loop().remove_signal_handler(sig)
            await self.stop()


async def run_server() -> None:
    configure_logging()
    setup_opentelemetry()
    try:
        await GrpcServer().serve()
    finally:
        shutdown_opentelemetry()


if __name__ == "__main__":  # pragma: no cover
    asyncio.run(run_server())  # pragma: no cover
