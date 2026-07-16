"""Tests for app/tools/pdf_tool.py"""

import base64
import os
from unittest.mock import AsyncMock, MagicMock, patch
from urllib.parse import urlparse

import httpx
import pytest

from app.tools.pdf_tool import (
    PDF_SIGNATURE,
    _has_pdf_headers,
    _is_ashx_link,
    save_base64_to_pdf,
    save_xml_to_file,
    verify_pdf_link,
)


class TestHasPdfHeaders:
    def test_pdf_content_type(self):
        headers = httpx.Headers({"content-type": "application/pdf"})
        assert _has_pdf_headers(headers) is True

    def test_pdf_content_disposition(self):
        headers = httpx.Headers(
            {"content-disposition": 'attachment; filename="invoice.pdf"'}
        )  # noqa: E501
        assert _has_pdf_headers(headers) is True

    def test_non_pdf_headers(self):
        headers = httpx.Headers({"content-type": "text/html"})
        assert _has_pdf_headers(headers) is False

    def test_empty_headers(self):
        headers = httpx.Headers({})
        assert _has_pdf_headers(headers) is False


class TestIsAshxLink:
    def test_ashx_link(self):
        parsed = urlparse("https://example.com/file.ashx")
        assert _is_ashx_link(parsed) is True

    def test_pdf_link(self):
        parsed = urlparse("https://example.com/file.pdf")
        assert _is_ashx_link(parsed) is False

    def test_ashx_uppercase(self):
        parsed = urlparse("https://example.com/file.ASHX")
        assert _is_ashx_link(parsed) is True


class TestVerifyPdfLink:
    @pytest.mark.asyncio
    async def test_returns_false_for_none_url(self):
        assert await verify_pdf_link(None) is False

    @pytest.mark.asyncio
    async def test_returns_false_for_invalid_scheme(self):
        assert await verify_pdf_link("ftp://example.com/file.pdf") is False

    @pytest.mark.asyncio
    async def test_returns_false_for_no_netloc(self):
        assert await verify_pdf_link("http:///file.pdf") is False

    @pytest.mark.asyncio
    async def test_returns_false_on_http_error(self):
        with patch(
            "app.tools.pdf_tool.httpx.AsyncClient",
            side_effect=httpx.HTTPError("connection error"),
        ):
            result = await verify_pdf_link("http://example.com/file.pdf")
        assert result is False

    @pytest.mark.asyncio
    async def test_returns_true_when_head_has_pdf_content_type(self):
        mock_head = MagicMock()
        mock_head.is_success = True
        mock_head.headers = httpx.Headers({"content-type": "application/pdf"})

        async def fake_aenter(self_):
            return self_

        async def fake_aexit(self_, *args):
            return False

        with patch("httpx.AsyncClient") as MockClient:
            instance = MagicMock()
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            instance.head = AsyncMock(return_value=mock_head)
            MockClient.return_value = instance
            result = await verify_pdf_link("http://example.com/file.pdf")

        assert result is True

    @pytest.mark.asyncio
    async def test_returns_true_when_stream_has_pdf_signature(self):
        mock_head = MagicMock()
        mock_head.is_success = False
        mock_head.headers = httpx.Headers({})

        mock_stream_resp = MagicMock()
        mock_stream_resp.is_success = True
        mock_stream_resp.headers = httpx.Headers({})

        async def aiter_bytes():
            yield PDF_SIGNATURE + b"rest of content"

        mock_stream_resp.aiter_bytes = aiter_bytes
        mock_stream_resp.__aenter__ = AsyncMock(return_value=mock_stream_resp)
        mock_stream_resp.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient") as MockClient:
            instance = MagicMock()
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            instance.head = AsyncMock(return_value=mock_head)
            instance.stream = MagicMock(return_value=mock_stream_resp)
            MockClient.return_value = instance
            result = await verify_pdf_link("http://example.com/file.pdf")

        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_when_stream_response_not_success(self):
        mock_head = MagicMock()
        mock_head.is_success = False
        mock_head.headers = httpx.Headers({})

        mock_stream_resp = MagicMock()
        mock_stream_resp.is_success = False
        mock_stream_resp.headers = httpx.Headers({})
        mock_stream_resp.__aenter__ = AsyncMock(return_value=mock_stream_resp)
        mock_stream_resp.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient") as MockClient:
            instance = MagicMock()
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            instance.head = AsyncMock(return_value=mock_head)
            instance.stream = MagicMock(return_value=mock_stream_resp)
            MockClient.return_value = instance
            result = await verify_pdf_link("http://example.com/file.pdf")

        assert result is False

    @pytest.mark.asyncio
    async def test_ashx_link_no_range_header(self):
        mock_head = MagicMock()
        mock_head.is_success = False
        mock_head.headers = httpx.Headers({})

        mock_stream_resp = MagicMock()
        mock_stream_resp.is_success = True
        mock_stream_resp.headers = httpx.Headers({"content-type": "application/pdf"})
        mock_stream_resp.__aenter__ = AsyncMock(return_value=mock_stream_resp)
        mock_stream_resp.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient") as MockClient:
            instance = MagicMock()
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            instance.head = AsyncMock(return_value=mock_head)
            instance.stream = MagicMock(return_value=mock_stream_resp)
            MockClient.return_value = instance
            # .ashx link
            result = await verify_pdf_link(
                "https://download.meinvoice.vn/handler.ashx?type=pdf"
            )

        assert result is True

    @pytest.mark.asyncio
    async def test_head_http_error_falls_through_to_stream(self):
        mock_stream_resp = MagicMock()
        mock_stream_resp.is_success = True
        mock_stream_resp.headers = httpx.Headers({"content-type": "application/pdf"})
        mock_stream_resp.__aenter__ = AsyncMock(return_value=mock_stream_resp)
        mock_stream_resp.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient") as MockClient:
            instance = MagicMock()
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            instance.head = AsyncMock(side_effect=httpx.HTTPError("head err"))
            instance.stream = MagicMock(return_value=mock_stream_resp)
            MockClient.return_value = instance
            result = await verify_pdf_link("http://example.com/file.pdf")

        assert result is True


