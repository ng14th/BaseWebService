from typing import Annotated, Any
from uuid import UUID, uuid4

try:
    from uuid import uuid7
except ImportError:  # pragma: no cover - Python < 3.14 compatibility
    uuid7 = uuid4

from pydantic import BeforeValidator


def get_uuid_from_int(value: int) -> UUID:
    if isinstance(value, bool) or value < 0 or value >= 10**12:
        raise ValueError("Integer id is out of range for UUID conversion")
    return UUID(f"00000000-0000-0000-0000-{value:012d}")


def parse_db_uuid(value: Any) -> UUID:
    if isinstance(value, UUID):
        return value

    if isinstance(value, int) and not isinstance(value, bool):
        return get_uuid_from_int(value)

    if isinstance(value, str):
        value = value.strip()
        if value.isdecimal():
            return get_uuid_from_int(int(value))
        return UUID(value)

    raise TypeError("Expected UUID, UUID string, or integer id")


DBUUID = Annotated[UUID, BeforeValidator(parse_db_uuid)]


def get_uuid_v4_str() -> str:
    return str(uuid4())


def get_uuid_v7_str() -> str:
    return str(uuid7())
