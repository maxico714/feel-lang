from __future__ import annotations

import json
from pathlib import Path

import pytest

from feel_lang.errors import ConfigError
from feel_lang.tables import DecisionTable, decision_table

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"


def load(name: str) -> dict[str, object]:
    return json.loads((FIXTURES / "tables" / name).read_text(encoding="utf-8"))


def test_discount_rules() -> None:
    table = load("discount.json")
    assert decision_table(table, {"age": 20, "risk": "high"}) == {"discount": 0.1, "band": "young-high"}
    assert decision_table(table, {"age": 30, "risk": "medium"}) == {"discount": 0.15, "band": "adult"}
    assert decision_table(table, {"age": 70, "risk": "high"}) == {"discount": 0.2, "band": "senior"}


def test_default_row_fires() -> None:
    table = load("discount.json")
    assert decision_table(table, {"age": 30, "risk": "high"}) == {"discount": 0, "band": "none"}


def test_default_is_omitted_when_absent() -> None:
    table = {
        "inputs": ["x"],
        "outputs": ["y"],
        "rules": [{"when": {"x": "1"}, "then": {"y": 10}}],
    }
    assert decision_table(table, {"x": 1}) == {"y": 10}
    assert decision_table(table, {"x": 2}) == {}


def test_unary_comparison_cells() -> None:
    table = load("shipping.json")
    assert decision_table(table, {"weight": 0.5, "country": "US"}) == {"price": 5, "note": "flat US"}
    assert decision_table(table, {"weight": 4, "country": "US"}) == {"price": 6, "note": "weight-based"}
    assert decision_table(table, {"weight": 12, "country": "US"}) == {"price": 25, "note": "heavy"}
    assert decision_table(table, {"weight": 0.5, "country": "DE"}) == {"price": 50, "note": "manual quote"}


def test_any_cell_and_list_cells() -> None:
    table = {
        "inputs": ["channel"],
        "outputs": ["tier"],
        "rules": [
            {"when": {"channel": ["email", "sms"]}, "then": {"tier": "messaging"}},
            {"when": {"channel": "-"}, "then": {"tier": "other"}},
        ],
    }
    assert decision_table(table, {"channel": "email"}) == {"tier": "messaging"}
    assert decision_table(table, {"channel": "sms"}) == {"tier": "messaging"}
    assert decision_table(table, {"channel": "push"}) == {"tier": "other"}


def test_expression_cell_compares() -> None:
    table = {
        "inputs": ["age"],
        "outputs": ["label"],
        "rules": [
            {"when": {"age": "? >= 18"}, "then": {"label": "adult"}},
            {"when": {"age": "-"}, "then": {"label": "minor"}},
        ],
    }
    assert decision_table(table, {"age": 20}) == {"label": "adult"}
    assert decision_table(table, {"age": 10}) == {"label": "minor"}


def test_text_cell_that_is_not_an_expression_is_a_literal() -> None:
    table = {
        "inputs": ["status"],
        "outputs": ["ok"],
        "rules": [{"when": {"status": "in progress"}, "then": {"ok": True}}],
        "default": {"ok": False},
    }
    assert decision_table(table, {"status": "in progress"}) == {"ok": True}
    assert decision_table(table, {"status": "done"}) == {"ok": False}


def test_output_expression() -> None:
    table = {
        "inputs": ["amount"],
        "outputs": ["fee"],
        "rules": [{"when": {"amount": "> 0"}, "then": {"fee": "= amount * 0.05"}}],
    }
    assert decision_table(table, {"amount": 200}) == {"fee": 10}


def test_invalid_output_expression_raises() -> None:
    table = {
        "inputs": ["amount"],
        "outputs": ["fee"],
        "rules": [{"when": {"amount": "-"}, "then": {"fee": "= amount * "}}],
    }
    with pytest.raises(ConfigError) as caught:
        decision_table(table, {"amount": 1})
    assert "not a valid expression" in caught.value.message


