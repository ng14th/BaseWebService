# -*- coding: utf-8 -*-
from typing import Any


class ErrorResponseException(Exception):
    def __init__(
        self,
        success: bool = False,
        status_code: int = 400,
        message: str = "",
        data: Any | None = None,
        extra: dict | None = None,
        traceback: str | None = None,
    ):
        super().__init__(message)
        self.success: bool = success
        self.status_code: int = status_code
        self.message: str = message
        self.data: Any = [] if data is None else data
        self.extra: dict | None = {} if extra is None else extra
        self.traceback: str | None = traceback


class ErrorHtmlResponseException(Exception):
    def __init__(self, error: str):
        self.error = error
