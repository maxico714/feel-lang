"""Evaluator for the FEEL subset. Three-valued logic, exact decimals, no eval()."""

from __future__ import annotations

import datetime as _dt
import json
import math
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal, DecimalException
from typing import Any

from .errors import ArgumentError, EvalError
from .nodes import (
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
    Node,
    Placeholder,
    Range,
    Unary,
)
from .values import (
    Duration,
    add_duration,
    decimal_within_limits,
    format_number,
    is_number,
    number,
    parse_date,
    parse_datetime,
    parse_time,
    to_decimal,
)


@dataclass(frozen=True)
class RangeValue:
    low: Any
    high: Any
    include_low: bool
    include_high: bool

    def contains(self, value: Any) -> bool | None:
        if self.low is not None:
            lower = compare(value, self.low)
            if lower is None:
                return None
            if lower < 0 or (lower == 0 and not self.include_low):
                return False
        if self.high is not None:
            upper = compare(value, self.high)
            if upper is None:
                return None
            if upper > 0 or (upper == 0 and not self.include_high):
                return False
        return True

    def __str__(self) -> str:
        low = "" if self.low is None else render(self.low)
        high = "" if self.high is None else render(self.high)
        return f"{'[' if self.include_low else ']'}{low}..{high}{']' if self.include_high else '['}"


def compare(left: Any, right: Any) -> int | None:
    """Three-way comparison for compatible values, else None."""
    if left is None or right is None:
        return None
    if is_number(left) and is_number(right):
        left_number, right_number = to_decimal(left), to_decimal(right)
        return (left_number > right_number) - (left_number < right_number)
    if isinstance(left, str) and isinstance(right, str):
        return (left > right) - (left < right)
    if isinstance(left, (_dt.date, _dt.time, _dt.datetime)) and type(left) is type(right):
        return (left > right) - (left < right)  # type: ignore[operator]
    if isinstance(left, Duration) and isinstance(right, Duration):
        if left.kind != right.kind:
            return None
        if left.months != right.months:
            return (left.months > right.months) - (left.months < right.months)
        return (left.seconds > right.seconds) - (left.seconds < right.seconds)
    return None


def equals(left: Any, right: Any) -> bool:
    if left is None or right is None:
        return left is None and right is None
    if is_number(left) and is_number(right):
        return to_decimal(left) == to_decimal(right)
    if isinstance(left, bool) or isinstance(right, bool):
        return isinstance(left, bool) and isinstance(right, bool) and left == right
    if isinstance(left, str) and isinstance(right, str):
        return left == right
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(equals(a, b) for a, b in zip(left, right, strict=True))
    if isinstance(left, dict) and isinstance(right, dict):
        if set(left) != set(right):
            return False
        return all(equals(left[key], right[key]) for key in left)
    if isinstance(left, RangeValue) and isinstance(right, RangeValue):
        return (
            equals(left.low, right.low)
            and equals(left.high, right.high)
            and left.include_low == right.include_low
            and left.include_high == right.include_high
        )
    if isinstance(left, Duration) and isinstance(right, Duration):
        return left == right
    if isinstance(left, (_dt.date, _dt.time, _dt.datetime)) and type(left) is type(right):
        return bool(left == right)
    return False


def render(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, Decimal):
        return format_number(value)
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, RangeValue):
        return str(value)
    if isinstance(value, (Duration, _dt.date, _dt.time, _dt.datetime)):
        return value.isoformat()
    if isinstance(value, list):
        return "[" + ", ".join(render(item) for item in value) + "]"
    if isinstance(value, dict):
        return "{" + ", ".join(f"{key}: {render(item)}" for key, item in value.items()) + "}"
    return str(value)


