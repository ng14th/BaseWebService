import json
from typing import Any

SENSITIVE_KEYWORDS = (
    "authorization",
    "password",
    "secret",
    "token",
    "api_key",
    "apikey",
)


def is_sensitive_key(key: Any) -> bool:
    key_text = str(key).lower()
    return any(keyword in key_text for keyword in SENSITIVE_KEYWORDS)


def redact_and_truncate(value: Any, max_str_len: int = 500) -> Any:
    if isinstance(value, dict):
        return {
            key: (
                "***"
                if is_sensitive_key(key)
                else redact_and_truncate(item, max_str_len)
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_and_truncate(item, max_str_len) for item in value]
    if isinstance(value, (tuple, set)):
        return [redact_and_truncate(item, max_str_len) for item in list(value)[:100]]
    if isinstance(value, str):
        if len(value) > max_str_len:
            return value[:max_str_len] + f"... [truncated, total {len(value)} chars]"
    return value


def redact_sensitive_data(value: Any) -> Any:
    return redact_and_truncate(value)


def safe_log_body(value: Any) -> Any:
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return redact_and_truncate(parsed)
        except Exception:
            return redact_and_truncate(value)
    return redact_and_truncate(value)
