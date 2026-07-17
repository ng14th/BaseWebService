import grpc

from app.api.common.grpc import grpc_error_response
from core.grpc_client.generated.health import health_pb2, health_pb2_grpc
from core.schemas.server.response import ApiResponse
from app.settings import settings


class GrpcHealthService:
    def __init__(self, metadata: list[tuple[str, str]]) -> None:
        self._metadata = metadata

    async def check(
        self,
        stub: health_pb2_grpc.HealthServiceStub,
    ) -> ApiResponse:
        try:
            response = await stub.Check(
                health_pb2.HealthCheckRequest(),
                metadata=self._metadata,
                timeout=settings.grpc_timeout_seconds,
            )
        except grpc.RpcError as error:
            raise grpc_error_response(error) from error

        return ApiResponse(
            message="gRPC health check completed",
            data={"status": response.status},
        )
