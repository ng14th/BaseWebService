from sqlalchemy.ext.asyncio import AsyncSession

from .auto_session import AutoSession


class BaseRepository:
    """Base repository.

    Prefer passing ``session`` explicitly at service boundaries. The AutoSession
    fallback is kept for legacy gRPC call paths that run inside ``session_scope``.
    """

    def __init__(self, session: AsyncSession | None = None) -> None:
        # auto get session from context if not provided
        self.session = session or AutoSession.get()

    @staticmethod
    def _audit_entity_fields(model: object) -> dict[str, str | None]:
        return {
            "created_by": getattr(model, "created_by", None),
            "updated_by": getattr(model, "updated_by", None),
            "time_created": getattr(model, "get_time_created", None) or None,
            "time_updated": getattr(model, "get_time_updated", None) or None,
        }
