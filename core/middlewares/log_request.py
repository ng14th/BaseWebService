import asyncio
import json
import time
import traceback
from datetime import datetime, timezone

from fastapi import Request
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from core.infra.system_log.mongo import MongoSystemEventLogger
from core.infra.system_log.tools import (
    build_request_query_params,
    get_browser_info,
    get_execution_time_partner,
    get_response_message,
    get_response_status_code,
    get_response_status_code_partner,
    get_response_success,
    serialize_for_log,
)
from core.logging.log import get_trace_id_span_id
from core.utils.uuid_utils import get_uuid_v4_str

WRITE_METHODS = {"PUT", "POST", "PATCH", "DELETE"}
DEFAULT_SYSTEM_PARTNER = "Unknown"


class LogRequestMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log API calls to MongoDB.
    """

    def __init__(
        self,
        app,
        *,
        table: str,
        request_partner_key: str,
    ) -> None:
        super().__init__(app)
        self.table = table
        self.request_partner_key = request_partner_key

    def get_request_id(self, request: Request):
        if hasattr(request.state, "request_id"):
            return request.state.request_id

        request_id = ""
        try:
            body_bytes = getattr(request, "_body", b"")
            if body_bytes:
                body_json = json.loads(body_bytes)
                if isinstance(body_json, dict):
                    request_id = body_json.get("request_id", "")
        except Exception:
            pass

        if not request_id:
            request_id = request.headers.get("x-request-id", "")

        if not request_id:
            request_id = get_uuid_v4_str()

        request.state.request_id = request_id
        return request_id

    async def _log_api_call(
        self,
        request_partner: str,
        request: Request,
        response: Response,
        execution_time: float,
        table: str,
    ):
        try:
            await self._do_log_api_call(
                request_partner,
                request,
                response,
                execution_time,
                table,
            )
        except Exception:
            logger.warning(
                "Failed to log API call to MongoDB: {}", traceback.format_exc()
            )

    async def _do_log_api_call(
        self,
        request_partner: str,
        request: Request,
        response: Response,
        execution_time: float,
        table: str,
    ):

        now = datetime.now(timezone.utc)

        response_data_logged = serialize_for_log(response)
        if hasattr(request.state, "traceback") and isinstance(
            response_data_logged, dict
        ):
            response_data_logged["traceback"] = request.state.traceback

        # extract request id
        request_id = self.get_request_id(request)
        trace_id, _ = get_trace_id_span_id()

        log_data = {
            "system_partner": request_partner,
            "method_call": request.method,
            "return_type": "JSON",
            "base_uri": request.url.path,
            "url": request.url.path,
            "request_time": now,
            "time_created": now.timestamp(),
            "request_data": serialize_for_log(request),
            "query_params": (
                serialize_for_log(build_request_query_params(request))
                if request.method not in WRITE_METHODS
                else {}
            ),
            "response_data": response_data_logged,
            "status_code": get_response_status_code(response),
            "execution_time": execution_time,
            "status_code_partner": get_response_status_code_partner(
                response
            ),  # noqa: E501
            "execution_time_partner": get_execution_time_partner(response),
            "message": get_response_message(response),
            "success": get_response_success(response),
            "request_id": request_id,
            "trace_id": trace_id,
            "ip_update": request.client.host if request.client else None,
            "browser_update": get_browser_info(request),
        }

        await MongoSystemEventLogger(
            table=table,
            body=log_data,
        ).insert_action()

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        trace_id, span_id = get_trace_id_span_id()

        # Read request body early for write methods so it's cached for logging
        if request.method in WRITE_METHODS:
            try:
                await request.body()
            except Exception:
                pass

        request_id = self.get_request_id(request)
        request_data_logged = serialize_for_log(request)

        with logger.contextualize(
            trace_id=trace_id, span_id=span_id, request_id=request_id
        ):
            logger.info(
                "Incoming request: {} {} | client_ip={} | query_params={} | body={}",
                request.method,
                request.url.path,
                request_data_logged.get("client_ip"),
                request_data_logged.get("query_params", {}),
                request_data_logged.get("body"),
            )

            response = await call_next(request)

        execution_time = time.time() - start_time
        request_partner = DEFAULT_SYSTEM_PARTNER

        # To log the response body without 'transforming' it, we must still
        # consume the stream and recreate the response object.
        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            body = [chunk async for chunk in response.body_iterator]
            full_body = b"".join(body)
            try:
                response_content = json.loads(full_body.decode("utf-8"))
                extra = response_content.get("extra", {})
                request_partner = (
                    extra.get(self.request_partner_key) or DEFAULT_SYSTEM_PARTNER
                )
            except Exception:
                request_partner = DEFAULT_SYSTEM_PARTNER

            # Recreate response with EXACTLY the same status and content
            headers = dict(response.headers)
            if not headers.get("x-request-id"):
                headers["x-request-id"] = self.get_request_id(request)
            headers.pop("content-length", None)
            response = Response(
                content=full_body,
                status_code=response.status_code,
                headers=headers,
                media_type=response.media_type,
            )

        # log to mongo in background
        asyncio.create_task(
            self._log_api_call(
                request_partner,
                request,
                response,
                execution_time,
                self.table,
            )
        )

        return response
