from __future__ import annotations

from decimal import Decimal

import pytest

from feel_lang.errors import ParseError
from feel_lang.nodes import (
    Between,
    Binary,
    Call,
    ContextAccess,
    ContextLiteral,
    If,
    Index,
    ListLiteral,
    Literal,
    Membership,
    Name,
    Placeholder,
    Range,
    Unary,
)
from feel_lang.parser import MAX_DEPTH, parse


def test_number_and_string_literals() -> None:
    assert parse("42") == Literal(Decimal(42), position=0)
    assert parse('"hi"') == Literal("hi", position=0)
    assert parse("true") == Literal(True, position=0)
    assert parse("null") == Literal(None, position=0)


def test_arithmetic_precedence() -> None:
    node = parse("1 + 2 * 3")
    assert isinstance(node, Binary) and node.operator == "+"
    assert isinstance(node.right, Binary) and node.right.operator == "*"


def test_parentheses_override_precedence() -> None:
    node = parse("(1 + 2) * 3")
    assert isinstance(node, Binary) and node.operator == "*"
    assert isinstance(node.left, Binary) and node.left.operator == "+"


def test_unary_binds_tighter_than_power() -> None:
    node = parse("-2 ** 2")
    assert isinstance(node, Binary) and node.operator == "**"
    assert isinstance(node.left, Unary)


def test_power_is_right_associative() -> None:
    node = parse("2 ** 3 ** 2")
    assert isinstance(node, Binary) and node.operator == "**"
    assert isinstance(node.right, Binary) and node.right.operator == "**"


def test_comparison_is_not_chained() -> None:
    with pytest.raises(ParseError):
        parse("1 < 2 < 3")


def test_logical_precedence() -> None:
    node = parse("1 < 2 and 3 > 4 or true")
    assert isinstance(node, Binary) and node.operator == "or"
    assert isinstance(node.left, Binary) and node.left.operator == "and"


def test_if_then_else_nests() -> None:
    node = parse("if a > 1 then 1 else if a > 0 then 2 else 3")
    assert isinstance(node, If)
    assert isinstance(node.otherwise, If)


def test_between() -> None:
    node = parse("5 between 1 and 10")
    assert isinstance(node, Between)


def test_membership_range_and_list() -> None:
    node = parse("5 in [1..10]")
    assert isinstance(node, Membership)
    assert isinstance(node.tests[0], Range)
    node = parse("5 in (1, 2, 3)")
    assert isinstance(node, Membership) and len(node.tests) == 3


def test_parenthesized_range() -> None:
    node = parse("10 in (1..10)")
    assert isinstance(node, Membership)
    test = node.tests[0]
    assert isinstance(test, Range) and test.include_low is False and test.include_high is False


def test_open_range_brackets() -> None:
    node = parse("5 in ]1..10[")
    assert isinstance(node, Membership)
    test = node.tests[0]
    assert isinstance(test, Range) and test.include_low is False and test.include_high is False


def test_unbounded_range() -> None:
    node = parse("[61..]")
    assert isinstance(node, Range) and node.high is None and node.include_low is True


def test_list_literal_and_empty_list() -> None:
    node = parse("[1, 2, 3]")
    assert isinstance(node, ListLiteral) and len(node.items) == 3
    assert parse("[]") == ListLiteral((), position=0)


def test_context_literal_and_access() -> None:
    node = parse("{a: 1, b: 2}.a")
    assert isinstance(node, ContextAccess) and node.key == "a"
    assert isinstance(node.target, ContextLiteral)
    assert [key for key, _ in node.target.entries] == ["a", "b"]


def test_context_access_chain() -> None:
    node = parse("x.y.z")
    assert isinstance(node, ContextAccess) and node.key == "z"
    assert isinstance(node.target, ContextAccess) and node.target.key == "y"


def test_index_expression() -> None:
    node = parse("[10, 20, 30][2]")
    assert isinstance(node, Index)
    assert isinstance(node.target, ListLiteral)


def test_placeholder() -> None:
    assert parse("? = 5").left == Placeholder(position=0)  # type: ignore[union-attr]


def test_multi_word_name() -> None:
    node = parse("customer age")
    assert isinstance(node, Name) and node.words == ("customer age",)


def test_date_and_time_function_name() -> None:
    node = parse('date and time("2024-01-02T03:04:05")')
    assert isinstance(node, Call) and node.name == "date and time"


def test_at_literals_parse_to_temporals() -> None:
    import datetime as dt

    assert isinstance(parse('@"2024-01-02"'), Literal)
    literal = parse('@"2024-01-02"')
    assert isinstance(literal, Literal) and literal.value == dt.date(2024, 1, 2)


def test_invalid_at_literal() -> None:
    with pytest.raises(ParseError):
        parse('@"not-a-date"')


def test_empty_expression() -> None:
    with pytest.raises(ParseError) as caught:
        parse("")
    assert "unexpected token" in caught.value.message


def test_unclosed_parenthesis() -> None:
    with pytest.raises(ParseError) as caught:
        parse("(1 + 2")
    assert "expected ')'" in caught.value.message


def test_trailing_token() -> None:
    with pytest.raises(ParseError) as caught:
        parse("1 2")
    assert "unexpected token" in caught.value.message


def test_instance_of_is_rejected_with_a_clear_message() -> None:
    with pytest.raises(ParseError) as caught:
        parse("1 instance of number")
    assert "instance of" in caught.value.message


def test_deep_nesting_is_bounded() -> None:
    with pytest.raises(ParseError) as caught:
        parse("(" * (MAX_DEPTH + 5) + "1" + ")" * (MAX_DEPTH + 5))
    assert "nests too deeply" in caught.value.message


def test_deep_unary_chain_is_bounded() -> None:
    with pytest.raises(ParseError) as caught:
        parse("-" * (MAX_DEPTH + 5) + "1")
    assert "nests too deeply" in caught.value.message


def test_large_list_under_the_input_cap_parses() -> None:
    node = parse("[" + ",".join(["1"] * 2_000) + "]")
    assert isinstance(node, ListLiteral) and len(node.items) == 2_000


def test_huge_list_is_rejected() -> None:
    with pytest.raises(ParseError):
        parse("[" + ",".join(["1"] * 10_001) + "]")


def test_unknown_function_name_is_a_call_node() -> None:
    node = parse("mystery(1)")
    assert isinstance(node, Call) and node.name == "mystery"
