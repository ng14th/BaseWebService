import asyncio

from core.grpc_server.otelemetry import setup_opentelemetry, shutdown_opentelemetry
from core.grpc_server.server import GrpcServer
from core.logging.log import configure_logging


async def main() -> None:
    """
    Main entry point for starting the gRPC server.
    """
    configure_logging()
    setup_opentelemetry()
    try:
        server = GrpcServer()
        
        # Register custom gRPC servicers here using server.server (grpc.aio.Server)
        # e.g.: my_service_pb2_grpc.add_MyServiceServicer_to_server(MyServicer(), server.server)
        
        await server.serve()
    finally:
        shutdown_opentelemetry()


if __name__ == "__main__":
    asyncio.run(main())
