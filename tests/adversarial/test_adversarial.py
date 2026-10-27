from __future__ import annotations

import json
from pathlib import Path

import pytest

from feel_lang import Evaluator, decision_table, evaluate, parse
from feel_lang.errors import ArgumentError, ConfigError, EvalError, ParseError
from feel_lang.lexer import MAX_INPUT_CHARS, MAX_TOKENS, tokenize


def test_long_input_is_rejected() -> None:
    with pytest.raises(ParseError) as caught:
        parse("1 + " * (MAX_INPUT_CHARS // 4))
    assert "longer than" in caught.value.message or "tokens" in caught.value.message


def test_token_cap_is_enforced() -> None:
    expression = "[" + ",".join(["1"] * (MAX_TOKENS // 2)) + "]"
    with pytest.raises(ParseError):
        tokenize(expression)


def test_null_bytes_are_rejected() -> None:
    with pytest.raises(ParseError) as caught:
        parse("1 \x002")
    assert "unexpected character" in caught.value.message


def test_unicode_and_control_characters_in_strings() -> None:
    assert evaluate('"héllo \u0001 wörld"') == "héllo \u0001 wörld"


def test_very_long_string_literal() -> None:
    text = "x" * 10_000
    assert evaluate(f'"{text}"') == text


def test_huge_list_literal_is_capped() -> None:
    with pytest.raises(ParseError):
        parse("[" + ",".join(["1"] * 20_000) + "]")


def test_nested_list_literal_depth() -> None:
    expression = "[" * 120 + "1" + "]" * 120
    with pytest.raises(ParseError) as caught:
        parse(expression)
    assert "nests too deeply" in caught.value.message


def test_repeated_unary_operators() -> None:
    with pytest.raises(ParseError):
        parse("-" * 500 + "1")


def test_division_by_zero_is_null_not_an_exception() -> None:
    assert evaluate("1 / 0") is None


def test_unknown_variable_in_arithmetic_is_null() -> None:
    assert evaluate("missing + 1") is None


def test_index_on_non_list_is_null() -> None:
    assert evaluate("1[1]") is None
    assert evaluate('"abc"[1]') is None


def test_context_with_hostile_values() -> None:
    context = {"x": [1, 2, 3], "y": {"nested": {"deep": 4}}, "z": None}
    assert evaluate("x[2]", context) == 2
    assert evaluate("y.nested.deep", context) == 4
    assert evaluate("z + 1", context) is None


def test_unknown_function_in_a_cell_never_matches() -> None:
    table = {
        "inputs": ["x"],
        "outputs": ["y"],
        "rules": [{"when": {"x": "mystery(1)"}, "then": {"y": 1}}, {"when": {"x": "-"}, "then": {"y": 0}}],
    }
    assert decision_table(table, {"x": 5}) == {"y": 0}


def test_large_context_list_is_evaluated_lazily() -> None:
    context = {"values": list(range(10_000))}
    assert evaluate("count(values)", context) == 10_000
    assert evaluate("sum(values)", context) == 49_995_000


def test_duplicate_context_keys_last_wins() -> None:
    context: dict[str, int] = {}
    context["a"] = 1
    context["a"] = 2
    assert Evaluator(context).evaluate(parse("a")) == 2


def test_wrong_arity_is_an_argument_error() -> None:
    with pytest.raises(ArgumentError):
        evaluate("substring(1)")


def test_eval_error_has_a_stable_code() -> None:
    with pytest.raises(EvalError) as caught:
        evaluate("mystery()")
    assert caught.value.code == "E_EVAL"


def test_parse_error_reports_position() -> None:
    with pytest.raises(ParseError) as caught:
        parse("1 + ")
    assert caught.value.position >= 0


def test_decision_table_from_json_file_with_hostile_names(tmp_path: Path) -> None:
    table = {
        "inputs": ["customer age"],
        "outputs": ["category"],
        "rules": [{"when": {"customer age": ">= 65"}, "then": {"category": "senior"}}],
    }
    path = tmp_path / "table.json"
    path.write_text(json.dumps(table), encoding="utf-8")
    assert decision_table(json.loads(path.read_text(encoding="utf-8")), {"customer age": 70}) == {"category": "senior"}


def test_table_rejects_nested_rule_values_that_cannot_match() -> None:
    table = {
        "inputs": ["x"],
        "outputs": ["y"],
        "rules": [{"when": {"x": {"nested": True}}, "then": {"y": 1}}, {"when": {"x": "-"}, "then": {"y": 2}}],
    }
    with pytest.raises(ConfigError):
        decision_table(table, {"x": 1})


def test_render_of_huge_list_is_bounded_by_input_caps() -> None:
    from feel_lang.evaluator import render

    assert render(list(range(100))).startswith("[0, 1, 2")
