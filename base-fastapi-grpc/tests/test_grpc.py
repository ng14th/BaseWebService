from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import grpc
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.requests import Request

from app.api.common.grpc import build_grpc_metadata, grpc_error_response
from app.api.health.dependencies import (
    get_grpc_health_service,
    get_health_service_stub,
)
from app.api.health.services import GrpcHealthService
from app.api.application import get_app
from app.rpc.channel import GrpcChannelPool
from app.rpc.lifespan import setup_grpc_client, shutdown_grpc_client
from app.rpc.generated.health import health_pb2, health_pb2_grpc
from app.schemas.exception import ErrorResponseException
from app.settings import settings


def test_generated_health_proto() -> None:
    from app.rpc.generated.health import health_pb2, health_pb2_grpc

    response = health_pb2.HealthCheckResponse(status="SERVING")

    assert response.status == "SERVING"
    assert health_pb2_grpc.HealthServiceStub


def test_build_grpc_metadata_uses_headers() -> None:
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/api/v1/health/grpc",
            "query_string": b"",
            "headers": [
                (b"authorization", b"Bearer access-token"),
                (b"x-client-id", b"client-1"),
            ],
        }
    )
    request.scope["route"] = SimpleNamespace(path="/v1/health/grpc")

    assert build_grpc_metadata(request) == [
        ("authorization", "Bearer access-token"),
        ("client_id", "client-1"),
        ("route_path", "/v1/health/grpc"),
        ("http_method", "GET"),
    ]


def test_build_grpc_metadata_uses_query_parameters() -> None:
    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/health/grpc",
            "query_string": b"access_token=token&client_id=client-2",
            "headers": [],
        }
    )

    metadata = dict(build_grpc_metadata(request))

    assert metadata["authorization"] == "Bearer token"
    assert metadata["client_id"] == "client-2"
    assert metadata["route_path"] == "/api/v1/health/grpc"
    assert metadata["http_method"] == "POST"


def test_get_health_service_stub() -> None:
    channel = MagicMock()
    request = MagicMock()
    request.app.state.grpc_channel_pool.get_channel.return_value = channel

    stub = get_health_service_stub(request)

    request.app.state.grpc_channel_pool.get_channel.assert_called_once()
    assert isinstance(stub, health_pb2_grpc.HealthServiceStub)


def test_get_health_service_stub_requires_grpc_client() -> None:
    request = MagicMock()
    request.app.state = SimpleNamespace()

    with pytest.raises(ErrorResponseException, match="not configured") as error:
        get_health_service_stub(request)

    assert error.value.status_code == 503


@pytest.mark.asyncio
async def test_grpc_health_service() -> None:
    stub = MagicMock()
    stub.Check = AsyncMock(
        return_value=health_pb2.HealthCheckResponse(status="SERVING")
    )
    service = GrpcHealthService(metadata=[("client_id", "client-1")])

    response = await service.check(stub)

    assert response.status_code == 200
    assert response.body
    stub.Check.assert_awaited_once_with(
        health_pb2.HealthCheckRequest(),
        metadata=[("client_id", "client-1")],
        timeout=settings.grpc_timeout_seconds,
    )


@pytest.mark.asyncio
async def test_grpc_health_service_maps_rpc_error() -> None:
    class UnavailableError(grpc.RpcError):
        def code(self):
            return grpc.StatusCode.UNAVAILABLE

    stub = MagicMock()
    stub.Check = AsyncMock(side_effect=UnavailableError())

    with pytest.raises(ErrorResponseException) as error:
        await GrpcHealthService(metadata=[]).check(stub)

    assert error.value.status_code == 503


def test_grpc_error_response_defaults_to_internal_error() -> None:
    class UnknownError(grpc.RpcError):
        def code(self):
            return grpc.StatusCode.UNKNOWN

    assert grpc_error_response(UnknownError()).status_code == 500


def test_grpc_health_route() -> None:
    app = get_app()
    stub = MagicMock()
    stub.Check = AsyncMock(
        return_value=health_pb2.HealthCheckResponse(status="SERVING")
    )
    app.dependency_overrides[get_health_service_stub] = lambda: stub

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/health/grpc",
            headers={
                "Authorization": "Bearer access-token",
                "X-Client-ID": "client-1",
            },
        )

    assert response.status_code == 200
    assert response.json()["data"] == {"status": "SERVING"}


@pytest.mark.asyncio
async def test_grpc_channel_pool() -> None:
    channel_pool = GrpcChannelPool("localhost:50051", size=2)

    assert channel_pool.get_channel() is not None
    assert channel_pool.get_channel() is not None

    await channel_pool.close()


@pytest.mark.asyncio
async def test_grpc_client_lifespan(monkeypatch: pytest.MonkeyPatch) -> None:
    app = FastAPI()
    monkeypatch.setattr(settings, "grpc_target", "localhost:50051")

    setup_grpc_client(app)

    assert isinstance(app.state.grpc_channel_pool, GrpcChannelPool)

    await shutdown_grpc_client(app)


def test_grpc_channel_pool_rejects_invalid_size() -> None:
    with pytest.raises(ValueError, match="at least 1"):
        GrpcChannelPool("localhost:50051", size=0)
