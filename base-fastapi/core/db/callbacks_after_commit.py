from typing import Any, Callable

from sqlalchemy.ext.asyncio import AsyncSession


class CallBackAfterCommit:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.callbacks: list[Callable[[], Any]] = (
            self.session.sync_session.info.setdefault("after_commit_callbacks", [])
        )

    def register(self, callback: Callable[[], Any]):
        self.callbacks.append(callback)
