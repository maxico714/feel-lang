"""Tokenizer for the FEEL subset. Bounded: input length and token count are capped."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .errors import ParseError
from .values import decimal_within_limits

MAX_INPUT_CHARS = 20_000
MAX_TOKENS = 5_000

KEYWORDS = frozenset(
    {
        "true",
        "false",
        "null",
        "if",
        "then",
        "else",
        "and",
        "or",
        "not",
        "in",
        "between",
        "instance",
        "of",
    }
)

TWO_CHAR_OPERATORS = {"**", "..", "!=", "<=", ">="}
ONE_CHAR_OPERATORS = set("+-*/=<>()[]{},:.?")


# `[` and `]` start ranges as well as lists; `]` alone is an open range bound.
@dataclass(frozen=True)
class Token:
    kind: str
    value: object
    position: int

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"Token({self.kind}, {self.value!r})"


def tokenize(text: str) -> list[Token]:
    if not isinstance(text, str):
        raise ParseError("expression must be a string", position=0)
    if len(text) > MAX_INPUT_CHARS:
        raise ParseError(f"expression longer than {MAX_INPUT_CHARS} characters", position=0)
    tokens: list[Token] = []
    index = 0
    length = len(text)
    while index < length:
        char = text[index]
        if char.isspace():
            index += 1
            continue
        if char == "/" and index + 1 < length and text[index + 1] == "/":
            break
        if char == "/" and index + 1 < length and text[index + 1] == "*":
            end = text.find("*/", index + 2)
            if end < 0:
                raise ParseError("unterminated comment", position=index)
            index = end + 2
            continue
        if char == "@":
            start = index
            literal, index = _read_at_literal(text, index)
            tokens.append(Token("AT_STRING", literal, start))
            _check_limit(tokens, index)
            continue
        if char == '"':
            start = index
            literal, index = _read_string(text, index)
            tokens.append(Token("STRING", literal, start))
            _check_limit(tokens, index)
            continue
        if char.isdigit() or (char == "." and index + 1 < length and text[index + 1].isdigit()):
            start = index
            numeric, index = _read_number(text, index)
            tokens.append(Token("NUMBER", numeric, start))
            _check_limit(tokens, index)
            continue
        if char.isalpha() or char == "_":
            start = index
            word, index = _read_name(text, index)
            kind = "KEYWORD" if word in KEYWORDS else "NAME"
            tokens.append(Token(kind, word, start))
            _check_limit(tokens, index)
            continue
        two = text[index : index + 2]
        if two in TWO_CHAR_OPERATORS:
            tokens.append(Token("OP", two, index))
            index += 2
            _check_limit(tokens, index)
            continue
        if char in ONE_CHAR_OPERATORS:
            tokens.append(Token("OP", char, index))
            index += 1
            _check_limit(tokens, index)
            continue
        raise ParseError(f"unexpected character {char!r}", position=index)
    tokens.append(Token("EOF", None, length))
    return tokens


def _check_limit(tokens: list[Token], position: int) -> None:
    if len(tokens) > MAX_TOKENS:
        raise ParseError(f"expression has more than {MAX_TOKENS} tokens", position=position)


def _read_name(text: str, index: int) -> tuple[str, int]:
    start = index
    while index < len(text) and (text[index].isalnum() or text[index] == "_"):
        index += 1
    return text[start:index], index


def _read_number(text: str, index: int) -> tuple[Decimal, int]:
    start = index
    seen_dot = False
    while index < len(text):
        char = text[index]
        if char.isdigit():
            index += 1
        elif char == "." and not seen_dot and index + 1 < len(text) and text[index + 1].isdigit():
            seen_dot = True
            index += 1
        else:
            break
    if index < len(text) and text[index] in "eE":
        probe = index + 1
        if probe < len(text) and text[probe] in "+-":
            probe += 1
        digits = probe
        while probe < len(text) and text[probe].isdigit():
            probe += 1
        if probe > digits:
            index = probe
    literal = text[start:index]
    try:
        value = Decimal(literal)
    except Exception as error:  # pragma: no cover - Decimal accepts what we lex
        raise ParseError(f"invalid number {literal!r}", position=start) from error
    if not decimal_within_limits(value):
        raise ParseError("number literal is outside the supported decimal range", position=start)
    return value, index


def _read_string(text: str, index: int) -> tuple[str, int]:
    start = index
    index += 1
    pieces: list[str] = []
    while index < len(text):
        char = text[index]
        if char == "\\":
            if index + 1 >= len(text):
                raise ParseError("unterminated escape sequence", position=index)
            escaped = text[index + 1]
            mapping = {'"': '"', "\\": "\\", "n": "\n", "t": "\t", "r": "\r"}
            if escaped in mapping:
                pieces.append(mapping[escaped])
                index += 2
                continue
            if escaped == "u":
                digits = text[index + 2 : index + 6]
                if len(digits) != 4 or any(item not in "0123456789abcdefABCDEF" for item in digits):
                    raise ParseError("invalid unicode escape", position=index)
                codepoint = int(digits, 16)
                if 0xD800 <= codepoint <= 0xDFFF:
                    raise ParseError("unicode escape is a lone surrogate", position=index)
                pieces.append(chr(codepoint))
                index += 6
                continue
            raise ParseError(f"invalid escape sequence '\\{escaped}'", position=index)
        if char == '"':
            return "".join(pieces), index + 1
        pieces.append(char)
        index += 1
    raise ParseError("unterminated string literal", position=start)


def _read_at_literal(text: str, index: int) -> tuple[str, int]:
    start = index
    index += 1
    if index >= len(text) or text[index] != '"':
        raise ParseError("expected a quoted literal after '@'", position=start)
    literal, end = _read_string(text, index)
    return literal, end
