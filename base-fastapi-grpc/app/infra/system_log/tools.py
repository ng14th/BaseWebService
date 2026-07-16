import json
from dataclasses import asdict, is_dataclass

from fastapi import Request
from pydantic import BaseModel
from starlette.responses import Response

from app.settings import settings
from app.tools.redaction import redact_sensitive_data


def _parse_response_body(response_data):
    """Parse response body bytes to dict once. Returns dict or None."""
    content = getattr(response_data, "body", None)
    if isinstance(content, bytes):
        try:
            return json.loads(content.decode("utf-8"))
        except Exception:
            return None
    return None


def serialize_for_log(value, _visited=None):
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, bytes):
        return _size_marker(value)

    if _visited is None:
        _visited = set()

    # Avoid infinite recursion
    if id(value) in _visited:
        return f"<recursive {type(value).__name__}>"
    _visited.add(id(value))

    # Starlette/FastAPI Response handling
    if isinstance(value, Response):
        content = _parse_response_body(value)
        return {
            "status_code": value.status_code,
            "content_type": value.headers.get("Content-Type"),
            "content": redact_sensitive_data(content),
        }

    # FastAPI Request handling
    if isinstance(value, Request):
        body = getattr(value, "_body", None)
        if isinstance(body, bytes) and len(body) > settings.max_log_body_bytes:
            body = _size_marker(body, truncated=True)
        if (
            isinstance(body, bytes)
            and value.headers.get("Content-Type") == "application/json"
        ):
            try:
                body = json.loads(body.decode("utf-8"))
            except Exception:
                pass
        return {
            "method": value.method,
            "url": str(value.url),
            "client_ip": value.client.host if value.client else None,
            "headers": redact_sensitive_data(
                {
                    k: v
                    for k, v in value.headers.items()
                    if k.lower() not in ("authorization", "cookie")
                }
            ),  # noqa: E501
            "body": _truncate_log_value(redact_sensitive_data(body)),
            "query_params": redact_sensitive_data(dict(value.query_params)),
            "path_params": redact_sensitive_data(getattr(value, "path_params", {})),
        }

    # Pydantic BaseModel handling
    if isinstance(value, BaseModel):
        try:
            return redact_sensitive_data(value.model_dump())
        except Exception:
            return str(value)

    if is_dataclass(value) and not isinstance(value, type):
        try:
            return redact_sensitive_data(asdict(value))
        except Exception:
            return str(value)

    if isinstance(value, dict):
        return _truncate_log_value(
            redact_sensitive_data(
                {str(k): serialize_for_log(v, _visited) for k, v in value.items()}
            )
        )  # noqa: E501

    if isinstance(value, (list, tuple, set)):
        return _truncate_log_value(
            redact_sensitive_data([serialize_for_log(item, _visited) for item in value])
        )

    # Fallback
    return str(value)


def _size_marker(
    value: bytes,
    *,
    truncated: bool = False,
) -> dict[str, int | bool | str]:
    marker: dict[str, int | bool | str] = {
        "type": "bytes",
        "size": len(value),
    }
    if truncated:
        marker["truncated"] = True
    return marker


def _truncate_log_value(value):
    if isinstance(value, str) and len(value) > settings.max_log_body_bytes:
        return value[: settings.max_log_body_bytes] + "... [truncated]"
    if isinstance(value, list) and len(value) > 100:
        return value[:100] + ["... [items truncated]"]
    if isinstance(value, dict):
        try:
            if (
                len(json.dumps(value, default=str).encode("utf-8"))
                > settings.max_log_body_bytes
            ):
                return {"type": "object", "truncated": True}
        except (TypeError, ValueError):
            return {"type": type(value).__name__, "truncated": True}
    return value


def get_browser_info(request):
    return request.headers.get("user-agent", "")


def build_request_query_params(request):
    if request is None:
        return {}
    try:
        prepared_params = dict(request.query_params)
        prepared_params.setdefault(
            "system", prepared_params.get("system") or "unkown"
        )  # noqa: E501
        return prepared_params
    except Exception:
        return {}


def get_response_message(response_data):
    if isinstance(response_data, Response):
        content = _parse_response_body(response_data)
        if isinstance(content, dict):
            return content.get("message") or content.get("messages")
        return None
    if isinstance(response_data, dict):
        return response_data.get("message") or response_data.get("messages")
    return getattr(response_data, "message", None)


def get_response_status_code(response_data):
    if isinstance(response_data, Response):
        return response_data.status_code
    if isinstance(response_data, dict):
        return response_data.get("status_code")
    return getattr(response_data, "status_code", None)


def get_response_status_code_partner(response_data):
    content = None
    if isinstance(response_data, Response):
        content = _parse_response_body(response_data)
    elif isinstance(response_data, dict):
        content = response_data

    if isinstance(content, dict):
        extra = content.get("extra", {})
        if not extra:
            return response_data.status_code
        resp_partner = extra.get("resp_partner", {})
        if not resp_partner:
            return response_data.status_code
        return resp_partner.get("status_code") or resp_partner.get("status")
    return getattr(response_data, "status_code_partner", None)


def get_execution_time_partner(response_data):
    content = None
    if isinstance(response_data, Response):
        content = _parse_response_body(response_data)
    elif isinstance(response_data, dict):
        content = response_data

    if isinstance(content, dict):
        extra = content.get("extra", {})
        if not extra:
            return 0.0
        resp_partner = extra.get("resp_partner", {})
        if not resp_partner:
            return 0.0
        return resp_partner.get("execution_time", 0.0)
    return 0.0


def get_response_success(response_data):
    if isinstance(response_data, Response):
        return response_data.status_code < 400
    if isinstance(response_data, dict):
        if "success" in response_data:
            return response_data.get("success")
        if "error" in response_data:
            return not response_data.get("error")
        status_code = get_response_status_code(response_data)
        try:
            return status_code is not None and int(status_code) < 400
        except (ValueError, TypeError):
            return False
    success = getattr(response_data, "success", None)
    if success is not None:
        return success
    status_code = get_response_status_code(response_data)
    try:
        return status_code is not None and int(status_code) < 400
    except (ValueError, TypeError):
        return False
