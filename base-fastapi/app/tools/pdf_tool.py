import base64
import os
import tempfile
import uuid
from urllib.parse import urlparse

import httpx

PDF_SIGNATURE = b"%PDF-"
PDF_CONTENT_TYPE = "application/pdf"
PDF_FILE_EXTENSION = ".pdf"
ASHX_FILE_EXTENSION = ".ashx"
PDF_LINK_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0 Safari/537.36"
    ),
    "Accept": "application/pdf,text/html,application/xhtml+xml,*/*;q=0.8",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
}


def _has_pdf_headers(headers: httpx.Headers) -> bool:
    content_type = headers.get("content-type", "").lower()
    if PDF_CONTENT_TYPE in content_type:
        return True

    content_disposition = headers.get("content-disposition", "").lower()
    return PDF_FILE_EXTENSION in content_disposition


def _is_ashx_link(parsed_url) -> bool:
    return parsed_url.path.lower().endswith(ASHX_FILE_EXTENSION)


async def verify_pdf_link(url: str | None, timeout_s: float = 5.0) -> bool:
    if not url:
        return False
    parsed_url = urlparse(url)
    if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
        return False

    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=timeout_s,
            headers=PDF_LINK_HEADERS,
        ) as client:
            try:
                head_response = await client.head(url)
                if head_response.is_success and _has_pdf_headers(head_response.headers):
                    return True
            except httpx.HTTPError:
                pass

            headers = {}
            if not _is_ashx_link(parsed_url):
                headers["Range"] = f"bytes=0-{len(PDF_SIGNATURE) - 1}"

            async with client.stream(
                "GET",
                url,
                headers=headers,
            ) as response:
                if not response.is_success:
                    return False

                if _has_pdf_headers(response.headers):
                    return True

                first_chunk = b""
                async for chunk in response.aiter_bytes():
                    first_chunk += chunk
                    if len(first_chunk) >= len(PDF_SIGNATURE):
                        break

                return first_chunk.startswith(PDF_SIGNATURE)
    except httpx.HTTPError:
        return False


def save_base64_to_pdf(base64_string: str, output_path: str | None = None) -> str:
    if output_path is None:
        output_path = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4()}.pdf")

    with open(output_path, "wb") as f:
        f.write(base64.b64decode(base64_string))

    return output_path


def save_xml_to_file(xml_string: str, output_path: str | None = None) -> str:
    if output_path is None:
        output_path = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4()}.xml")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(xml_string)

    return output_path
