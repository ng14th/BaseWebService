import json
from collections.abc import Mapping
from typing import Any

REDACTED = "[REDACTED]"

SENSITIVE_KEYS = {
    "authorization",
    "cookie",
    "set-cookie",
    "password",
    "client_secret",
    "access_token",
    "refresh_token",
    "auth_token",
    "token",
    "api_key",
    "apikey",
    "secret",
}


def _is_sensitive_key(key: Any) -> bool:
    normalized = str(key).lower().replace("-", "_")
    return normalized in SENSITIVE_KEYS or normalized.endswith("_token")


def redact_sensitive_data(value: Any, _visited: set[int] | None = None) -> Any:
    if value is None or isinstance(value, (int, float, bool)):
        return value

    if isinstance(value, str):
        stripped = value.strip()
        if stripped.startswith(("{", "[")):
            try:
                return redact_sensitive_data(json.loads(stripped), _visited)
            except (TypeError, ValueError, json.JSONDecodeError):
                return value
        return value

    if _visited is None:
        _visited = set()

    value_id = id(value)
    if value_id in _visited:
        return f"<recursive {type(value).__name__}>"
    _visited.add(value_id)

    if isinstance(value, Mapping):
        return {
            str(key): (
                REDACTED
                if _is_sensitive_key(key)
                else redact_sensitive_data(item, _visited)
            )
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple, set)):
        return [redact_sensitive_data(item, _visited) for item in list(value)[:100]]

    return value
