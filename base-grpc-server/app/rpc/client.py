from app.rpc.channel import GrpcChannelPool
from app.rpc.generated.health import health_pb2, health_pb2_grpc
from app.settings import settings


class GrpcHealthClient:
    def __init__(
        self,
        target: str | None = None,
        timeout_seconds: float | None = None,
        pool_size: int | None = None,
    ) -> None:
        self._timeout_seconds = timeout_seconds or settings.grpc_client_timeout_seconds
        self._channel_pool = GrpcChannelPool(
            target=target or settings.grpc_client_target,
            size=pool_size or settings.grpc_client_channel_pool_size,
        )

    async def check(self) -> health_pb2.HealthCheckResponse:
        stub = health_pb2_grpc.HealthServiceStub(self._channel_pool.get_channel())
        return await stub.Check(
            health_pb2.HealthCheckRequest(),
            timeout=self._timeout_seconds,
        )

    async def close(self) -> None:
        await self._channel_pool.close()
