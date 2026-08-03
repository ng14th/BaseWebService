import enum
from pathlib import Path
from tempfile import gettempdir
from typing import Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from yarl import URL

from app.settings.app_security import Security
from app.settings.celery_setting import CelerySetting
from app.settings.circuit_breaker_setting import CircuitBreakerSetting
from app.settings.db_setting import DatabaseSetting
from app.settings.gunicorn_settings import GunicornSetting
from app.settings.grpc_setting import GrpcSetting
from app.settings.http_client_setting import HttpClientSetting
from app.settings.mongo_setting import MongoSetting
from app.settings.rate_limit_setting import RateLimitSetting
from app.settings.redis_setting import RedisSetting

TEMP_DIR = Path(gettempdir())


class LogLevel(str, enum.Enum):
    NOTSET = "NOTSET"
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    FATAL = "FATAL"


class Settings(
    BaseSettings,
    DatabaseSetting,
    GunicornSetting,
    GrpcSetting,
    HttpClientSetting,
    Security,
    RedisSetting,
    MongoSetting,
    CelerySetting,
    CircuitBreakerSetting,
    RateLimitSetting,
):
    host: str = "127.0.0.1"
    port: int = 8000
    reload: bool = False
    service_name: str = "my-app"

    environment: str = "dev"
    log_level: LogLevel = LogLevel.INFO

    prometheus_dir: Path = TEMP_DIR / "prom"

    sentry_dsn: Optional[str] = None
    sentry_sample_rate: float = 1.0
    opentelemetry_endpoint: Optional[str] = None
    opentelemetry_insecure: bool = False

    max_request_body_bytes: int = 2 * 1024 * 1024
    max_log_body_bytes: int = 16 * 1024

    @property
    def db_url(self) -> URL:
        return URL.build(
            scheme="postgresql+asyncpg",
            host=self.db_host,
            port=self.db_port,
            user=self.db_user,
            password=self.db_pass,
            path=f"/{self.db_name}",
        )

    @property
    def db_read_url(self) -> URL:
        return URL.build(
            scheme="postgresql+asyncpg",
            host=self.db_read_host,
            port=self.db_read_port,
            user=self.db_read_user,
            password=self.db_read_pass,
            path=f"/{self.db_read_name}",
        )

    @field_validator("prometheus_dir")
    @classmethod
    def validate_prometheus_dir(cls, value: Path) -> Path:
        if str(value) in (".", "") or value.absolute() == Path.cwd().absolute():
            raise ValueError(
                "prometheus_dir cannot be empty, current directory, or resolve to it",
            )
        return value

    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent.parent / ".env",
        env_prefix="",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
