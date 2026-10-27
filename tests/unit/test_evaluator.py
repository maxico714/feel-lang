from __future__ import annotations

import datetime as dt
from decimal import Decimal

import pytest

import feel_lang
from feel_lang import evaluate, parse, render
from feel_lang.errors import ArgumentError, EvalError
from feel_lang.values import Duration


def ev(expression: str, context: dict[str, object] | None = None) -> object:
    return evaluate(expression, context or {})


def test_decimal_arithmetic_is_exact() -> None:
    assert ev("0.1 + 0.2") == 0.3
    assert evaluate("0.1 + 0.2", raw=True) == Decimal("0.3")


def test_integer_results_stay_integers() -> None:
    result = ev("1 + 2")
    assert result == 3 and isinstance(result, int)


def test_operator_precedence() -> None:
    assert ev("1 + 2 * 3") == 7
    assert ev("(1 + 2) * 3") == 9
    assert ev("2 ** 3 ** 2") == 512
    assert ev("-2 ** 2") == 4
    assert ev("2 ** -1") == 0.5


def test_division_by_zero_is_null() -> None:
    assert ev("1 / 0") is None
    assert ev("0 / 0") is None


def test_type_mismatch_arithmetic_is_null() -> None:
    assert ev('1 + "a"') is None


def test_string_concatenation() -> None:
    assert ev('"a" + "b"') == "ab"


def test_equality_across_number_types() -> None:
    assert ev("1 = 1.0") is True
    assert ev('"a" = "b"') is False
    assert ev("[1, 2] = [1, 2]") is True
    assert ev("[1] = [1, 2]") is False
    assert ev("{a: 1} = {a: 1}") is True
    assert ev("{a: 1} = {a: 2}") is False


def test_null_equality() -> None:
    assert ev("null = null") is True
    assert ev("1 = null") is False
    assert ev("null = 1") is False
    assert ev("x = null", {"x": None}) is True
    assert ev("x = null", {"x": 1}) is False
    assert ev("null != null") is False


def test_ordering() -> None:
    assert ev("1 < 2") is True
    assert ev('"a" < "b"') is True
    assert ev("2 >= 2") is True
    assert ev('1 < "a"') is None
    assert ev("null < 1") is None


def test_three_valued_and() -> None:
    assert ev("true and true") is True
    assert ev("true and false") is False
    assert ev("null and false") is False
    assert ev("null and true") is None
    assert ev("true and 1") is None


def test_three_valued_or() -> None:
    assert ev("false or false") is False
    assert ev("null or true") is True
    assert ev("null or false") is None
    assert ev("1 or false") is None


def test_not() -> None:
    assert ev("not(true)") is False
    assert ev("not(null)") is None
    assert ev("not(1)") is None


def test_if_then_else() -> None:
    assert ev("if 1 > 2 then 1 else 2") == 2
    assert ev("if null then 1 else 2") == 2
    assert ev("if true then 1 else 2") == 1


def test_between_and_membership() -> None:
    assert ev("5 between 1 and 10") is True
    assert ev("5 in [1..10]") is True
    assert ev("10 in (1..10)") is False
    assert ev("5 in ]1..10[") is True
    assert ev("1 in (1, 2, 3)") is True
    assert ev("4 in (1, 2, 3)") is False
    assert ev("1 in ([1..5], [10..20])") is True
    assert ev("null in [1..2]") is None


def test_range_literal_str() -> None:
    value = feel_lang.Evaluator({}).evaluate(parse("[1..10]"))
    assert str(value) == "[1..10]"


def test_list_indexing_is_one_based_and_negative_from_end() -> None:
    assert ev("[10, 20, 30][1]") == 10
    assert ev("[10, 20, 30][3]") == 30
    assert ev("[10, 20, 30][-1]") == 30
    assert ev("[10, 20, 30][0]") is None
    assert ev("[10, 20, 30][4]") is None
    assert ev("[10, 20, 30][1.5]") is None


def test_boolean_index_filters() -> None:
    assert ev("[10, 20][true]") == [10, 20]
    assert ev("[10, 20][false]") == []