def test_missing_input_raises() -> None:
    with pytest.raises(ConfigError) as caught:
        decision_table(load("discount.json"), {"age": 20})
    assert "missing input" in caught.value.message


def test_table_must_be_an_object() -> None:
    with pytest.raises(ConfigError):
        DecisionTable.from_dict([1, 2, 3])


def test_unknown_table_key() -> None:
    with pytest.raises(ConfigError) as caught:
        DecisionTable.from_dict(
            {"inputs": ["a"], "outputs": ["b"], "rules": [{"when": {"a": "-"}, "then": {"b": 1}}], "extra": 1}
        )
    assert "unknown decision-table key" in caught.value.message


def test_unknown_rule_key() -> None:
    with pytest.raises(ConfigError) as caught:
        DecisionTable.from_dict(
            {"inputs": ["a"], "outputs": ["b"], "rules": [{"when": {"a": "-"}, "then": {"b": 1}, "x": 2}]}
        )
    assert "unknown key" in caught.value.message


def test_duplicate_inputs_rejected() -> None:
    with pytest.raises(ConfigError) as caught:
        DecisionTable.from_dict(
            {"inputs": ["a", "a"], "outputs": ["b"], "rules": [{"when": {"a": "-"}, "then": {"b": 1}}]}
        )
    assert "duplicate" in caught.value.message


def test_inputs_must_be_non_empty() -> None:
    with pytest.raises(ConfigError):
        DecisionTable.from_dict({"inputs": [], "outputs": ["b"], "rules": [{"when": {}, "then": {"b": 1}}]})


def test_rule_uses_unknown_input() -> None:
    with pytest.raises(ConfigError) as caught:
        DecisionTable.from_dict({"inputs": ["a"], "outputs": ["b"], "rules": [{"when": {"z": "-"}, "then": {"b": 1}}]})
    assert "unknown input" in caught.value.message


def test_rule_missing_output() -> None:
    with pytest.raises(ConfigError) as caught:
        DecisionTable.from_dict(
            {"inputs": ["a"], "outputs": ["b", "c"], "rules": [{"when": {"a": "-"}, "then": {"b": 1}}]}
        )
    assert "missing output" in caught.value.message


def test_default_missing_output() -> None:
    with pytest.raises(ConfigError) as caught:
        DecisionTable.from_dict(
            {
                "inputs": ["a"],
                "outputs": ["b", "c"],
                "rules": [{"when": {"a": "-"}, "then": {"b": 1, "c": 2}}],
                "default": {"b": 0},
            }
        )
    assert "default is missing output" in caught.value.message


def test_only_first_hit_policy_supported() -> None:
    with pytest.raises(ConfigError) as caught:
        DecisionTable.from_dict(
            {
                "inputs": ["a"],
                "outputs": ["b"],
                "hit_policy": "unique",
                "rules": [{"when": {"a": "-"}, "then": {"b": 1}}],
            }
        )
    assert "hit policy" in caught.value.message


def test_empty_rules_rejected() -> None:
    with pytest.raises(ConfigError) as caught:
        DecisionTable.from_dict({"inputs": ["a"], "outputs": ["b"], "rules": []})
    assert "non-empty list" in caught.value.message


def test_rule_cap() -> None:
    rules = [{"when": {"a": "-"}, "then": {"b": 1}} for _ in range(1_001)]
    with pytest.raises(ConfigError) as caught:
        DecisionTable.from_dict({"inputs": ["a"], "outputs": ["b"], "rules": rules})
    assert "more than 1000 rules" in caught.value.message


def test_first_match_wins_in_order() -> None:
    table = {
        "inputs": ["x"],
        "outputs": ["y"],
        "rules": [
            {"when": {"x": "> 0"}, "then": {"y": "positive"}},
            {"when": {"x": "-"}, "then": {"y": "fallback"}},
        ],
    }
    assert decision_table(table, {"x": 5}) == {"y": "positive"}
