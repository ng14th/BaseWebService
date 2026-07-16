from contextvars import ContextVar

grpc_deadline_remaining: ContextVar[float | None] = ContextVar(
    "grpc_deadline_remaining",
    default=None,
)
