from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import Session
from sqlalchemy.sql import Delete, Insert, Update

from core.db.engine_routing import READ_ENGINE, WRITE_ENGINE

SessionMode = Literal["read", "write", "auto"]


class RoutingSession(Session):
    """Session with routing between read/write engines."""

    _PINNED_TO_WRITE_KEY = "pinned_to_write"

    def get_bind(
        self,
        mapper=None,
        clause=None,
        **kw,
    ):
        """Get engine for query."""
        # ORM flushes usually call get_bind() with clause=None, so relying only on
        # Insert/Update/Delete misses write paths such as session.add(...)+flush().
        # Once a session performs any write, pin the rest of the session to WRITE
        # to keep read-after-write consistency inside the same logical transaction.
        if self.info.get(self._PINNED_TO_WRITE_KEY):
            return WRITE_ENGINE.sync_engine

        if self._flushing or isinstance(clause, (Insert, Update, Delete)):
            self.info[self._PINNED_TO_WRITE_KEY] = True
            return WRITE_ENGINE.sync_engine

        return READ_ENGINE.sync_engine


AsyncReadSession = async_sessionmaker(
    bind=READ_ENGINE,
    expire_on_commit=False,
    autoflush=False,
)

AsyncWriteSession = async_sessionmaker(
    bind=WRITE_ENGINE,
    expire_on_commit=False,
    autoflush=False,
)

AsyncAutoSession = async_sessionmaker(
    bind=READ_ENGINE,
    sync_session_class=RoutingSession,
    expire_on_commit=False,
    autoflush=False,
)

MODE_SESSION_FACTORIES: dict[SessionMode, async_sessionmaker[AsyncSession]] = {
    "read": AsyncReadSession,
    "write": AsyncWriteSession,
    "auto": AsyncAutoSession,
}


def get_session_factory(mode: SessionMode) -> async_sessionmaker[AsyncSession]:
    return MODE_SESSION_FACTORIES[mode]
