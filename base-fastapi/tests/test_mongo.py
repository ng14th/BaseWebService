# type: ignore
from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import Request
from pydantic import BaseModel
from starlette.responses import Response

from core.infra.system_log.mongo import MongoClientSingleton, MongoSystemEventLogger
from core.infra.system_log.tools import (
    _parse_response_body,
    _truncate_log_value,
    build_request_query_params,
    get_browser_info,
    get_execution_time_partner,
    get_response_message,
    get_response_status_code,
    get_response_status_code_partner,
    get_response_success,
    serialize_for_log,
)
from app.settings.app_settings import settings


@pytest.fixture(autouse=True)
def reset_mongo():
    MongoClientSingleton.reset()
    yield
    MongoClientSingleton.reset()


@pytest.mark.asyncio
async def test_mongo_client_singleton():
    with patch("core.infra.system_log.mongo.AsyncIOMotorClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.close = MagicMock()
        mock_client.return_value = mock_instance

        client1 = await MongoClientSingleton.get_client("mongodb://localhost")
        client2 = await MongoClientSingleton.get_client("mongodb://localhost")

        assert client1 is client2

        MongoClientSingleton.close()
        mock_instance.close.assert_called_once()

        assert MongoClientSingleton._instance is None


@pytest.mark.asyncio
async def test_mongo_system_event_logger():
    with patch(
        "core.infra.system_log.mongo.MongoClientSingleton.get_client"
    ) as mock_get_client:  # noqa: E501
        mock_client = AsyncMock()
        mock_db = MagicMock()
        mock_collection = AsyncMock()

        mock_client.__getitem__.return_value = mock_db
        mock_db.__getitem__.return_value = mock_collection
        mock_get_client.return_value = mock_client

        logger = MongoSystemEventLogger(table="test_table", body={"test": 1})

        # Test get_connection
        conn = await logger.get_connection()
        assert conn is mock_collection

        # Test get_connection_by_table
        conn2 = await MongoSystemEventLogger.get_connection_by_table("test_table")
        assert conn2 is mock_collection

        # Test insert_action
        mock_collection.insert_one.return_value.inserted_id = "123"
        res = await logger.insert_action()
        assert res == "123"

        # Test insert_many_action
        mock_collection.insert_many.return_value = ["123", "456"]
        res_many = await logger.insert_many_action()
        assert res_many == ["123", "456"]

        # Test find_one_action
        mock_collection.find_one.return_value = {"_id": "123", "test": 1}
        res_find = await logger.find_one_action({"_id": "123"})
        assert res_find["test"] == 1

        # Test update_action
        mock_collection.update_one.return_value.modified_count = 1
        res_update = await logger.update_action({"_id": "123"}, {"test": 2})
        assert res_update is True

        # Test transaction
        mock_session = AsyncMock()

        class AsyncContextManagerMock:
            async def __aenter__(self):
                return mock_session

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass

        mock_client.start_session.return_value = AsyncContextManagerMock()
        mock_session.start_transaction = MagicMock(
            return_value=AsyncContextManagerMock()
        )
        async with logger.transaction() as session:
            assert session is mock_session
            mock_session.start_transaction.assert_called_once()


def test_parse_response_body():
    resp = MagicMock()
    resp.body = b'{"msg": "ok"}'
    assert _parse_response_body(resp) == {"msg": "ok"}

    resp.body = b"invalid json"
    assert _parse_response_body(resp) is None

    resp.body = "not bytes"
    assert _parse_response_body(resp) is None


@dataclass
class MockDataClass:
    a: int


class MockPydantic(BaseModel):
    a: int

    # Ensure no warnings
    model_config = {"arbitrary_types_allowed": True}


def test_serialize_for_log():
    assert serialize_for_log(None) is None
    assert serialize_for_log(1) == 1
    assert serialize_for_log(b"test") == {"type": "bytes", "size": 4}

    # Recursive
    lst = []
    lst.append(lst)
    assert "<recursive list>" in serialize_for_log(lst)

    # Response
    resp = Response(
        content=b'{"msg":"ok"}', headers={"Content-Type": "application/json"}
    )
    assert serialize_for_log(resp)["status_code"] == 200

    # Request
    req = MagicMock(spec=Request)
    req._body = b'{"msg":"ok"}'
    req.headers = {"Content-Type": "application/json"}
    req.method = "POST"
    req.url = "http://test"
    req.client.host = "127.0.0.1"
    req.query_params = {}
    req.path_params = {}
    assert serialize_for_log(req)["method"] == "POST"

    # Request invalid body
    req._body = b"invalid"
    assert serialize_for_log(req)["body"] == b"invalid"

    # Pydantic
    assert serialize_for_log(MockPydantic(a=1)) == {"a": 1}

    # Dataclass
    assert serialize_for_log(MockDataClass(a=1)) == {"a": 1}

    # Exceptions
    with patch(
        "core.infra.system_log.tools.redact_sensitive_data", side_effect=Exception("bad")
    ):  # noqa: E501
        assert "MockDataClass" in serialize_for_log(MockDataClass(a=1))
        assert "a=1" in serialize_for_log(MockPydantic(a=1))

    class BadDataClass:
        pass

    assert "BadDataClass" in serialize_for_log(BadDataClass())

    # Dict & List
    assert serialize_for_log({"a": [1, {"b": 2}]}) == {"a": [1, {"b": 2}]}

    # Truncate strings
    long_str = "a" * (settings.max_log_body_bytes + 10)
    assert "... [truncated]" in _truncate_log_value(long_str)

    # Truncate lists
    long_list = list(range(105))
    res_list = _truncate_log_value(long_list)
    assert len(res_list) == 101
    assert res_list[-1] == "... [items truncated]"

    # Truncate large dicts
    long_dict = {"a": "a" * settings.max_log_body_bytes}
    assert _truncate_log_value(long_dict) == {"type": "object", "truncated": True}

    # Dict json serialization error
    class UnserializableClass:
        def __str__(self):
            raise ValueError("cannot serialize")
    bad_dict = {"a": UnserializableClass()}
    assert _truncate_log_value(bad_dict) == {"type": "dict", "truncated": True}

    # Truncate large bytes body in request
    req = MagicMock(spec=Request)
    req.headers = {"Content-Type": "text/plain"}
    req.method = "POST"
    req.url = "http://test"
    req.client.host = "127.0.0.1"
    req.query_params = {}
    req.path_params = {}
    req._body = b"a" * (settings.max_log_body_bytes + 10)
    res_req = serialize_for_log(req)
    assert res_req["body"]["truncated"] is True

    # Fallback
    class Dummy:
        def __str__(self):
            return "dummy"

    assert serialize_for_log(Dummy()) == "dummy"


def test_get_browser_info():
    req = MagicMock()
    req.headers = {"user-agent": "test-agent"}
    assert get_browser_info(req) == "test-agent"


def test_build_request_query_params():
    assert build_request_query_params(None) == {}

    req = MagicMock()
    req.query_params = {"a": "1"}
    assert build_request_query_params(req) == {"a": "1", "system": "unkown"}

    req.query_params = None
    assert build_request_query_params(req) == {}


def test_get_response_message():
    resp = Response(
        content=b'{"message":"ok"}', headers={"Content-Type": "application/json"}
    )  # noqa: E501
    assert get_response_message(resp) == "ok"

    resp_msg = Response(
        content=b'{"messages":"ok2"}', headers={"Content-Type": "application/json"}
    )  # noqa: E501
    assert get_response_message(resp_msg) == "ok2"

    # Response returning dict but no message/messages
    resp_empty = Response(
        content=b'{"data":"ok"}', headers={"Content-Type": "application/json"}
    )
    assert get_response_message(resp_empty) is None

    # Response returning non-dict
    resp_non_dict = Response(
        content=b'"just string"', headers={"Content-Type": "application/json"}
    )
    assert get_response_message(resp_non_dict) is None

    assert get_response_message({"message": "dict_ok"}) == "dict_ok"

    class ObjMsg:
        message = "obj_ok"

    assert get_response_message(ObjMsg()) == "obj_ok"


def test_get_response_status_code():
    resp = Response(content=b"{}", status_code=201)
    assert get_response_status_code(resp) == 201

    assert get_response_status_code({"status_code": 404}) == 404

    class ObjStatus:
        status_code = 500

    assert get_response_status_code(ObjStatus()) == 500


def test_get_response_status_code_partner():
    resp = Response(
        content=b'{"extra":{"resp_partner":{"status_code": 200}}}', status_code=201
    )  # noqa: E501
    assert get_response_status_code_partner(resp) == 200

    resp_status = Response(
        content=b'{"extra":{"resp_partner":{"status": 202}}}', status_code=201
    )  # noqa: E501
    assert get_response_status_code_partner(resp_status) == 202

    # Empty resp_partner
    resp_empty_partner = Response(
        content=b'{"extra":{"resp_partner":{}}}', status_code=201
    )
    assert get_response_status_code_partner(resp_empty_partner) == 201

    # No extra
    resp_no_extra = Response(content=b"{}", status_code=201)
    assert get_response_status_code_partner(resp_no_extra) == 201

    # Dict
    assert (
        get_response_status_code_partner(
            {"extra": {"resp_partner": {"status_code": 200}}}
        )
        == 200
    )  # noqa: E501

    # Fallback
    class ObjPartner:
        status_code_partner = 300

    assert get_response_status_code_partner(ObjPartner()) == 300


def test_get_execution_time_partner():
    resp = Response(
        content=b'{"extra":{"resp_partner":{"execution_time": 1.5}}}', status_code=201
    )  # noqa: E501
    assert get_execution_time_partner(resp) == 1.5

    # Empty resp_partner
    resp_empty = Response(content=b'{"extra":{"resp_partner":{}}}', status_code=201)
    assert get_execution_time_partner(resp_empty) == 0.0

    # No extra
    resp_no_extra = Response(content=b"{}", status_code=201)
    assert get_execution_time_partner(resp_no_extra) == 0.0

    # Dict
    assert (
        get_execution_time_partner({"extra": {"resp_partner": {"execution_time": 2.5}}})
        == 2.5
    )  # noqa: E501

    # Fallback
    class ObjEmpty:
        pass

    assert get_execution_time_partner(ObjEmpty()) == 0.0


def test_get_response_success():
    resp = Response(status_code=200)
    assert get_response_success(resp) is True

    resp_fail = Response(status_code=400)
    assert get_response_success(resp_fail) is False

    assert get_response_success({"success": True}) is True
    assert get_response_success({"error": False}) is True
    assert get_response_success({"error": True}) is False
    assert get_response_success({"status_code": 200}) is True
    assert get_response_success({"status_code": 400}) is False
    assert get_response_success({"invalid": "data"}) is False

    # Dict fallback ValueError/TypeError handling
    assert get_response_success({"status_code": "invalid"}) is False
    assert get_response_success({"status_code": {}}) is False

    class ObjSuccess:
        success = True

    assert get_response_success(ObjSuccess()) is True

    class ObjStatusCode:
        status_code = 200

    assert get_response_success(ObjStatusCode()) is True

    class ObjFailCode:
        status_code = 500

    assert get_response_success(ObjFailCode()) is False

    class ObjInvalidCode:
        status_code = "invalid"

    assert get_response_success(ObjInvalidCode()) is False
