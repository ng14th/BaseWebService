from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from pydantic_settings import BaseSettings

from core.fastapi_server.lifespan import create_lifespan
from core.grpc_client.lifespan import setup_grpc_client, shutdown_grpc_client


def create_grpc_gateway_lifespan(settings: BaseSettings):
    base_lifespan = create_lifespan(settings)

    @asynccontextmanager
    async def lifespan(
        app: FastAPI,
    ) -> AsyncGenerator[None, None]:  # pragma: no cover
        async with base_lifespan(app):
            setup_grpc_client(app)
            try:
                yield
            finally:
                await shutdown_grpc_client(app)

    return lifespan
