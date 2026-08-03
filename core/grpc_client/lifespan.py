from fastapi import FastAPI

from core.grpc_client.channel import GrpcChannelPool
from app.settings import settings


def setup_grpc_client(app: FastAPI) -> None:
    if not settings.grpc_target:
        return

    app.state.grpc_channel_pool = GrpcChannelPool(
        target=settings.grpc_target,
        size=settings.grpc_pool_size,
    )


async def shutdown_grpc_client(app: FastAPI) -> None:
    channel_pool = getattr(app.state, "grpc_channel_pool", None)
    if channel_pool is not None:
        await channel_pool.close()
