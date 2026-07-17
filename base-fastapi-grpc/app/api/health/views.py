from fastapi import APIRouter, Depends, Request

from app.api.common.dependencies import check_required_auth_header
from core.rate_limiter.rate_limit import rate_limit
from app.api.health.dependencies import (
    get_grpc_health_service,
    get_health_service_stub,
)
from app.api.health.services import GrpcHealthService
from core.grpc_client.generated.health import health_pb2_grpc
from core.schemas.server.response import ApiResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_class=ApiResponse)
async def health_check() -> ApiResponse:
    return ApiResponse(message="OK", data={"status": "healthy"})


@router.get(
    "/health/grpc",
    response_class=ApiResponse,
    dependencies=[Depends(rate_limit())],
)
async def grpc_health_check(
    request: Request,
    _: bool = Depends(check_required_auth_header),
    stub: health_pb2_grpc.HealthServiceStub = Depends(get_health_service_stub),
    service: GrpcHealthService = Depends(get_grpc_health_service),
) -> ApiResponse:
    return await service.check(stub)
