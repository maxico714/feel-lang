"""Recursive-descent parser for the FEEL subset described in docs/FEEL_SUBSET.md."""

from __future__ import annotations

from decimal import Decimal

from .errors import ParseError
from .lexer import Token, tokenize
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

MAX_DEPTH = 100
MAX_LIST_ITEMS = 10_000

COMPARISONS = {"=", "!=", "<", "<=", ">", ">="}


class Parser:
    def __init__(self, tokens: list[Token]) -> None:
        self.tokens = tokens
        self.index = 0
        self.depth = 0
        self.no_index = 0

    # -- token helpers -----------------------------------------------------
    def peek(self, offset: int = 0) -> Token:
        position = min(self.index + offset, len(self.tokens) - 1)
        return self.tokens[position]

    def advance(self) -> Token:
        token = self.peek()
        if token.kind != "EOF":
            self.index += 1
        return token

    def match_op(self, *operators: str) -> Token | None:
        token = self.peek()
        if token.kind == "OP" and token.value in operators:
            return self.advance()
        return None

    def match_keyword(self, *words: str) -> Token | None:
        token = self.peek()
        if token.kind == "KEYWORD" and token.value in words:
            return self.advance()
        return None

    def expect_op(self, operator: str) -> Token:
        token = self.match_op(operator)
        if token is None:
            raise ParseError(f"expected '{operator}'", position=self.peek().position)
        return token

    def expect_keyword(self, word: str) -> Token:
        token = self.match_keyword(word)
        if token is None:
            raise ParseError(f"expected '{word}'", position=self.peek().position)
        return token

    # -- grammar -----------------------------------------------------------
    def parse(self) -> Node:
        node = self.expression()
        token = self.peek()
        if token.kind != "EOF":
            if token.kind == "KEYWORD" and token.value in {"instance", "of"}:
                raise ParseError("'instance of' is not part of the v0.1 subset", position=token.position)
            raise ParseError(f"unexpected token {token.value!r}", position=token.position)
        return node

    def expression(self) -> Node:
        self.depth += 1
        if self.depth > MAX_DEPTH:
            raise ParseError("expression nests too deeply", position=self.peek().position)
        try:
            if self.match_keyword("if") is not None:
                condition = self.expression()
                self.expect_keyword("then")
                then = self.expression()
                self.expect_keyword("else")
                otherwise = self.expression()
                return If(condition, then, otherwise)
            return self.or_expression()
        finally:
            self.depth -= 1

    def or_expression(self) -> Node:
        node = self.and_expression()
        while self.match_keyword("or") is not None:
            node = Binary("or", node, self.and_expression())
        return node

    def and_expression(self) -> Node:
        node = self.comparison()
        while self.match_keyword("and") is not None:
            node = Binary("and", node, self.comparison())
        return node

    def comparison(self) -> Node:
        node = self.additive()
        token = self.peek()
        if token.kind == "OP" and token.value in COMPARISONS:
            operator = str(self.advance().value)
            node = Binary(operator, node, self.additive())
            return node
        if self.match_keyword("between") is not None:
            low = self.additive()
            self.expect_keyword("and")
            high = self.additive()
            return Between(node, low, high)
        if self.match_keyword("in") is not None:
            return Membership(node, self.membership_tests())
        return node

    def membership_tests(self) -> tuple[Node, ...]:
        if self.peek().kind == "OP" and self.peek().value == "(" and self.is_range_ahead():
            self.advance()
            low = self.range_bound()
            self.expect_op("..")
            high = None if self.peek().kind == "OP" and self.peek().value == ")" else self.range_bound()
            self.expect_op(")")
            return (Range(low, high, False, False, position=low.position),)
        if self.match_op("(") is not None:
            tests = [self.membership_item()]
            while self.match_op(",") is not None:
                tests.append(self.membership_item())
            self.expect_op(")")
            return tuple(tests)
        return (self.membership_item(),)

    def membership_item(self) -> Node:
        if self.peek().kind == "OP" and self.peek().value == "]":
            return self.range_literal()
        if self.peek().kind == "OP" and self.peek().value == "[":
            if self.is_range_ahead():
                return self.range_literal()
            return self.list_or_range()
        return self.additive()

    def is_range_ahead(self) -> bool:
        depth = 0
        offset = 0
        while True:
            token = self.peek(offset)
            if token.kind == "EOF":
                return False
            if token.kind == "OP" and token.value in {"[", "(", "{"}:
                depth += 1
            elif token.kind == "OP" and token.value in {"]", ")", "}"}:
                depth -= 1
                if depth == 0:
                    return False
            elif token.kind == "OP" and token.value == ".." and depth == 1:
                return True
            offset += 1
            if offset > 256:
                return False

    def additive(self) -> Node:
        node = self.multiplicative()
        while True:
            token = self.match_op("+", "-")
            if token is None:
                return node
            node = Binary(str(token.value), node, self.multiplicative())

    def multiplicative(self) -> Node:
        node = self.power()
        while True:
            token = self.match_op("*", "/")
            if token is None:
                return node
            node = Binary(str(token.value), node, self.power())

    def power(self) -> Node:
        self.depth += 1
        if self.depth > MAX_DEPTH:
            raise ParseError("expression nests too deeply", position=self.peek().position)
        try:
            node = self.unary()
            if self.match_op("**") is not None:
                return Binary("**", node, self.power())
            return node
        finally:
            self.depth -= 1

    def unary(self) -> Node:
        self.depth += 1
        if self.depth > MAX_DEPTH:
            raise ParseError("expression nests too deeply", position=self.peek().position)
        try:
            token = self.match_op("-", "+")
            if token is not None:
                operand = self.unary()
                if token.value == "+":
                    return operand
                return Unary("-", operand)
            return self.postfix()
        finally:
            self.depth -= 1

    def postfix(self) -> Node:
        node = self.primary()
        while True:
            if self.no_index == 0 and self.match_op("[") is not None:
                index = self.expression()
                self.expect_op("]")
                node = Index(node, index)
                continue
            if self.match_op(".") is not None:
                node = ContextAccess(node, self.name_words(allow_keywords=False))
                continue
            return node

    def range_bound(self) -> Node:
        """Parse a range bound without letting it consume the closing bracket as an index."""
        self.no_index += 1
        try:
            return self.expression()
        finally:
            self.no_index -= 1

    def primary(self) -> Node:
        token = self.peek()
        if token.kind == "NUMBER":
            self.advance()
            return Literal(Decimal(str(token.value)), position=token.position)
        if token.kind == "STRING":
            self.advance()
            return Literal(str(token.value), position=token.position)
        if token.kind == "AT_STRING":
            self.advance()
            return Literal(_parse_at_literal(str(token.value), token.position), position=token.position)
        if token.kind == "KEYWORD" and token.value in {"true", "false", "null"}:
            self.advance()
            value = {"true": True, "false": False, "null": None}[str(token.value)]
            return Literal(value, position=token.position)
        if token.kind == "KEYWORD" and token.value == "not":
            self.advance()
            self.expect_op("(")
            argument = self.expression()
            self.expect_op(")")
            return Call("not", (argument,), position=token.position)
        if token.kind == "OP" and token.value == "?":
            self.advance()
            return Placeholder(position=token.position)
        if token.kind == "OP" and token.value == "(":
            self.advance()
            node = self.expression()
            self.expect_op(")")
            return node
        if token.kind == "OP" and token.value == "{":
            return self.context_literal()
        if token.kind == "OP" and token.value == "[":
            return self.list_or_range()
        if token.kind == "OP" and token.value == "]":
            return self.range_literal()
        if token.kind == "NAME":
            return self.name_or_call()
        raise ParseError(f"unexpected token {token.value!r}", position=token.position)

    def list_or_range(self) -> Node:
        start = self.expect_op("[")
        if self.match_op("]") is not None:
            return ListLiteral((), position=start.position)
        first = self.expression()
        if self.match_op("..") is not None:
            high = None if self.peek().kind == "OP" and self.peek().value in {"]", "["} else self.range_bound()
            include_high = self.expect_range_close()
            return Range(first, high, True, include_high, position=start.position)
        items = [first]
        while self.match_op(",") is not None:
            items.append(self.expression())
            if len(items) > MAX_LIST_ITEMS:
                raise ParseError(f"list literal has more than {MAX_LIST_ITEMS} items", position=start.position)
        self.expect_op("]")
        return ListLiteral(tuple(items), position=start.position)

    def range_literal(self) -> Node:
        start = self.advance()
        include_low = start.value == "["
        low = None if self.peek().kind == "OP" and self.peek().value == ".." else self.range_bound()
        self.expect_op("..")
        if self.peek().kind == "OP" and self.peek().value in {"]", "["}:
            high = None
            include_high = self.expect_range_close()
        else:
            high = self.range_bound()
            include_high = self.expect_range_close()
        return Range(low, high, include_low, include_high, position=start.position)

    def expect_range_close(self) -> bool:
        token = self.peek()
        if token.kind == "OP" and token.value in {"]", "["}:
            self.advance()
            return token.value == "]"
        raise ParseError("expected ']' or '[' to close the range", position=token.position)

    def name_or_call(self) -> Node:
        start = self.peek()
        joined = self.name_words(allow_keywords=False)
        if (
            joined == "date"
            and self.peek().kind == "KEYWORD"
            and self.peek().value == "and"
            and self.peek(1).kind == "NAME"
            and self.peek(1).value == "time"
        ):
            self.advance()
            self.advance()
            joined = "date and time"
        if self.match_op("(") is not None:
            arguments = self.call_arguments()
            return Call(joined, arguments, position=start.position)
        return Name((joined,), position=start.position)

    def name_words(self, *, allow_keywords: bool) -> str:
        parts: list[str] = []
        while True:
            token = self.peek()
            if token.kind == "NAME" or (allow_keywords and token.kind == "KEYWORD"):
                parts.append(str(self.advance().value))
                continue
            break
        if not parts:
            raise ParseError("expected a name", position=self.peek().position)
        return " ".join(parts)

    def context_literal(self) -> Node:
        start = self.expect_op("{")
        entries: list[tuple[str, Node]] = []
        if self.match_op("}") is not None:
            return ContextLiteral(tuple(entries), position=start.position)
        while True:
            key_token = self.peek()
            if key_token.kind == "STRING":
                self.advance()
                key = str(key_token.value)
            else:
                key = self.name_words(allow_keywords=True)
            self.expect_op(":")
            entries.append((key, self.expression()))
            if self.match_op(",") is not None:
                continue
            self.expect_op("}")
            return ContextLiteral(tuple(entries), position=start.position)

    def call_arguments(self) -> tuple[Node, ...]:
        arguments: list[Node] = []
        if self.match_op(")") is not None:
            return ()
        arguments.append(self.expression())
        while self.match_op(",") is not None:
            arguments.append(self.expression())
            if len(arguments) > MAX_LIST_ITEMS:
                raise ParseError("too many arguments", position=self.peek().position)
        self.expect_op(")")
        return tuple(arguments)


def parse(text: str) -> Node:
    """Parse a FEEL expression into an AST, raising ParseError on invalid input."""
    return Parser(tokenize(text)).parse()


def _parse_at_literal(text: str, position: int) -> object:
    """Temporal literal after '@': duration, date-time, date or time."""
    from .values import Duration, parse_date, parse_datetime, parse_time

    if text.startswith("P"):
        duration = Duration.parse(text)
        if duration is not None:
            return duration
    if "T" in text:
        moment = parse_datetime(text)
        if moment is not None:
            return moment
    if "-" in text:
        day = parse_date(text)
        if day is not None:
            return day
    if ":" in text:
        clock = parse_time(text)
        if clock is not None:
            return clock
    raise ParseError(f"invalid @literal {text!r}", position=position)
