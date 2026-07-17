import pytest
from fastapi import Request, status
from unittest.mock import MagicMock

from app.api.common.dependencies import check_required_auth_header, check_request_id
from core.schemas.server.exception import ErrorResponseException

def test_check_required_auth_header_success():
    request = MagicMock(spec=Request)
    request.headers = {"Authorization": "Bearer token", "X-Client-ID": "client-123"}
    assert check_required_auth_header(request) is True

def test_check_required_auth_header_missing_auth():
    request = MagicMock(spec=Request)
    request.headers = {"X-Client-ID": "client-123"}
    with pytest.raises(ErrorResponseException) as exc:
        check_required_auth_header(request)
    assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED

def test_check_required_auth_header_missing_client_id():
    request = MagicMock(spec=Request)
    request.headers = {"Authorization": "Bearer token"}
    with pytest.raises(ErrorResponseException) as exc:
        check_required_auth_header(request)
    assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED

def test_check_required_auth_header_missing_both():
    request = MagicMock(spec=Request)
    request.headers = {}
    with pytest.raises(ErrorResponseException) as exc:
        check_required_auth_header(request)
    assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED

def test_check_request_id_success():
    request = MagicMock(spec=Request)
    request.headers = {"x-request-id": "req-123"}
    assert check_request_id(request) == "req-123"

def test_check_request_id_missing():
    request = MagicMock(spec=Request)
    request.headers = {}
    with pytest.raises(ErrorResponseException) as exc:
        check_request_id(request)
    assert exc.value.status_code == status.HTTP_400_BAD_REQUEST
