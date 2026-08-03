import enum
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class LogLevel(str, enum.Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class Settings(BaseSettings):
    service_name: str = "my-app-grpc-server"

    environment: str = "dev"
    log_level: LogLevel = LogLevel.INFO

    grpc_host: str = "0.0.0.0"
    grpc_port: int = 50051
    grpc_shutdown_grace_seconds: float = 15.0

    grpc_client_target: str = "127.0.0.1:50051"
    grpc_client_timeout_seconds: float = 20.0
    grpc_client_channel_pool_size: int = 1

    opentelemetry_endpoint: str | None = None
    opentelemetry_insecure: bool = False

    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent.parent / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
