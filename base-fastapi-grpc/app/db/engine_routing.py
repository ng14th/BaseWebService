from __future__ import annotations

import os
from typing import Any

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import NullPool

from app.settings import settings


class EngineFactory:
    """Build database engines from the active environment."""

    POOL_CONFIG: dict[str, Any] = {
        "poolclass": NullPool,
        "connect_args": {
            "statement_cache_size": 0,
            "timeout": settings.db_timeout,
        },
    }

    DEFAULT_CONFIG: dict[str, Any] = {
        "max_overflow": settings.db_max_overflow,
        "pool_size": settings.db_pool_size,
        "pool_timeout": settings.db_pool_timeout,
        "pool_pre_ping": settings.db_pool_pre_ping,
        "pool_recycle": settings.db_pool_recycle,
        "connect_args": {"timeout": settings.db_timeout},
    }

    ENVIRONMENT_CONFIG: dict[str, dict[str, Any]] = {
        "dev": {},
        "cloud": {},
    }

    def __init__(self, environment: str) -> None:
        self.environment = environment.lower()

    def _engine_config(self) -> dict[str, Any]:
        # Overide by setting CELERY_WORKER = 1 to use NullPool for celery worker
        if settings.use_pgbouncer or os.getenv("CELERY_WORKER") == "1":
            config = dict(self.POOL_CONFIG)
        else:
            config = dict(self.DEFAULT_CONFIG)

        env_config = self.ENVIRONMENT_CONFIG.get(self.environment, {})

        # Shallow-merge most keys, but deep-merge connect_args.
        connect_args = dict(config.get("connect_args", {}) or {})
        connect_args.update(env_config.get("connect_args", {}) or {})
        config.update({k: v for k, v in env_config.items() if k != "connect_args"})
        config["connect_args"] = connect_args
        config["echo"] = settings.db_echo
        return config

    def create_engine(self, db_url: str) -> AsyncEngine:
        engine_config = self._engine_config()
        logger.info(
            "Initializing SQLAlchemy engine "
            f"(env={self.environment}, use_pgbouncer={settings.use_pgbouncer}, "
            f"host={settings.db_host}, port={settings.db_port}, db={settings.db_name})",
        )
        return create_async_engine(db_url, **engine_config)

    def create_read_engine(self) -> AsyncEngine:
        return self.create_engine(str(settings.db_read_url))

    def create_write_engine(self) -> AsyncEngine:
        return self.create_engine(str(settings.db_url))


engine_factory = EngineFactory(settings.environment)

logger.info("Creating database engines at import time (READ_ENGINE/WRITE_ENGINE).")
WRITE_ENGINE: AsyncEngine = engine_factory.create_write_engine()
READ_ENGINE: AsyncEngine = engine_factory.create_read_engine()