class TestSaveBase64ToPdf:
    def test_saves_to_default_tmp_path(self):
        b64 = base64.b64encode(b"%PDF-hello").decode()
        path = save_base64_to_pdf(b64)
        assert os.path.isfile(path)
        assert path.endswith(".pdf")
        os.remove(path)

    def test_saves_to_custom_path(self, tmp_path):
        b64 = base64.b64encode(b"%PDF-world").decode()
        output = str(tmp_path / "custom.pdf")
        result = save_base64_to_pdf(b64, output_path=output)
        assert result == output
        assert os.path.isfile(output)

    def test_content_is_decoded_correctly(self, tmp_path):
        content = b"%PDF-test content"
        b64 = base64.b64encode(content).decode()
        output = str(tmp_path / "check.pdf")
        save_base64_to_pdf(b64, output_path=output)
        with open(output, "rb") as f:
            assert f.read() == content


class TestSaveXmlToFile:
    def test_saves_to_default_tmp_path(self):
        xml = "<root><id>1</id></root>"
        path = save_xml_to_file(xml)
        assert os.path.isfile(path)
        assert path.endswith(".xml")
        os.remove(path)

    def test_saves_to_custom_path(self, tmp_path):
        xml = "<invoice/>"
        output = str(tmp_path / "custom.xml")
        result = save_xml_to_file(xml, output_path=output)
        assert result == output
        assert os.path.isfile(output)

    def test_content_is_correct(self, tmp_path):
        xml = "<root>Misa đơn vị</root>"
        output = str(tmp_path / "content.xml")
        save_xml_to_file(xml, output_path=output)
        with open(output, encoding="utf-8") as f:
            assert f.read() == xml
