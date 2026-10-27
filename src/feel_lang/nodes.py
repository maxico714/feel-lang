"""AST node definitions for the FEEL subset."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from .values import Duration


@dataclass(frozen=True)
class Node:
    position: int = field(default=-1, compare=False, kw_only=True)


@dataclass(frozen=True)
class Literal(Node):
    value: object


@dataclass(frozen=True)
class Name(Node):
    """A (possibly multi-word) name reference with an optional context path."""

    words: tuple[str, ...]
    path: tuple[str, ...] = ()


@dataclass(frozen=True)
class Placeholder(Node):
    """The `?` input placeholder used by decision-table cells."""


@dataclass(frozen=True)
class Unary(Node):
    operator: str
    operand: Node


@dataclass(frozen=True)
class Binary(Node):
    operator: str
    left: Node
    right: Node


@dataclass(frozen=True)
class If(Node):
    condition: Node
    then: Node
    otherwise: Node


@dataclass(frozen=True)
class Between(Node):
    value: Node
    low: Node
    high: Node


@dataclass(frozen=True)
class Membership(Node):
    value: Node
    tests: tuple[Node, ...]


@dataclass(frozen=True)
class Call(Node):
    name: str
    arguments: tuple[Node, ...]


@dataclass(frozen=True)
class Range(Node):
    low: Node | None
    high: Node | None
    include_low: bool
    include_high: bool


@dataclass(frozen=True)
class ListLiteral(Node):
    items: tuple[Node, ...]


@dataclass(frozen=True)
class ContextLiteral(Node):
    entries: tuple[tuple[str, Node], ...]


@dataclass(frozen=True)
class Index(Node):
    target: Node
    index: Node


@dataclass(frozen=True)
class ContextAccess(Node):
    target: Node
    key: str


Number = Decimal
__all__ = [
    "Between",
    "Binary",
    "Call",
    "ContextAccess",
    "ContextLiteral",
    "Duration",
    "If",
    "Index",
    "ListLiteral",
    "Literal",
    "Membership",
    "Name",
    "Node",
    "Number",
    "Placeholder",
    "Range",
    "Unary",
]
