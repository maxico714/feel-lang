"""Structured errors with stable rule ids."""

from __future__ import annotations


class FeelError(Exception):
    """Base class for every error raised by feel-lang."""

    code = "E_FEEL"

    def __init__(self, message: str, *, position: int = -1) -> None:
        self.message = message
        self.position = position
        super().__init__(message if position < 0 else f"{message} (at {position})")

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {"code": self.code, "message": self.message}
        if self.position >= 0:
            payload["position"] = self.position
        return payload


class ParseError(FeelError):
    code = "E_PARSE"


class EvalError(FeelError):
    code = "E_EVAL"


class TypeError_(FeelError):
    """Type mismatch. Named with a trailing underscore to avoid shadowing builtins."""

    code = "E_TYPE"


class ArgumentError(FeelError):
    code = "E_ARG"


class ConfigError(FeelError):
    code = "E_CONFIG"


class OracleError(FeelError):
    code = "E_ORACLE"
