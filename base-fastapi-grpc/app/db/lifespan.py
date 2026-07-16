from fastapi import FastAPI
from loguru import logger

from app.db.engine_routing import READ_ENGINE, WRITE_ENGINE
from app.db.session import AsyncAutoSession, AsyncReadSession, AsyncWriteSession


def setup_database(app: FastAPI) -> None:  # pragma: no cover

    app.state.read_session_factory = AsyncReadSession
    app.state.write_session_factory = AsyncWriteSession
    app.state.auto_session_factory = AsyncAutoSession
    logger.info("Database session factories initialized")


async def dispose_engines() -> None:
    """Dispose global SQLAlchemy engines."""
    await WRITE_ENGINE.dispose()
    await READ_ENGINE.dispose()
