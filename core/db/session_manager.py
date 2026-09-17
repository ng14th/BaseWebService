import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from loguru import logger
from sqlalchemy import ClauseElement, event
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio.session import async_sessionmaker

from core.db.engine_routing import READ_ENGINE, WRITE_ENGINE

from .auto_session import AutoSession
from .session import SessionMode, get_session_factory


def compile_sql(statement: ClauseElement):
    logger.info(str(statement.compile(compile_kwargs={"literal_binds": True})))


def _format_sql_param(param):
    if param is None:
        return "NULL"
    if isinstance(param, (int, float)):
        return str(param)
    if isinstance(param, bool):
        return "TRUE" if param else "FALSE"
    return f"'{str(param)}'"


@event.listens_for(WRITE_ENGINE.sync_engine, "before_cursor_execute")
@event.listens_for(READ_ENGINE.sync_engine, "before_cursor_execute")
def receive_before_cursor_execute(
    conn,
    cursor,
    statement,
    parameters,
    context,
    executemany,
):
    is_enable_log_sql = os.getenv("ENABLE_LOG_SQL", "false").lower() == "true"
    if is_enable_log_sql:
        sql_msg = statement.replace("\n", " ").strip()
        if parameters:
            if isinstance(parameters, (tuple, list)):
                # Handle positional params (e.g., $1, $2)
                for i in range(len(parameters), 0, -1):
                    val = _format_sql_param(parameters[i - 1])
                    sql_msg = sql_msg.replace(f"${i}", val)
            elif isinstance(parameters, dict):
                # Handle named params (e.g., %(name)s)
                for k, v in parameters.items():
                    val = _format_sql_param(v)
                    sql_msg = sql_msg.replace(f"%({k})s", val)

        logger.info(f"Executing SQL: {sql_msg}")


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
