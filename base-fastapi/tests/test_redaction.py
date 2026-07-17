from core.logging.redaction import redact_sensitive_data, REDACTED


def test_redact_sensitive_data_primitives():
    assert redact_sensitive_data(None) is None
    assert redact_sensitive_data(1) == 1
    assert redact_sensitive_data(True) is True
    assert redact_sensitive_data(1.5) == 1.5


def test_redact_sensitive_data_strings():
    assert redact_sensitive_data("hello") == "hello"
    
    # Valid JSON string
    assert redact_sensitive_data('{"token": "secret"}') == {"token": REDACTED}
    assert redact_sensitive_data('[{"token": "secret"}]') == [{"token": REDACTED}]
    
    # Invalid JSON string
    assert redact_sensitive_data('{"token": "secret"') == '{"token": "secret"'
    assert redact_sensitive_data('[{"token": "secret"') == '[{"token": "secret"'
    
    # Non-JSON bracket strings
    assert redact_sensitive_data('{hello}') == '{hello}'


def test_redact_sensitive_data_recursive():
    lst = []
    lst.append(lst)
    res = redact_sensitive_data(lst)
    assert "<recursive list>" in res[0]
    
    dct = {}
    dct["recursive"] = dct
    res_dct = redact_sensitive_data(dct)
    assert "<recursive dict>" in res_dct["recursive"]


def test_redact_sensitive_data_mapping():
    data = {
        "normal": "value",
        "authorization": "secret1",
        "cookie": "secret2",
        "password": "secret3",
        "client-secret": "secret4",
        "my_custom_token": "secret5",
        "nested": {
            "token": "secret6",
            "safe": "data"
        }
    }
    
    res = redact_sensitive_data(data)
    assert res["normal"] == "value"
    assert res["authorization"] == REDACTED
    assert res["cookie"] == REDACTED
    assert res["password"] == REDACTED
    assert res["client-secret"] == REDACTED
    assert res["my_custom_token"] == REDACTED
    assert res["nested"]["token"] == REDACTED
    assert res["nested"]["safe"] == "data"


def test_redact_sensitive_data_iterables():
    data_list = [1, {"token": "secret"}, 3]
    res_list = redact_sensitive_data(data_list)
    assert res_list == [1, {"token": REDACTED}, 3]
    
    data_tuple = (1, {"token": "secret"})
    res_tuple = redact_sensitive_data(data_tuple)
    assert res_tuple == [1, {"token": REDACTED}]
    
    data_set = {1, 2}
    res_set = redact_sensitive_data(data_set)
    assert set(res_set) == {1, 2}


def test_redact_sensitive_data_fallback():
    class CustomObj:
        pass
    
    obj = CustomObj()
    assert redact_sensitive_data(obj) is obj