class Evaluator:
    def __init__(self, context: Mapping[str, Any] | None = None) -> None:
        self.context = dict(context or {})
        self.placeholder: Any = self.context.get("?")
        self.has_placeholder = "?" in self.context

    def evaluate(self, node: Node) -> Any:
        method = getattr(self, f"_eval_{type(node).__name__.lower()}", None)
        if method is None:  # pragma: no cover - every node has a method
            raise EvalError(f"unsupported node {type(node).__name__}", position=node.position)
        value = method(node)
        if isinstance(value, Decimal) and not decimal_within_limits(value):
            return None
        return value

    # -- nodes -------------------------------------------------------------
    def _eval_literal(self, node: Literal) -> Any:
        return node.value

    def _eval_placeholder(self, node: Placeholder) -> Any:
        if not self.has_placeholder:
            raise EvalError("no value bound to '?'", position=node.position)
        return self.placeholder

    def _eval_name(self, node: Name) -> Any:
        key = node.words[0]
        if key in self.context:
            value = self.context[key]
            return _coerce(value)
        if len(node.words) > 1:
            joined = " ".join(node.words)
            if joined in self.context:
                return _coerce(self.context[joined])
        return None

    def _eval_contextaccess(self, node: ContextAccess) -> Any:
        target = self.evaluate(node.target)
        if isinstance(target, dict):
            return _coerce(target.get(node.key))
        return None

    def _eval_index(self, node: Index) -> Any:
        target = self.evaluate(node.target)
        index = self.evaluate(node.index)
        if target is None or index is None:
            return None
        if isinstance(index, bool):
            return list(target) if index and isinstance(target, list) else []
        if is_number(index) and isinstance(target, list):
            position = to_decimal(index)
            if position != position.to_integral_value():
                return None
            offset = int(position)
            if 0 < offset <= len(target):
                return target[offset - 1]
            if -len(target) <= offset < 0:
                return target[offset]
            return None
        return None

    def _eval_unary(self, node: Unary) -> Any:
        value = self.evaluate(node.operand)
        if value is None:
            return None
        if node.operator == "-" and is_number(value):
            return -to_decimal(value)
        return None

    def _eval_binary(self, node: Binary) -> Any:
        if node.operator == "and":
            return self._and(node)
        if node.operator == "or":
            return self._or(node)
        left = self.evaluate(node.left)
        right = self.evaluate(node.right)
        operator = node.operator
        if operator in {"=", "!="}:
            if operator == "=":
                return equals(left, right)
            return not equals(left, right)
        if operator in {"<", "<=", ">", ">="}:
            order = compare(left, right)
            if order is None:
                return None
            return {"<": order < 0, "<=": order <= 0, ">": order > 0, ">=": order >= 0}[operator]
        return self._arithmetic(operator, left, right)

    def _and(self, node: Binary) -> Any:
        left = self.evaluate(node.left)
        if left is False:
            return False
        right = self.evaluate(node.right)
        if right is False:
            return False
        return True if left is True and right is True else None

    def _or(self, node: Binary) -> Any:
        left = self.evaluate(node.left)
        if left is True:
            return True
        right = self.evaluate(node.right)
        if right is True:
            return True
        return False if left is False and right is False else None

    def _arithmetic(self, operator: str, left: Any, right: Any) -> Any:
        if operator == "+":
            if left is None or right is None:
                return None
            if isinstance(left, Duration) and isinstance(right, (_dt.date, _dt.time, _dt.datetime)):
                return add_duration(right, left)
            if isinstance(left, (_dt.date, _dt.time, _dt.datetime)) and isinstance(right, Duration):
                return add_duration(left, right)
        if left is None or right is None:
            return None
        if operator == "+" and isinstance(left, str) and isinstance(right, str):
            return left + right
        if not (is_number(left) and is_number(right)):
            return None
        left_number, right_number = to_decimal(left), to_decimal(right)
        try:
            if operator == "+":
                return left_number + right_number
            if operator == "-":
                return left_number - right_number
            if operator == "*":
                return left_number * right_number
            if operator == "/":
                if right_number == 0:
                    return None
                return left_number / right_number
            if operator == "**":
                return _power(left_number, right_number)
        except (DecimalException, OverflowError, ValueError):
            return None
        return None

    def _eval_if(self, node: If) -> Any:
        condition = self.evaluate(node.condition)
        return self.evaluate(node.then) if condition is True else self.evaluate(node.otherwise)

    def _eval_between(self, node: Between) -> Any:
        value = self.evaluate(node.value)
        low = self.evaluate(node.low)
        high = self.evaluate(node.high)
        if value is None or low is None or high is None:
            return None
        lower = compare(value, low)
        upper = compare(value, high)
        if lower is None or upper is None:
            return None
        return lower >= 0 and upper <= 0

    def _eval_membership(self, node: Membership) -> Any:
        value = self.evaluate(node.value)
        if value is None:
            return None
        result: bool = False
        for test in node.tests:
            candidate = self.evaluate(test)
            if isinstance(candidate, RangeValue):
                outcome = candidate.contains(value)
                if outcome is True:
                    return True
                if outcome is None:
                    result = False
                continue
            if equals(value, candidate):
                return True
        return result

    def _eval_range(self, node: Range) -> RangeValue:
        low = None if node.low is None else self.evaluate(node.low)
        high = None if node.high is None else self.evaluate(node.high)
        return RangeValue(low, high, node.include_low, node.include_high)

    def _eval_listliteral(self, node: ListLiteral) -> Any:
        return [self.evaluate(item) for item in node.items]

    def _eval_contextliteral(self, node: ContextLiteral) -> Any:
        return {key: self.evaluate(value) for key, value in node.entries}

    def _eval_call(self, node: Call) -> Any:
        handler = _BUILTINS.get(node.name)
        if handler is None:
            raise EvalError(f"unknown function '{node.name}'", position=node.position)
        arguments = [self.evaluate(argument) for argument in node.arguments]
        return handler(arguments)


