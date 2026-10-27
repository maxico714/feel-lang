from __future__ import annotations

import json
from pathlib import Path

import pytest

from feel_lang import decision_table, evaluate
from feel_lang.values import to_jsonable

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"


def load_fixtures() -> dict[str, object]:
    return json.loads((FIXTURES / "fixtures.json").read_text(encoding="utf-8"))


FIXTURE_DATA = load_fixtures()
EXPRESSIONS = FIXTURE_DATA["expressions"]
TABLES = FIXTURE_DATA["tables"]


@pytest.mark.parametrize("case", EXPRESSIONS, ids=[case["expression"] for case in EXPRESSIONS])
def test_expression_fixture(case: dict[str, object]) -> None:
    result = evaluate(case["expression"], case["context"])  # type: ignore[arg-type]
    assert to_jsonable(result) == case["expected"]


@pytest.mark.parametrize("group", TABLES, ids=[group["table"] for group in TABLES])
def test_table_fixture(group: dict[str, object]) -> None:
    table = json.loads((FIXTURES / "tables" / group["table"]).read_text(encoding="utf-8"))  # type: ignore[arg-type]
    for case in group["cases"]:  # type: ignore[union-attr]
        result = decision_table(table, case["inputs"])
        assert result == case["expected"], case["inputs"]
