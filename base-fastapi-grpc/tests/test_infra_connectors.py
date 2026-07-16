"""Tests for app/infra/connectors/base_client.py, concurrency.py, http_client_manager.py"""  # noqa: E501
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.infra.connectors.base_client import BaseAsyncHttpConnector, ConnectorConfig
from app.infra.connectors.concurrency import get_http_call_semaphore
from app.infra.connectors.custom_response import CustomResponse
from app.infra.connectors.http_client_manager import HttpClientManager


# ---------------------------------------------------------------------------
# ConnectorConfig
# ---------------------------------------------------------------------------

class TestConnectorConfig:
    def test_defaults(self):
        config = ConnectorConfig(base_url="http://test.com")
        assert config.timeout_s == 10.0
        assert config.service_name is None

    def test_custom_values(self):
        config = ConnectorConfig(base_url="http://test.com", timeout_s=5.0, service_name="TestSvc")  # noqa: E501
        assert config.timeout_s == 5.0
        assert config.service_name == "TestSvc"


# ---------------------------------------------------------------------------
# HttpClientManager
# ---------------------------------------------------------------------------

class TestHttpClientManager:
    def setup_method(self):
        HttpClientManager._client = None

    def test_get_client_creates_singleton(self):
        c1 = HttpClientManager.get_client()
        c2 = HttpClientManager.get_client()
        assert c1 is c2

    @pytest.mark.asyncio
    async def test_close_client_clears_singleton(self):
        HttpClientManager.get_client()
        await HttpClientManager.close_client()
        assert HttpClientManager._client is None

    @pytest.mark.asyncio
    async def test_close_client_noop_when_none(self):
        HttpClientManager._client = None
        await HttpClientManager.close_client()  # Should not raise


# ---------------------------------------------------------------------------
# Concurrency
# ---------------------------------------------------------------------------

class TestConcurrency:
    def test_get_http_call_semaphore_singleton(self):
        import app.infra.connectors.concurrency as conc_module
        conc_module._HTTP_CALL_SEMAPHORE = None
        s1 = get_http_call_semaphore()
        s2 = get_http_call_semaphore()
        assert s1 is s2
        assert isinstance(s1, asyncio.Semaphore)


# ---------------------------------------------------------------------------
# BaseAsyncHttpConnector
# ---------------------------------------------------------------------------

def _make_connector(base_url="http://example.com", timeout=5.0):
    return BaseAsyncHttpConnector(
        ConnectorConfig(base_url=base_url, timeout_s=timeout, service_name="TestSvc")
    )


class TestBaseAsyncHttpConnectorMakeUrl:
    def test_absolute_url_returned_as_is(self):
        conn = _make_connector()
        assert conn._make_url("https://other.com/path") == "https://other.com/path"

    def test_relative_path_joined_with_base(self):
        conn = _make_connector("http://example.com/api/")
        url = conn._make_url("resource")
        assert "resource" in url

    def test_context_manager(self):
        conn = _make_connector()
        assert conn._config.timeout_s == 5.0