def _coerce(value: Any) -> Any:
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, int):
        if value.bit_length() > 333:
            return None
        decimal = Decimal(value)
        return decimal if decimal_within_limits(decimal) else None
    if isinstance(value, float):
        if not math.isfinite(value):
            return None
        decimal = Decimal(str(value))
        return decimal if decimal_within_limits(decimal) else None
    if isinstance(value, Decimal):
        return value if decimal_within_limits(value) else None
    return value


def _power(base: Decimal, exponent: Decimal) -> Decimal | None:
    if exponent == exponent.to_integral_value():
        power = int(exponent)
        if abs(power) > 10_000:
            return None
        try:
            return base**power
        except (DecimalException, OverflowError):
            return None
    if base <= 0:
        return None
    try:
        return Decimal(str(float(base) ** float(exponent)))
    except (DecimalException, OverflowError, ValueError):
        return None


# -- built-in functions ----------------------------------------------------
def _as_list(arguments: list[Any]) -> list[Any] | None:
    if len(arguments) == 1 and isinstance(arguments[0], list):
        return arguments[0]
    return None


def _count(arguments: list[Any]) -> Any:
    _arity("count", arguments, 1)
    value = arguments[0]
    if value is None:
        return Decimal(0)
    return Decimal(len(value)) if isinstance(value, list) else Decimal(1)


def _numbers(arguments: list[Any]) -> list[Decimal] | None:
    values = _as_list(arguments) if len(arguments) == 1 else arguments
    if values is None:
        return None
    numbers: list[Decimal] = []
    for value in values:
        if not is_number(value):
            return None
        numbers.append(to_decimal(value))
    return numbers


def _sum(arguments: list[Any]) -> Any:
    _arity("sum", arguments, 1)
    numbers = _numbers(arguments)
    if numbers is None or not numbers:
        return None
    return sum(numbers, Decimal(0))


def _min(arguments: list[Any]) -> Any:
    _arity_range("min", arguments, 1, 1_000)
    numbers = _numbers(arguments)
    return None if not numbers else min(numbers)


def _max(arguments: list[Any]) -> Any:
    _arity_range("max", arguments, 1, 1_000)
    numbers = _numbers(arguments)
    return None if not numbers else max(numbers)


def _mean(arguments: list[Any]) -> Any:
    _arity("mean", arguments, 1)
    numbers = _numbers(arguments)
    if not numbers:
        return None
    return sum(numbers, Decimal(0)) / Decimal(len(numbers))


def _all(arguments: list[Any]) -> Any:
    _arity("all", arguments, 1)
    values = arguments[0]
    if not isinstance(values, list):
        return None
    if not values:
        return True
    result: bool | None = True
    for value in values:
        if value is False:
            return False
        if value is not True:
            result = None
    return result


def _any(arguments: list[Any]) -> Any:
    _arity("any", arguments, 1)
    values = arguments[0]
    if not isinstance(values, list):
        return None
    if not values:
        return False
    result: bool | None = False
    for value in values:
        if value is True:
            return True
        if value is not False:
            result = None
    return result


