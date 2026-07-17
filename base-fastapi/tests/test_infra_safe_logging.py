"""Tests for app/infra/connectors/safe_logging.py"""

import pytest

from core.infra.connectors.safe_logging import (
    is_sensitive_key,
    redact_and_truncate,
    redact_sensitive_data,
    safe_log_body,
)


class TestIsSensitiveKey:
    def test_authorization_key(self):
        assert is_sensitive_key("Authorization") is True

    def test_password_key(self):
        assert is_sensitive_key("password") is True

    def test_secret_key(self):
        assert is_sensitive_key("SECRET_KEY") is True

    def test_token_key(self):
        assert is_sensitive_key("access_token") is True

    def test_api_key(self):
        assert is_sensitive_key("api_key") is True

    def test_apikey(self):
        assert is_sensitive_key("apikey") is True

    def test_non_sensitive_key(self):
        assert is_sensitive_key("Content-Type") is False

    def test_non_sensitive_number_key(self):
        assert is_sensitive_key(42) is False


class TestRedactAndTruncate:
    def test_redacts_sensitive_dict_key(self):
        result = redact_and_truncate({"Authorization": "Bearer abc123"})
        assert result["Authorization"] == "***"

    def test_keeps_non_sensitive_dict_key(self):
        result = redact_and_truncate({"Content-Type": "application/json"})
        assert result["Content-Type"] == "application/json"

    def test_truncates_long_string(self):
        long_str = "x" * 600
        result = redact_and_truncate(long_str)
        assert result.endswith(f"... [truncated, total {len(long_str)} chars]")
        assert result.startswith("x" * 500)

    def test_short_string_not_truncated(self):
        short_str = "hello"
        result = redact_and_truncate(short_str)
        assert result == "hello"

    def test_redacts_list_of_dicts(self):
        result = redact_and_truncate([{"token": "secret123"}, {"name": "test"}])
        assert result[0]["token"] == "***"
        assert result[1]["name"] == "test"

    def test_nested_dict(self):
        result = redact_and_truncate({"outer": {"password": "pass123", "id": 1}})
        assert result["outer"]["password"] == "***"
        assert result["outer"]["id"] == 1

    def test_non_string_value_unchanged(self):
        result = redact_and_truncate({"count": 42})
        assert result["count"] == 42

    def test_none_value(self):
        result = redact_and_truncate(None)
        assert result is None

    def test_custom_max_len(self):
        result = redact_and_truncate("abcdef", max_str_len=3)
        assert result == "abc... [truncated, total 6 chars]"


class TestRedactSensitiveData:
    def test_delegates_to_redact_and_truncate(self):
        result = redact_sensitive_data({"Authorization": "Bearer token"})
        assert result["Authorization"] == "***"


class TestSafeLogBody:
    def test_valid_json_string_parsed_and_redacted(self):
        import json

        body = json.dumps({"Authorization": "Bearer token", "name": "test"})
        result = safe_log_body(body)
        assert result["Authorization"] == "***"
        assert result["name"] == "test"

    def test_invalid_json_string_truncated_directly(self):
        result = safe_log_body("not json {{{{")
        assert result == "not json {{{{"

    def test_dict_input(self):
        result = safe_log_body({"password": "123", "data": "ok"})
        assert result["password"] == "***"
        assert result["data"] == "ok"

    def test_list_input(self):
        result = safe_log_body([{"token": "abc"}])
        assert result[0]["token"] == "***"

    def test_none_input(self):
        result = safe_log_body(None)
        assert result is None

    def test_long_json_string_value_truncated(self):
        import json

        body = json.dumps({"Data": "B" * 600})
        result = safe_log_body(body)
        assert "truncated" in result["Data"]
