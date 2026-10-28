from __future__ import annotations

from decimal import Decimal

import pytest

from feel_lang.errors import ParseError
from feel_lang.lexer import MAX_INPUT_CHARS, tokenize


def kinds(text: str) -> list[tuple[str, object]]:
    return [(token.kind, token.value) for token in tokenize(text) if token.kind != "EOF"]


def test_integer_literal() -> None:
    assert kinds("42") == [("NUMBER", Decimal("42"))]


def test_decimal_and_leading_dot() -> None:
    assert kinds("1.5 .5") == [("NUMBER", Decimal("1.5")), ("NUMBER", Decimal("0.5"))]


def test_exponent_literal() -> None:
    assert kinds("1e3 -2.5E-2") == [("NUMBER", Decimal("1E+3")), ("OP", "-"), ("NUMBER", Decimal("2.5E-2"))]


def test_keywords_and_names() -> None:
    assert kinds("if risk then true else nullValue") == [
        ("KEYWORD", "if"),
        ("NAME", "risk"),
        ("KEYWORD", "then"),
        ("KEYWORD", "true"),
        ("KEYWORD", "else"),
        ("NAME", "nullValue"),
    ]


def test_two_character_operators() -> None:
    assert kinds("** .. != <= >=") == [
        ("OP", "**"),
        ("OP", ".."),
        ("OP", "!="),
        ("OP", "<="),
        ("OP", ">="),
    ]


def test_string_escapes() -> None:
    assert kinds(r'"a\"b\\c\nd\te"') == [("STRING", 'a"b\\c\nd\te')]


def test_unicode_escape() -> None:
    assert kinds(r'"\u00e9"') == [("STRING", "é")]


def test_at_literal() -> None:
    assert kinds('@"2024-01-01"') == [("AT_STRING", "2024-01-01")]


def test_comments_are_skipped() -> None:
    assert kinds("1 // trailing") == [("NUMBER", Decimal("1"))]
    assert kinds("1 /* block */ + 2") == [("NUMBER", Decimal("1")), ("OP", "+"), ("NUMBER", Decimal("2"))]


def test_positions_point_at_token_start() -> None:
    tokens = tokenize("  12 + x")
    assert [(token.value, token.position) for token in tokens[:-1]] == [
        (Decimal("12"), 2),
        ("+", 5),
        ("x", 7),
    ]


def test_unterminated_string_reports_position() -> None:
    with pytest.raises(ParseError) as caught:
        tokenize('"abc')
    assert "unterminated string" in caught.value.message
    assert caught.value.position == 0


def test_invalid_escape_reports_position() -> None:
    with pytest.raises(ParseError) as caught:
        tokenize(r'"a\qb"')
    assert "invalid escape" in caught.value.message
    assert caught.value.position == 2


def test_invalid_unicode_escape() -> None:
    with pytest.raises(ParseError):
        tokenize(r'"\u12"')
    with pytest.raises(ParseError):
        tokenize(r'"\uzzzz"')
    with pytest.raises(ParseError) as caught:
        tokenize(r'"\uD800"')
    assert "surrogate" in caught.value.message


def test_out_of_range_numeric_literals_are_rejected() -> None:
    for text in ["1e999999", "1e-999999", "0." + "1" * 101]:
        with pytest.raises(ParseError) as caught:
            tokenize(text)
        assert "decimal range" in caught.value.message


def test_unterminated_block_comment() -> None:
    with pytest.raises(ParseError) as caught:
        tokenize("1 /* open")
    assert "unterminated comment" in caught.value.message


def test_unexpected_character() -> None:
    with pytest.raises(ParseError) as caught:
        tokenize("1 $ 2")
    assert "unexpected character" in caught.value.message
    assert caught.value.position == 2


def test_empty_input_is_eof_only() -> None:
    assert [token.kind for token in tokenize("")] == ["EOF"]
    assert [token.kind for token in tokenize("   ")] == ["EOF"]


def test_input_length_cap() -> None:
    with pytest.raises(ParseError) as caught:
        tokenize("1" * (MAX_INPUT_CHARS + 1))
    assert "longer than" in caught.value.message


def test_non_string_input() -> None:
    with pytest.raises(ParseError):
        tokenize(42)  # type: ignore[arg-type]


def test_number_does_not_swallow_range() -> None:
    assert kinds("1..10") == [("NUMBER", Decimal("1")), ("OP", ".."), ("NUMBER", Decimal("10"))]