def _contains(arguments: list[Any]) -> Any:
    _arity("contains", arguments, 2)
    text, match = arguments
    if not isinstance(text, str) or not isinstance(match, str):
        return None
    return match in text


def _substring(arguments: list[Any]) -> Any:
    _arity_range("substring", arguments, 2, 3)
    text, start = arguments[0], arguments[1]
    length = arguments[2] if len(arguments) == 3 else None
    if not isinstance(text, str) or not is_number(start):
        return None
    start_number = to_decimal(start)
    if start_number != start_number.to_integral_value():
        return None
    start_index = int(start_number)
    if start_index < 1 or start_index > len(text):
        return None
    end = len(text) + 1
    if length is not None:
        if not is_number(length):
            return None
        length_number = to_decimal(length)
        if length_number < 0 or length_number != length_number.to_integral_value():
            return None
        end = start_index + int(length_number)
    return text[start_index - 1 : end - 1]


def _string(arguments: list[Any]) -> Any:
    _arity("string", arguments, 1)
    value = arguments[0]
    if value is None:
        return None
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return value
    if isinstance(value, Decimal):
        return format_number(value)
    if isinstance(value, Duration):
        return value.isoformat()
    if isinstance(value, (_dt.date, _dt.time, _dt.datetime)):
        return value.isoformat()
    return None


def _number(arguments: list[Any]) -> Any:
    _arity("number", arguments, 3)
    text, group_separator, decimal_separator = arguments
    if not all(isinstance(item, str) for item in arguments):
        return None
    if not group_separator:
        return None
    normalized = str(text).replace(str(group_separator), "").replace(str(decimal_separator), ".")
    return number(normalized)


def _date(arguments: list[Any]) -> Any:
    if len(arguments) == 1 and isinstance(arguments[0], str):
        return parse_date(arguments[0])
    if len(arguments) == 1 and isinstance(arguments[0], _dt.datetime):
        return arguments[0].date()
    _arity("date", arguments, 3)
    year, month, day = arguments
    if not all(is_number(item) for item in arguments):
        return None
    try:
        return _dt.date(int(to_decimal(year)), int(to_decimal(month)), int(to_decimal(day)))
    except ValueError:
        return None


def _time(arguments: list[Any]) -> Any:
    if len(arguments) == 1 and isinstance(arguments[0], str):
        return parse_time(arguments[0])
    _arity("time", arguments, 3)
    hour, minute, second = arguments
    if not all(is_number(item) for item in arguments):
        return None
    try:
        return _dt.time(int(to_decimal(hour)), int(to_decimal(minute)), int(to_decimal(second)))
    except ValueError:
        return None


def _date_and_time(arguments: list[Any]) -> Any:
    if len(arguments) == 1 and isinstance(arguments[0], str):
        return parse_datetime(arguments[0])
    _arity("date and time", arguments, 2)
    date_value, time_value = arguments
    if isinstance(date_value, _dt.datetime):
        date_value = date_value.date()
    if not isinstance(date_value, _dt.date) or not isinstance(time_value, _dt.time):
        return None
    return _dt.datetime.combine(date_value, time_value)


def _duration(arguments: list[Any]) -> Any:
    _arity("duration", arguments, 1)
    if not isinstance(arguments[0], str):
        return None
    return Duration.parse(arguments[0])


def _not(arguments: list[Any]) -> Any:
    _arity("not", arguments, 1)
    value = arguments[0]
    if value is None:
        return None
    return (not value) if isinstance(value, bool) else None


def _arity(name: str, arguments: list[Any], count: int) -> None:
    if len(arguments) != count:
        raise ArgumentError(f"{name} expects {count} argument(s), got {len(arguments)}")


def _arity_range(name: str, arguments: list[Any], low: int, high: int) -> None:
    if not low <= len(arguments) <= high:
        raise ArgumentError(f"{name} expects between {low} and {high} argument(s), got {len(arguments)}")


_BUILTINS: dict[str, Any] = {
    "count": _count,
    "sum": _sum,
    "min": _min,
    "max": _max,
    "mean": _mean,
    "all": _all,
    "any": _any,
    "contains": _contains,
    "substring": _substring,
    "string": _string,
    "number": _number,
    "date": _date,
    "time": _time,
    "date and time": _date_and_time,
    "duration": _duration,
    "not": _not,
}
