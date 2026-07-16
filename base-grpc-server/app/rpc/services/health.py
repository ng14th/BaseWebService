from app.rpc.generated.health import health_pb2


class HealthService:
    async def check(self) -> health_pb2.HealthCheckResponse:
        return health_pb2.HealthCheckResponse(status="SERVING")
