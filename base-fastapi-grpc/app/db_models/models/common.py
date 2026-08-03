from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import BigInteger, String
from sqlalchemy.orm import Mapped, mapped_column


class DatetimeHelper:
    @staticmethod
    def convert_strftime_sgn(timestamp: int | None) -> str:
        if not timestamp:
            return ""
        try:
            return datetime.fromtimestamp(
                int(timestamp),
                tz=timezone.utc,
            ).strftime("%Y-%m-%d %H:%M:%S")
        except (TypeError, ValueError, OSError):
            return ""

    @staticmethod
    def parse_to_timestamp(date_val: str | int | float | None) -> int | None:
        if date_val is None:
            return None
        if isinstance(date_val, (int, float)):
            ts = int(date_val)
            return ts // 1000 if ts > 9999999999 else ts

        date_str = str(date_val).strip()
        if not date_str:
            return None

        if date_str.isdigit():
            ts = int(date_str)
            return ts // 1000 if ts > 9999999999 else ts

        try:
            clean_str = date_str.replace("Z", "+00:00")
            dt = datetime.fromisoformat(clean_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return int(dt.timestamp())
        except (ValueError, TypeError):
            pass

        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y/%m/%d %H:%M:%S", "%Y/%m/%d"):
            try:
                dt = datetime.strptime(date_str, fmt).replace(tzinfo=timezone.utc)
                return int(dt.timestamp())
            except (ValueError, TypeError):
                continue

        return None


class UnixTimeStampFieldDefault(DatetimeHelper):
    time_created: Mapped[int] = mapped_column(
        BigInteger,
        default=lambda: int(datetime.now(timezone.utc).timestamp()),
        nullable=False,
    )
    time_updated: Mapped[int | None] = mapped_column(
        BigInteger,
        default=None,
        onupdate=lambda: int(datetime.now(timezone.utc).timestamp()),
        nullable=True,
    )

    @property
    def get_time_created(self) -> str:
        return self.convert_strftime_sgn(self.time_created)

    @property
    def get_time_updated(self) -> str:
        return self.convert_strftime_sgn(self.time_updated)


class CreatedUpdatedByMixin:
    created_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
