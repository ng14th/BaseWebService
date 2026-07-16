from app.rpc.generated.health import health_pb2, health_pb2_grpc
from app.rpc.services.health import HealthService


class HealthServicer(health_pb2_grpc.HealthServiceServicer):
    def __init__(self, service: HealthService | None = None) -> None:
        self._service = service or HealthService()

    async def Check(
        self,
        request: health_pb2.HealthCheckRequest,
        context,
    ) -> health_pb2.HealthCheckResponse:
        return await self._service.check()
