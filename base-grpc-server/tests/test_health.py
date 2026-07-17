from unittest.mock import AsyncMock

import pytest

from core.grpc_server.generated.health import health_pb2
from core.grpc_server.servicers.health import HealthServicer
from core.grpc_server.services.health import HealthService


@pytest.mark.asyncio
async def test_health_service_returns_serving() -> None:
    response = await HealthService().check()

    assert response.status == "SERVING"


@pytest.mark.asyncio
async def test_health_servicer_delegates_to_service() -> None:
    service = HealthService()
    service.check = AsyncMock(
        return_value=health_pb2.HealthCheckResponse(status="SERVING")
    )

    response = await HealthServicer(service).Check(
        health_pb2.HealthCheckRequest(),
        context=None,
    )

    assert response.status == "SERVING"
    service.check.assert_awaited_once()
