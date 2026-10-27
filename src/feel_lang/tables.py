"""Decision-table evaluation with a first-match hit policy."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .errors import ConfigError, ParseError
from .evaluator import Evaluator, RangeValue, equals
from .nodes import Name, Node
from .parser import parse
from .values import to_jsonable

ANY = "-"
LEADING_OPERATORS = ("!=", "<=", ">=", "=", "<", ">")
MAX_RULES = 1_000


@dataclass(frozen=True)
class Rule:
    when: Mapping[str, object]
    then: Mapping[str, object]
    index: int


@dataclass(frozen=True)
class DecisionTable:
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    rules: tuple[Rule, ...]
    default: Mapping[str, object] | None
    hit_policy: str = "first"

    @classmethod
    def from_dict(cls, data: object) -> DecisionTable:
        if not isinstance(data, dict):
            raise ConfigError("decision table must be a JSON object")
        unknown = set(data) - {"inputs", "outputs", "rules", "default", "hit_policy", "name", "description"}
        if unknown:
            raise ConfigError(f"unknown decision-table key(s): {', '.join(sorted(unknown))}")
        inputs = _string_list(data.get("inputs"), "inputs")
        outputs = _string_list(data.get("outputs"), "outputs")
        hit_policy = data.get("hit_policy", "first")
        if hit_policy != "first":
            raise ConfigError("only the 'first' hit policy is supported in v0.1", position=-1)
        raw_rules = data.get("rules")
        if not isinstance(raw_rules, list) or not raw_rules:
            raise ConfigError("rules must be a non-empty list")
        if len(raw_rules) > MAX_RULES:
            raise ConfigError(f"decision table has more than {MAX_RULES} rules")
        rules: list[Rule] = []
        for index, raw in enumerate(raw_rules):
            if not isinstance(raw, dict):
                raise ConfigError(f"rule {index} must be an object")
            unknown_rule = set(raw) - {"when", "then", "description"}
            if unknown_rule:
                raise ConfigError(f"rule {index} has unknown key(s): {', '.join(sorted(unknown_rule))}")
            when = raw.get("when")
            then = raw.get("then")
            if not isinstance(when, dict):
                raise ConfigError(f"rule {index} needs a 'when' object")
            if not isinstance(then, dict):
                raise ConfigError(f"rule {index} needs a 'then' object")
            unknown_inputs = set(when) - set(inputs)
            if unknown_inputs:
                raise ConfigError(f"rule {index} uses unknown input(s): {', '.join(sorted(unknown_inputs))}")
            for name, cell in when.items():
                _validate_cell(cell, f"rule {index} input '{name}'")
            missing_outputs = set(outputs) - set(then)
            if missing_outputs:
                raise ConfigError(f"rule {index} is missing output(s): {', '.join(sorted(missing_outputs))}")
            rules.append(Rule(when=dict(when), then=dict(then), index=index))
        default = data.get("default")
        if default is not None:
            if not isinstance(default, dict):
                raise ConfigError("default must be an object")
            missing = set(outputs) - set(default)
            if missing:
                raise ConfigError(f"default is missing output(s): {', '.join(sorted(missing))}")
        return cls(tuple(inputs), tuple(outputs), tuple(rules), dict(default) if default else None, hit_policy)

    def evaluate(self, inputs: Mapping[str, Any]) -> dict[str, Any]:
        missing = [name for name in self.inputs if name not in inputs]
        if missing:
            raise ConfigError(f"missing input(s): {', '.join(missing)}")
        for rule in self.rules:
            if all(_matches(rule.when[name], inputs[name]) for name in rule.when):
                return _outputs(rule.then, inputs, self.outputs, rule.index)
        if self.default is not None:
            return _outputs(self.default, inputs, self.outputs, -1)
        return {}


MAX_CELL_ITEMS = 100


def _validate_cell(cell: object, where: str) -> None:
    if isinstance(cell, list):
        if not cell:
            raise ConfigError(f"{where}: a cell list must not be empty")
        if len(cell) > MAX_CELL_ITEMS:
            raise ConfigError(f"{where}: a cell list has more than {MAX_CELL_ITEMS} items")
        for item in cell:
            _validate_cell(item, where)
        return
    if isinstance(cell, dict):
        raise ConfigError(f"{where}: a cell must be a scalar, a list of scalars, or '-'")
    if cell is None or isinstance(cell, (str, int, float, bool)):
        return
    raise ConfigError(f"{where}: unsupported cell type {type(cell).__name__}")


def _string_list(value: object, field: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise ConfigError(f"{field} must be a non-empty list of names")
    names: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ConfigError(f"{field} entries must be non-empty strings")
        names.append(item)
    duplicates = {name for name in names if names.count(name) > 1}
    if duplicates:
        raise ConfigError(f"{field} has duplicate(s): {', '.join(sorted(duplicates))}")
    return names


def _matches(cell: object, value: Any) -> bool:
    if isinstance(cell, list):
        return any(_matches(item, value) for item in cell)
    if cell == ANY:
        return True
    if isinstance(cell, str):
        return _match_text(cell, value)
    return equals(value, cell)


def _match_text(text: str, value: Any) -> bool:
    stripped = text.strip()
    if stripped == ANY:
        return True
    expression = stripped
    for operator in LEADING_OPERATORS:
        if expression.startswith(operator):
            expression = f"? {expression}"
            break
    try:
        node = parse(expression)
    except ParseError:
        return equals(value, text)
    return _eval_unary(node, value)


def _eval_unary(node: Node, value: Any) -> bool:
    if isinstance(node, Name):
        return equals(value, node.words[0])
    try:
        result = Evaluator({"?": value}).evaluate(node)
    except Exception:
        return False
    if isinstance(result, RangeValue):
        return result.contains(value) is True
    if isinstance(result, bool) or result is None:
        return result is True
    return equals(value, result)


def _outputs(
    cells: Mapping[str, object], inputs: Mapping[str, Any], outputs: tuple[str, ...], index: int
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for name in outputs:
        cell = cells[name]
        if isinstance(cell, str) and cell.startswith("="):
            try:
                node = parse(cell[1:])
            except ParseError as error:
                raise ConfigError(f"rule {index} output '{name}' is not a valid expression: {error.message}") from error
            result[name] = to_jsonable(Evaluator(inputs).evaluate(node))
        else:
            result[name] = to_jsonable(cell)
    return result


def decision_table(table: object, inputs: Mapping[str, Any]) -> dict[str, Any]:
    """Evaluate a decision-table mapping; values are converted to JSON-friendly types."""
    return DecisionTable.from_dict(table).evaluate(inputs)
