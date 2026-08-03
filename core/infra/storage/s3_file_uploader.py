from __future__ import annotations

import asyncio
import dataclasses
from io import BytesIO
from typing import Any
from urllib.parse import quote

import boto3
import botocore.exceptions

from app.settings import settings


@dataclasses.dataclass
class ResultUploadFile:
    success: bool = True
    url: str | None = None
    message: str | None = None


class S3FileUploader:
    def __init__(
        self,
        *,
        s3_client: Any | None = None,
        space_name: str | None = None,
        endpoint_url: str | None = None,
    ) -> None:
        self.space_name = space_name or settings.do_space_name
        self.endpoint_url = (endpoint_url or settings.do_endpoint_url).rstrip("/")
        self.s3 = s3_client or self._build_client()

    def _build_client(self) -> Any:

        session = boto3.session.Session()
        return session.client(
            "s3",
            region_name="sgp1",
            endpoint_url=settings.do_endpoint_url,
            aws_access_key_id=settings.do_access_key,
            aws_secret_access_key=settings.do_secret_key,
        )

    def _build_public_url(self, file_name: str) -> str:
        safe_file_name = quote(file_name.lstrip("/"), safe="/")
        return f"{self.endpoint_url}/{self.space_name}/einvoice/{safe_file_name}"

    async def upload_file_content(
        self,
        file_content: bytes,
        file_name: str,
    ) -> ResultUploadFile:
        try:
            await asyncio.to_thread(
                self.s3.upload_fileobj,
                BytesIO(file_content),
                self.space_name,
                file_name,
                ExtraArgs={"ACL": "public-read"},
            )
            return ResultUploadFile(
                success=True,
                url=self._build_public_url(file_name),
            )
        except self._client_error_exception() as error:
            return ResultUploadFile(
                success=False,
                message=f"Không thể upload file: {error}",
            )

    @staticmethod
    def _client_error_exception():
        return botocore.exceptions.ClientError
