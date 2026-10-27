"""Public API for feel-lang."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .errors import ArgumentError, ConfigError, EvalError, FeelError, OracleError, ParseError, TypeError_
from .evaluator import Evaluator, RangeValue, equals, render
from .nodes import Node
from .parser import parse
from .tables import DecisionTable, decision_table
from .values import Duration, to_jsonable, to_public

__version__ = "0.1.0"

__all__ = [
    "ArgumentError",
    "ConfigError",
    "DecisionTable",
    "Duration",
    "EvalError",
    "Evaluator",
    "FeelError",
    "Node",
    "OracleError",
    "ParseError",
    "RangeValue",
    "TypeError_",
    "decision_table",
    "equals",
    "evaluate",
    "parse",
    "render",
    "to_jsonable",
]


def evaluate(expression: str, context: Mapping[str, Any] | None = None, *, raw: bool = False) -> Any:
    """Evaluate a FEEL expression.

    Numbers come back as int/float, dates and times as ``datetime`` objects, durations as
    :class:`Duration`. Pass ``raw=True`` for exact ``Decimal`` numbers.
    """
    value = Evaluator(context).evaluate(parse(expression))
    if raw:
        return value
    return to_public(value)
