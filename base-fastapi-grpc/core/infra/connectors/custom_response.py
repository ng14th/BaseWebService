from dataclasses import dataclass
from typing import Any, Mapping

import httpx
from loguru import logger


@dataclass
class CustomResponse:
    response: httpx.Response | None
    execute_time_ms: float | int
    source_service: str
    is_timeout: bool = False

    @property
    def json(self) -> Any:
        if self.response and not self.is_timeout:
            try:
                return self.response.json()
            except Exception as exc:
                logger.error(
                    f"[ERROR] parse json request {self.source_service} "
                    f"| response={self.response}: {exc}",
                )
                return {}
        return {}

    @property
    def status_code(self) -> int:
        if self.response and not self.is_timeout:
            return self.response.status_code
        return 400

    @property
    def text(self) -> str | None:
        if self.response and not self.is_timeout:
            return self.response.text
        return None

    @property
    def headers(self) -> Mapping[str, str] | None:
        if self.response and not self.is_timeout:
            return self.response.headers
        return None

    @property
    def success(self) -> bool:
        if self.response:
            return self.response.is_success
        return False

    @property
    def timeout_msg_error(self) -> str | None:
        if self.is_timeout:
            return f"No response from {self.source_service}. Please retry."
        return None
