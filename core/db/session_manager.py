from contextlib import asynccontextmanager
from typing import AsyncGenerator

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio.session import async_sessionmaker

from .auto_session import AutoSession
from .session import SessionMode, get_session_factory


@asynccontextmanager
async def managed_session(
    factory: async_sessionmaker[AsyncSession],
    mode: SessionMode,
) -> AsyncGenerator[AsyncSession, None]:
    """Open, manage, and close a session from the given factory."""
    session = factory()
    try:
        yield session
        if mode != "read":
            logger.debug(f"Committing session {id(session)} with {mode=}")
            await session.commit()

            for callback in session.sync_session.info.pop("after_commit_callbacks", []):
                try:
                    callback()
                except Exception as e:
                    logger.exception(
                        f"Error running after-commit callback {callback}: {e}"
                    )

    except Exception:
        if mode != "read":
            logger.debug(f"Rolling back session {id(session)} with {mode=}")
            await session.rollback()
            session.sync_session.info.pop("after_commit_callbacks", None)
        raise
    finally:
        try:
            await session.close()
            logger.debug(f"Close session {id(session)} with {mode=}")
        except Exception as e:
            logger.warning(f"Error closing session {id(session)}: {e}")


@asynccontextmanager
async def session_scope(
    mode: SessionMode = "auto",
    enable_auto_session: bool = False,
) -> AsyncGenerator[AsyncSession, None]:
    """Session scope for gRPC/services."""
    async with managed_session(get_session_factory(mode), mode) as session:
        logger.debug(f"Open session {id(session)} with {mode=}")
        if enable_auto_session:
            token = AutoSession.set(session)
            try:
                yield session
            finally:
                AutoSession.reset(token)
        else:
            yield session
