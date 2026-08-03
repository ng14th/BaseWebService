"""Tests for app/infra/connectors/custom_response.py"""
import pytest
from unittest.mock import MagicMock

from core.infra.connectors.custom_response import CustomResponse


def _make_mock_response(status_code=200, json_data=None, text="", is_success=True):
    mock = MagicMock()
    mock.status_code = status_code
    mock.is_success = is_success
    mock.text = text
    mock.json.return_value = json_data or {}
    mock.headers = {"content-type": "application/json"}
    return mock


class TestCustomResponse:

    def test_json_returns_parsed_json(self):
        mock_resp = _make_mock_response(json_data={"key": "value"})
        cr = CustomResponse(response=mock_resp, execute_time_ms=100, source_service="svc")
        assert cr.json == {"key": "value"}

    def test_json_returns_empty_dict_on_parse_error(self):
        mock_resp = _make_mock_response()
        mock_resp.json.side_effect = Exception("parse error")
        cr = CustomResponse(response=mock_resp, execute_time_ms=100, source_service="svc")
        assert cr.json == {}

    def test_json_returns_empty_dict_when_timeout(self):
        cr = CustomResponse(response=None, execute_time_ms=100, source_service="svc", is_timeout=True)  # noqa: E501
        assert cr.json == {}

    def test_json_returns_empty_dict_when_no_response(self):
        cr = CustomResponse(response=None, execute_time_ms=100, source_service="svc")
        assert cr.json == {}

    def test_status_code_returns_value(self):
        mock_resp = _make_mock_response(status_code=200)
        cr = CustomResponse(response=mock_resp, execute_time_ms=50, source_service="svc")
        assert cr.status_code == 200

    def test_status_code_returns_400_on_no_response(self):
        cr = CustomResponse(response=None, execute_time_ms=50, source_service="svc")
        assert cr.status_code == 400

    def test_status_code_returns_400_on_timeout(self):
        mock_resp = _make_mock_response(status_code=200)
        cr = CustomResponse(response=mock_resp, execute_time_ms=50, source_service="svc", is_timeout=True)  # noqa: E501
        assert cr.status_code == 400

    def test_text_returns_response_text(self):
        mock_resp = _make_mock_response(text="hello")
        cr = CustomResponse(response=mock_resp, execute_time_ms=50, source_service="svc")
        assert cr.text == "hello"

    def test_text_returns_none_when_no_response(self):
        cr = CustomResponse(response=None, execute_time_ms=50, source_service="svc")
        assert cr.text is None

    def test_text_returns_none_on_timeout(self):
        mock_resp = _make_mock_response(text="some text")
        cr = CustomResponse(response=mock_resp, execute_time_ms=50, source_service="svc", is_timeout=True)  # noqa: E501
        assert cr.text is None

    def test_headers_returns_response_headers(self):
        mock_resp = _make_mock_response()
        cr = CustomResponse(response=mock_resp, execute_time_ms=50, source_service="svc")
        assert cr.headers is not None

    def test_headers_returns_none_when_no_response(self):
        cr = CustomResponse(response=None, execute_time_ms=50, source_service="svc")
        assert cr.headers is None

    def test_headers_returns_none_on_timeout(self):
        mock_resp = _make_mock_response()
        cr = CustomResponse(response=mock_resp, execute_time_ms=50, source_service="svc", is_timeout=True)  # noqa: E501
        assert cr.headers is None

    def test_success_true_when_response_is_success(self):
        mock_resp = _make_mock_response(is_success=True)
        cr = CustomResponse(response=mock_resp, execute_time_ms=50, source_service="svc")
        assert cr.success is True

    def test_success_false_when_response_is_failure(self):
        mock_resp = _make_mock_response(is_success=False)
        cr = CustomResponse(response=mock_resp, execute_time_ms=50, source_service="svc")
        assert cr.success is False

    def test_success_false_when_no_response(self):
        cr = CustomResponse(response=None, execute_time_ms=50, source_service="svc")
        assert cr.success is False

    def test_timeout_msg_error_returns_message_when_timeout(self):
        cr = CustomResponse(response=None, execute_time_ms=50, source_service="MySvc", is_timeout=True)  # noqa: E501
        assert "MySvc" in cr.timeout_msg_error

    def test_timeout_msg_error_returns_none_when_not_timeout(self):
        mock_resp = _make_mock_response()
        cr = CustomResponse(response=mock_resp, execute_time_ms=50, source_service="svc")
        assert cr.timeout_msg_error is None

    def test_circuit_open_msg_error_returns_message_when_open(self):
        cr = CustomResponse(
            response=None,
            execute_time_ms=50,
            source_service="MySvc",
            is_circuit_open=True,
        )
        assert "MySvc" in cr.circuit_open_msg_error

    def test_circuit_open_msg_error_returns_none_when_not_open(self):
        mock_resp = _make_mock_response()
        cr = CustomResponse(response=mock_resp, execute_time_ms=50, source_service="svc")
        assert cr.circuit_open_msg_error is None
