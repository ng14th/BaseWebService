# -*- coding: utf-8 -*-
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal, Mapping

from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from core.logging.log import get_trace_id_span_id

SameSite = Literal["lax", "strict", "none"]


@dataclass(slots=True)
class CookieOptions:
    key: str
    value: str

    max_age: int | None = None
    expires: datetime | str | int | None = None

    path: str = "/"
    domain: str | None = None

    secure: bool = True
    httponly: bool = True
    samesite: SameSite = "lax"


class ApiResponse(JSONResponse):

    def __init__(
        self,
        status_code: int = 200,
        message: str | None = "",
        data: Any | None = None,
        extra: dict | None = None,
        traceback: str | None = None,
        headers: Mapping[str, str] | None = None,
        cookie: CookieOptions | None = None,
        request_id: str | None = None,
        **kwargs,
    ):
        trace_id, span_id = get_trace_id_span_id()

        response_headers = dict(headers or {})
        response_headers["X-Trace-ID"] = trace_id
        response_headers["X-Span-ID"] = span_id
        if request_id:
            response_headers["X-Request-ID"] = request_id

        success = status_code < 400

        content = {
            "success": success,
            "status_code": status_code,
            "message": message,
            "data": [] if data is None else data,
            "extra": {} if extra is None else extra,
        }

        super().__init__(
            content=jsonable_encoder(content),
            status_code=status_code,
            headers=response_headers,
            **kwargs,
        )

        if cookie is not None:
            self.set_cookie(
                key=cookie.key,
                value=cookie.value,
                max_age=cookie.max_age,
                expires=cookie.expires,
                path=cookie.path,
                domain=cookie.domain,
                secure=cookie.secure,
                httponly=cookie.httponly,
                samesite=cookie.samesite,
            )
