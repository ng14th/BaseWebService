from __future__ import annotations

from contextvars import ContextVar, Token

from sqlalchemy.ext.asyncio import AsyncSession

_current_session: ContextVar[AsyncSession | None] = ContextVar(
    "current_db_session",
    default=None,
)


class AutoSession:
    @staticmethod
    def get() -> AsyncSession:
        session = _current_session.get()
        if session is None:
            raise RuntimeError(
                "No active database session in context. "
                "Use session_scope/managed_session or pass session explicitly.",
            )
        return session

    @staticmethod
    def set(session: AsyncSession) -> Token:
        return _current_session.set(session)

    @staticmethod
    def reset(token: Token) -> None:
        _current_session.reset(token)