def test_context_literal_and_access() -> None:
    assert ev("{a: 1, b: 2}.a") == 1
    assert ev('{a: 1}["a"]') is None
    assert ev("x.y", {"x": {"y": 7}}) == 7
    assert ev("x.z", {"x": {"y": 7}}) is None


def test_unknown_variable_is_null() -> None:
    assert ev("missing") is None


def test_placeholder_requires_binding() -> None:
    assert ev("? = 5", {"?": 5}) is True
    with pytest.raises(EvalError):
        ev("? = 5")


def test_count_sum_min_max_mean() -> None:
    assert ev("count([1, 2, 3])") == 3
    assert ev("count([])") == 0
    assert ev("count(1)") == 1
    assert ev("count(null)") == 0
    assert ev("sum([1, 2, 3])") == 6
    assert ev("sum([])") is None
    assert ev("min([3, 1, 2])") == 1
    assert ev("min(3, 1, 2)") == 1
    assert ev("max([])") is None
    assert ev("mean([1, 2, 3])") == 2
    assert ev("mean([])") is None
    assert ev('sum([1, "a"])') is None


def test_all_and_any() -> None:
    assert ev("all([true, true])") is True
    assert ev("all([true, false])") is False
    assert ev("all([])") is True
    assert ev("any([false, true])") is True
    assert ev("any([])") is False
    assert ev("all([true, null])") is None


def test_string_functions() -> None:
    assert ev('contains("hello", "ell")') is True
    assert ev('contains("hello", "xyz")') is False
    assert ev('substring("hello", 2)') == "ello"
    assert ev('substring("hello", 2, 3)') == "ell"
    assert ev('substring("hello", 0, 2)') is None
    assert ev('substring("hello", 6, 2)') is None
    assert ev('substring("hello", 2, -1)') is None


def test_conversions() -> None:
    assert ev("string(1.5)") == "1.5"
    assert ev("string(true)") == "true"
    assert ev("string(null)") is None
    assert ev('number("1 234,56", " ", ",")') == 1234.56
    assert ev('number("abc", " ", ",")') is None


def test_temporal_functions() -> None:
    assert ev('date("2024-02-29")') == dt.date(2024, 2, 29)
    assert ev('date("2024-02-30")') is None
    assert ev('time("13:45:30")') == dt.time(13, 45, 30)
    assert ev("date(2024, 1, 2)") == dt.date(2024, 1, 2)
    assert ev('date and time("2024-01-02T03:04:05")') == dt.datetime(2024, 1, 2, 3, 4, 5)


def test_duration_parsing_and_arithmetic() -> None:
    assert ev('duration("P1DT2H")') == Duration(0, Decimal(93600), "seconds")
    assert ev('date("2024-01-02") + duration("P1D")') == dt.date(2024, 1, 3)
    assert ev('date("2024-01-31") + duration("P1M")') == dt.date(2024, 2, 29)
    assert ev('duration("P1M") + duration("P1D")') is None


def test_at_literals() -> None:
    assert ev('@"2024-01-01" + @"P1D"') == dt.date(2024, 1, 2)


def test_unknown_function_raises() -> None:
    with pytest.raises(EvalError) as caught:
        ev("mystery(1)")
    assert "unknown function" in caught.value.message


def test_wrong_arity_raises() -> None:
    with pytest.raises(ArgumentError):
        ev("count(1, 2)")


def test_multi_word_and_dotted_names() -> None:
    assert ev("customer age > 30", {"customer age": 35}) is True
    assert ev("order.total", {"order": {"total": 10}}) == 10


def test_render() -> None:
    assert render(None) == "null"
    assert render(True) == "true"
    assert render(Decimal("1.50")) == "1.5"
    assert render("hi") == '"hi"'
    assert render([Decimal(1), Decimal(2)]) == "[1, 2]"


def test_evaluator_does_not_execute_code() -> None:
    with pytest.raises(EvalError):
        ev('__import__("os")')


def test_deep_power_is_bounded() -> None:
    assert ev("2 ** 100000") is None
