from __future__ import annotations

import datetime as dt
from decimal import Decimal

import pytest

from feel_lang.values import (
    Duration,
    add_duration,
    format_number,
    number,
    parse_date,
    parse_datetime,
    parse_time,
    public_number,
    to_decimal,
    to_jsonable,
)


def test_duration_parse_forms() -> None:
    assert Duration.parse("P1Y") == Duration(12, Decimal(0), "months")
    assert Duration.parse("P1M") == Duration(1, Decimal(0), "months")
    assert Duration.parse("P1D") == Duration(0, Decimal(86400), "seconds")
    assert Duration.parse("PT2H30M") == Duration(0, Decimal(9000), "seconds")
    assert Duration.parse("P1DT2H") == Duration(0, Decimal(93600), "seconds")
    assert Duration.parse("P1Y2M3DT4H5M6S") == Duration(14, Decimal(273906), "mixed")


def test_duration_rejects_invalid() -> None:
    for text in ["", "P", "PT", "1D", "P1W", "P1S", "P1H"]:
        assert Duration.parse(text) is None


def test_duration_rejects_oversized_components() -> None:
    assert Duration.parse("P" + "9" * 5_000 + "Y") is None
    assert Duration.parse("PT" + "9" * 5_000 + "S") is None
    assert Duration.parse("P" + "9" * 5_000 + "DT1S") is None


def test_add_duration_overflow_returns_none() -> None:
    assert add_duration(dt.date(2024, 1, 1), Duration.parse("P999999999Y")) is None  # type: ignore[arg-type]
    assert add_duration(dt.date(2024, 1, 1), Duration.parse("P999999999999999999D")) is None  # type: ignore[arg-type]


def test_duration_isoformat_round_trip() -> None:
    for text in ["P1Y", "P1M", "P1D", "PT2H30M", "P1DT2H", "P1Y2M3DT4H5M6S", "PT0S"]:
        duration = Duration.parse(text)
        assert duration is not None
        assert duration.isoformat() == text


def test_duration_equality_and_hash() -> None:
    assert Duration.parse("P1D") == Duration.parse("PT24H")
    assert len({Duration.parse("P1D"), Duration.parse("PT24H")}) == 1


def test_add_duration_to_date() -> None:
    assert add_duration(dt.date(2024, 1, 31), Duration.parse("P1M")) == dt.date(2024, 2, 29)  # type: ignore[arg-type]
    assert add_duration(dt.date(2023, 1, 31), Duration.parse("P1M")) == dt.date(2023, 2, 28)  # type: ignore[arg-type]
    assert add_duration(dt.date(2024, 1, 1), Duration.parse("P1D")) == dt.date(2024, 1, 2)  # type: ignore[arg-type]


def test_add_duration_to_time_rejects_multiple_days() -> None:
    assert add_duration(dt.time(23, 0), Duration.parse("PT2H")) is None  # type: ignore[arg-type]
    assert add_duration(dt.time(10, 0), Duration.parse("PT2H")) == dt.time(12, 0)  # type: ignore[arg-type]
    assert add_duration(dt.time(10, 0), Duration.parse("P1M")) is None  # type: ignore[arg-type]


def test_add_duration_to_datetime() -> None:
    moment = dt.datetime(2024, 12, 31, 23, 30)
    assert add_duration(moment, Duration.parse("PT1H")) == dt.datetime(2025, 1, 1, 0, 30)  # type: ignore[arg-type]
    assert add_duration(moment, Duration.parse("P1M")) == dt.datetime(2025, 1, 31, 23, 30)  # type: ignore[arg-type]


def test_mixed_duration_with_temporal_is_rejected() -> None:
    assert add_duration(dt.date(2024, 1, 1), Duration.parse("P1M1D")) is None  # type: ignore[arg-type]


def test_number_parsing() -> None:
    assert number("12") == Decimal(12)
    assert number("1.5") == Decimal("1.5")
    assert number(".5") == Decimal("0.5")
    assert number("1e3") == Decimal("1E+3")
    assert number("abc") is None
    assert number("1.") is None
    assert number("1,5") is None


def test_number_digit_cap() -> None:
    assert number("1" * 101) is None
    assert number("1e999999") is None
    assert number("1e-999999") is None
    assert number("1e100") is not None


def test_to_decimal_from_float_uses_repr() -> None:
    assert to_decimal(0.1) == Decimal("0.1")
    assert to_decimal(1) == Decimal(1)
    assert to_decimal(Decimal("2.5")) == Decimal("2.5")


def test_public_number() -> None:
    assert public_number(Decimal("3.0")) == 3
    assert isinstance(public_number(Decimal("3.0")), int)
    assert public_number(Decimal("3.5")) == 3.5


def test_format_number() -> None:
    assert format_number(Decimal("1.50")) == "1.5"
    assert format_number(Decimal("2")) == "2"
    assert format_number(Decimal("-0.25")) == "-0.25"


def test_temporal_parsers() -> None:
    assert parse_date("2024-02-29") == dt.date(2024, 2, 29)
    assert parse_date("2024-02-30") is None
    assert parse_time("13:45:30") == dt.time(13, 45, 30)
    assert parse_time("25:00:00") is None
    assert parse_datetime("2024-01-02T03:04:05") == dt.datetime(2024, 1, 2, 3, 4, 5)
    assert parse_datetime("nope") is None


def test_to_jsonable_converts_nested_values() -> None:
    payload = {
        "number": Decimal("1.5"),
        "duration": Duration.parse("P1D"),
        "date": dt.date(2024, 1, 2),
        "list": [Decimal(1), None, True],
    }
    assert to_jsonable(payload) == {
        "number": 1.5,
        "duration": "P1D",
        "date": "2024-01-02",
        "list": [1, None, True],
    }


def test_is_number_rejects_bools() -> None:
    from feel_lang.values import is_number

    assert is_number(True) is False
    assert is_number(1) is True
    assert is_number(1.5) is True
    assert is_number(Decimal(1)) is True
    assert is_number("1") is False


@pytest.mark.parametrize("text", ["P0D", "PT0S", "P0Y"])
def test_zero_durations(text: str) -> None:
    parsed = Duration.parse(text)
    assert parsed is not None
    assert parsed.isoformat() == "PT0S"
