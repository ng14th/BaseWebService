# -*- coding: utf-8 -*-
from typing import Any

from fastapi.responses import JSONResponse

from app.log import get_trace_id_span_id


class ApiResponse(JSONResponse):

    def __init__(
        self,
        status_code: int = 200,
        message: str | None = "",
        data: Any | None = None,
        extra: dict | None = None,
        traceback: str | None = None,
        headers: dict[str, str] | None = None,
        **kwargs,
    ):
        # add trace_id and span_id to headers
        trace_id, span_id = get_trace_id_span_id()
        headers = headers or {}
        headers["X-Trace-ID"] = trace_id
        headers["X-Span-ID"] = span_id

        # set success status
        success = status_code < 400

        # build response content
        content = {
            "success": success,
            "status_code": status_code,
            "message": message,
            "data": [] if data is None else data,
            "extra": {} if extra is None else extra,
        }

        # init JSONResponse
        super().__init__(content, status_code, headers, **kwargs)
