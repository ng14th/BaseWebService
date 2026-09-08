from fastapi import FastAPI
from loguru import logger

from core.db.engine_routing import (
    READ_ENGINE,
    WRITE_ENGINE,
    dispose_engines,
)
from core.db.session import AsyncAutoSession, AsyncReadSession, AsyncWriteSession


def setup_database(app: FastAPI) -> None:  # pragma: no cover

    app.state.read_session_factory = AsyncReadSession
    app.state.write_session_factory = AsyncWriteSession
    app.state.auto_session_factory = AsyncAutoSession
    logger.info("Database session factories initialized")


__all__ = ["setup_database", "dispose_engines"]
