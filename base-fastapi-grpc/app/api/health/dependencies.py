from fastapi import Request, status

from app.api.common.grpc import build_grpc_metadata
from app.api.health.services import GrpcHealthService
from app.rpc.generated.health import health_pb2_grpc
from app.schemas.exception import ErrorResponseException


def get_health_service_stub(
    request: Request,
) -> health_pb2_grpc.HealthServiceStub:
    channel_pool = getattr(request.app.state, "grpc_channel_pool", None)
    if channel_pool is None:
        raise ErrorResponseException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            message="gRPC client is not configured",
        )
    return health_pb2_grpc.HealthServiceStub(channel_pool.get_channel())


def get_grpc_health_service(request: Request) -> GrpcHealthService:
    return GrpcHealthService(metadata=build_grpc_metadata(request))
