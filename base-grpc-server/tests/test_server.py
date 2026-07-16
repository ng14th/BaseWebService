import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.rpc.client import GrpcHealthClient
from app.rpc.server import GrpcServer, run_server


@pytest.mark.asyncio
async def test_server_and_client_health_check() -> None:
    server = GrpcServer(host="127.0.0.1", port=0)
    await server.start()
    client = GrpcHealthClient(target=server.address)

    try:
        response = await client.check()
    finally:
        await client.close()
        await server.stop()

    assert response.status == "SERVING"


@pytest.mark.asyncio
async def test_server_stops_after_termination() -> None:
    server = GrpcServer(host="127.0.0.1", port=0)
    server.start = AsyncMock()
    server.stop = AsyncMock()
    stop_event = asyncio.Event()
    stop_event.set()

    await server.serve(stop_event)

    server.start.assert_awaited_once()
    server.stop.assert_awaited_once()


@pytest.mark.asyncio
async def test_server_registers_signal_handlers() -> None:
    server = GrpcServer(host="127.0.0.1", port=0)
    server.start = AsyncMock()
    server.stop = AsyncMock()
    loop = MagicMock()

    def add_signal_handler(_, callback):
        callback()

    loop.add_signal_handler.side_effect = add_signal_handler
    with patch("app.rpc.server.asyncio.get_running_loop", return_value=loop):
        await server.serve()

    assert loop.add_signal_handler.call_count == 2
    assert loop.remove_signal_handler.call_count == 2


@pytest.mark.asyncio
async def test_run_server_shuts_down_telemetry() -> None:
    with (
        patch("app.rpc.server.configure_logging"),
        patch("app.rpc.server.setup_opentelemetry"),
        patch("app.rpc.server.shutdown_opentelemetry") as shutdown,
        patch("app.rpc.server.GrpcServer") as grpc_server,
    ):
        grpc_server.return_value.serve = AsyncMock()

        await run_server()

    grpc_server.return_value.serve.assert_awaited_once()
    shutdown.assert_called_once()
