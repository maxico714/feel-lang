"""FEEL value helpers: exact decimal arithmetic, temporals and durations."""

from __future__ import annotations

import datetime as _dt
import re
from decimal import Decimal, InvalidOperation

MAX_LIST_LENGTH = 10_000
MAX_DECIMAL_DIGITS = 100

_NUMBER_RE = re.compile(r"^[+-]?(?:\d+(?:\.\d+)?|\.\d+)(?:[eE][+-]?\d+)?$")
_DURATION_RE = re.compile(
    r"^P(?:(?P<years>\d+)Y)?(?:(?P<months>\d+)M)?(?:(?P<days>\d+)D)?"
    r"(?:T(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+(?:\.\d+)?)S)?)?$"
)


class Duration:
    """ISO 8601 duration split into months and seconds.

    FEEL separates years/months durations from days/time durations, and adding the two
    kinds to a temporal value is an error. ``kind`` records which part was supplied.
    """

    __slots__ = ("kind", "months", "seconds")

    def __init__(self, months: int = 0, seconds: Decimal = Decimal(0), kind: str = "mixed") -> None:
        self.months = months
        self.seconds = seconds
        self.kind = kind

    @classmethod
    def parse(cls, text: str) -> Duration | None:
        match = _DURATION_RE.match(text)
        if match is None or text in {"P", "PT"}:
            return None
        parts = {key: value for key, value in match.groupdict().items() if value is not None}
        if not parts:
            return None
        months = int(parts.get("years", 0)) * 12 + int(parts.get("months", 0))
        seconds = (
            Decimal(parts.get("days", 0)) * 86400
            + Decimal(parts.get("hours", 0)) * 3600
            + Decimal(parts.get("minutes", 0)) * 60
            + Decimal(parts.get("seconds", 0))
        )
        if months and seconds:
            kind = "mixed"
        elif months:
            kind = "months"
        else:
            kind = "seconds"
        return cls(months, seconds, kind)

    def isoformat(self) -> str:
        years, months = divmod(self.months, 12)
        days = int(self.seconds // 86400)
        remainder = self.seconds - days * 86400
        hours = int(remainder // 3600)
        remainder -= hours * 3600
        minutes = int(remainder // 60)
        seconds = remainder - minutes * 60
        text = "P"
        if years:
            text += f"{years}Y"
        if months:
            text += f"{months}M"
        if days:
            text += f"{days}D"
        time_part = ""
        if hours:
            time_part += f"{hours}H"
        if minutes:
            time_part += f"{minutes}M"
        if seconds:
            time_part += f"{format_number(seconds)}S"
        if time_part:
            text += "T" + time_part
        return "PT0S" if text == "P" else text

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Duration) and self.months == other.months and self.seconds == other.seconds

    def __hash__(self) -> int:
        return hash((self.months, self.seconds))

    def __repr__(self) -> str:
        return f"Duration({self.isoformat()!r})"


Temporal = _dt.date | _dt.time | _dt.datetime


def is_number(value: object) -> bool:
    return isinstance(value, (int, float, Decimal)) and not isinstance(value, bool)


def to_decimal(value: int | float | Decimal) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if isinstance(value, int):
        return Decimal(value)
    return Decimal(str(value))


def number(value: str | int | float | Decimal) -> Decimal | None:
    """Parse a FEEL number literal into an exact Decimal, or return None."""
    text = str(value).strip()
    if not _NUMBER_RE.match(text):
        return None
    try:
        result = Decimal(text)
    except InvalidOperation:  # pragma: no cover - regex already rejects this
        return None
    if len(result.as_tuple().digits) > MAX_DECIMAL_DIGITS:
        return None
    return result


def public_number(value: Decimal) -> int | float:
    """Convert an internal Decimal to a JSON-friendly int or float."""
    if value == value.to_integral_value():
        return int(value)
    return float(value)


def format_number(value: Decimal) -> str:
    if value == value.to_integral_value():
        return str(int(value))
    text = format(value.normalize(), "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def parse_date(text: str) -> _dt.date | None:
    try:
        return _dt.date.fromisoformat(text)
    except ValueError:
        return None


def parse_time(text: str) -> _dt.time | None:
    try:
        return _dt.time.fromisoformat(text)
    except ValueError:
        return None


def parse_datetime(text: str) -> _dt.datetime | None:
    try:
        return _dt.datetime.fromisoformat(text)
    except ValueError:
        return None


def temporal_isoformat(value: Temporal) -> str:
    if isinstance(value, _dt.datetime):
        return value.isoformat(timespec="seconds") if value.microsecond == 0 else value.isoformat()
    if isinstance(value, _dt.time):
        return value.isoformat(timespec="seconds") if value.microsecond == 0 else value.isoformat()
    return value.isoformat()


def add_duration(temporal: Temporal, duration: Duration) -> Temporal | None:
    """Add a duration to a date, time or date-time following FEEL type rules."""
    if isinstance(temporal, _dt.time):
        if duration.months:
            return None
        moment = _dt.datetime.combine(_dt.date(1970, 1, 1), temporal)
        shifted = moment + _dt.timedelta(seconds=float(duration.seconds))
        if shifted.date() != moment.date():
            return None
        return shifted.timetz().replace(tzinfo=None)
    if duration.kind == "months" or (duration.months and not duration.seconds):
        return _add_months(temporal, duration.months)
    if duration.months:
        return None
    return temporal + _dt.timedelta(seconds=float(duration.seconds))


def _add_months(temporal: Temporal, months: int) -> Temporal:
    if isinstance(temporal, _dt.time):
        raise ValueError("months cannot be added to a time")
    base = temporal if isinstance(temporal, _dt.datetime) else _dt.datetime.combine(temporal, _dt.time())
    total = base.year * 12 + (base.month - 1) + months
    year, month = divmod(total, 12)
    month += 1
    day = min(base.day, _days_in_month(year, month))
    result = base.replace(year=year, month=month, day=day)
    if isinstance(temporal, _dt.datetime):
        return result
    return result.date()


def _days_in_month(year: int, month: int) -> int:
    if month == 12:
        return 31
    return (_dt.date(year, month + 1, 1) - _dt.timedelta(days=1)).day


def to_jsonable(value: object) -> object:
    """Convert internal values into JSON-serialisable ones."""
    if isinstance(value, Decimal):
        return public_number(value)
    if isinstance(value, Duration):
        return value.isoformat()
    if isinstance(value, (_dt.date, _dt.time, _dt.datetime)):
        return temporal_isoformat(value)
    if isinstance(value, list):
        return [to_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): to_jsonable(item) for key, item in value.items()}
    return value


def to_public(value: object) -> object:
    """Convert decimals to int/float but keep temporals and durations as native objects."""
    if isinstance(value, Decimal):
        return public_number(value)
    if isinstance(value, list):
        return [to_public(item) for item in value]
    if isinstance(value, dict):
        return {str(key): to_public(item) for key, item in value.items()}
    return value