class TestBaseAsyncHttpConnectorRequest:
    def _make_mock_http_response(self, status_code=200, text='{"ok":true}'):
        mock = MagicMock(spec=httpx.Response)
        mock.status_code = status_code
        mock.text = text
        mock.is_success = (status_code < 400)
        mock.json.return_value = {"ok": True}
        return mock

    @pytest.mark.asyncio
    async def test_successful_get_request(self):
        conn = _make_connector()
        mock_resp = self._make_mock_http_response()
        conn._client.request = AsyncMock(return_value=mock_resp)
        result = await conn.request(method="GET", path_or_url="http://example.com/test")
        assert isinstance(result, CustomResponse)
        assert result.status_code == 200

    @pytest.mark.asyncio
    async def test_request_with_dict_body(self):
        conn = _make_connector()
        mock_resp = self._make_mock_http_response()
        conn._client.request = AsyncMock(return_value=mock_resp)
        result = await conn.request(
            method="POST",
            path_or_url="http://example.com/test",
            body={"key": "value"},
        )
        assert result.status_code == 200
        call_kwargs = conn._client.request.call_args.kwargs
        assert "json" in call_kwargs

    @pytest.mark.asyncio
    async def test_request_with_list_body(self):
        conn = _make_connector()
        mock_resp = self._make_mock_http_response()
        conn._client.request = AsyncMock(return_value=mock_resp)
        result = await conn.request(
            method="POST",
            path_or_url="http://example.com/test",
            body=["item1", "item2"],
        )
        assert result.status_code == 200
        call_kwargs = conn._client.request.call_args.kwargs
        assert "json" in call_kwargs

    @pytest.mark.asyncio
    async def test_request_with_bytes_body(self):
        conn = _make_connector()
        mock_resp = self._make_mock_http_response()
        conn._client.request = AsyncMock(return_value=mock_resp)
        result = await conn.request(
            method="POST",
            path_or_url="http://example.com/test",
            body=b"raw bytes",
        )
        assert result.status_code == 200
        call_kwargs = conn._client.request.call_args.kwargs
        assert "content" in call_kwargs

    @pytest.mark.asyncio
    async def test_request_with_data(self):
        conn = _make_connector()
        mock_resp = self._make_mock_http_response()
        conn._client.request = AsyncMock(return_value=mock_resp)
        result = await conn.request(
            method="POST",
            path_or_url="http://example.com/test",
            data={"field": "val"},
        )
        assert result.status_code == 200

    @pytest.mark.asyncio
    async def test_timeout_exception_returns_is_timeout(self):
        conn = _make_connector()
        conn._client.request = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
        result = await conn.request(method="GET", path_or_url="http://example.com/test")
        assert result.is_timeout is True

    @pytest.mark.asyncio
    async def test_pool_timeout_returns_is_timeout(self):
        conn = _make_connector()
        conn._client.request = AsyncMock(side_effect=httpx.PoolTimeout("pool timeout"))
        result = await conn.request(method="GET", path_or_url="http://example.com/test")
        assert result.is_timeout is True

    @pytest.mark.asyncio
    async def test_other_exception_is_reraised(self):
        conn = _make_connector()
        conn._client.request = AsyncMock(side_effect=RuntimeError("unexpected"))
        with pytest.raises(RuntimeError):
            await conn.request(method="GET", path_or_url="http://example.com/test")

    @pytest.mark.asyncio
    async def test_uses_effective_timeout_from_config(self):
        conn = _make_connector(timeout=3.0)
        mock_resp = self._make_mock_http_response()
        conn._client.request = AsyncMock(return_value=mock_resp)
        await conn.request(method="GET", path_or_url="http://example.com/test")
        call_kwargs = conn._client.request.call_args.kwargs
        assert call_kwargs["timeout"] == 3.0

    @pytest.mark.asyncio
    async def test_custom_timeout_s_overrides_config(self):
        conn = _make_connector(timeout=3.0)
        mock_resp = self._make_mock_http_response()
        conn._client.request = AsyncMock(return_value=mock_resp)
        await conn.request(
            method="GET",
            path_or_url="http://example.com/test",
            timeout_s=15.0,
        )
        call_kwargs = conn._client.request.call_args.kwargs
        assert call_kwargs["timeout"] == 15.0

    @pytest.mark.asyncio
    async def test_request_with_params(self):
        conn = _make_connector()
        mock_resp = self._make_mock_http_response()
        conn._client.request = AsyncMock(return_value=mock_resp)
        result = await conn.request(
            method="GET",
            path_or_url="http://example.com/test",
            params={"q": "test"},
        )
        assert result.status_code == 200

    @pytest.mark.asyncio
    async def test_no_service_name_uses_downstream(self):
        conn = BaseAsyncHttpConnector(
            ConnectorConfig(base_url="http://example.com", timeout_s=5.0)
        )
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.text = "{}"
        mock_resp.is_success = True
        conn._client.request = AsyncMock(return_value=mock_resp)
        result = await conn.request(method="GET", path_or_url="http://example.com/test")
        assert result.status_code == 200

    @pytest.mark.asyncio
    async def test_aclose_noop_when_not_owns_client(self):
        conn = _make_connector()
        await conn.aclose()  # Should not raise

    @pytest.mark.asyncio
    async def test_aclose_closes_client_when_owns(self):
        conn = _make_connector()
        conn._owns_client = True
        conn._client.aclose = AsyncMock()
        await conn.aclose()
        conn._client.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_context_manager_protocol(self):
        conn = _make_connector()
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.text = "{}"
        mock_resp.is_success = True
        conn._client.request = AsyncMock(return_value=mock_resp)
        async with conn as c:
            result = await c.request(method="GET", path_or_url="http://example.com")
        assert result.status_code == 200
