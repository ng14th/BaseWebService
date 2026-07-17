from core.infra.connectors.safe_logging import redact_and_truncate


def test_redact_and_truncate_set_tuple():
    assert redact_and_truncate((1, 2)) == [1, 2]
    assert set(redact_and_truncate({1, 2})) == {1, 2}
