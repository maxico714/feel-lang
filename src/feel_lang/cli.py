"""Command-line interface: eval, parse, table, diff-oracle, doctor."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from dataclasses import fields
from pathlib import Path
from typing import Any, NoReturn

from . import __version__
from .errors import ArgumentError, ConfigError, EvalError, FeelError, OracleError, ParseError, TypeError_
from .evaluator import Evaluator, render
from .nodes import Node
from .oracle import evaluate_cases, find_oracle, load_cases
from .parser import parse
from .tables import decision_table
from .values import to_jsonable

EXIT_OK = 0
EXIT_EVAL = 1
EXIT_PARSE = 2
EXIT_ORACLE = 3
EXIT_USAGE = 4

MAX_JSON_BYTES = 5 * 1024 * 1024


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        self.print_usage(sys.stderr)
        self.exit(EXIT_USAGE, f"{self.prog}: error: {message}\n")


def build_parser() -> argparse.ArgumentParser:
    parser = _Parser(prog="feel-lang", description="Pure-Python FEEL expression evaluator and decision tables")
    parser.add_argument("--version", action="version", version=f"feel-lang {__version__}")
    commands = parser.add_subparsers(dest="command", required=True, parser_class=_Parser)

    evaluate_parser = commands.add_parser("eval", help="evaluate a FEEL expression")
    evaluate_parser.add_argument("expression")
    evaluate_parser.add_argument("--context", help="JSON file with the evaluation context")
    evaluate_parser.add_argument("--json", action="store_true", help="print the result as JSON")

    parse_parser = commands.add_parser("parse", help="parse an expression and print its AST")
    parse_parser.add_argument("expression")
    parse_parser.add_argument("--json", action="store_true", help="print the AST as JSON")
    parse_parser.add_argument("--dry-run", action="store_true", help="parse only; never evaluate")

    table_parser = commands.add_parser("table", help="evaluate a decision table")
    table_parser.add_argument("table", help="decision-table JSON file")
    table_parser.add_argument("--inputs", required=True, help="JSON file with input values")
    table_parser.add_argument("--json", action="store_true", help="print the result as JSON")

    oracle_parser = commands.add_parser("diff-oracle", help="compare against the dsntk oracle")
    oracle_parser.add_argument("--expressions", required=True, help="JSON file with {expression, context} cases")
    oracle_parser.add_argument("--oracle", help="path to the dsntk executable (or set FEEL_DSNTK)")
    oracle_parser.add_argument("--json", action="store_true", help="print the comparison as JSON")

    doctor_parser = commands.add_parser("doctor", help="check the installation")
    doctor_parser.add_argument("--json", action="store_true", help="machine-readable report")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    arguments = parser.parse_args(list(argv) if argv is not None else None)
    try:
        if arguments.command == "eval":
            return _command_eval(arguments)
        if arguments.command == "parse":
            return _command_parse(arguments)
        if arguments.command == "table":
            return _command_table(arguments)
        if arguments.command == "diff-oracle":
            return _command_oracle(arguments)
        if arguments.command == "doctor":
            return _command_doctor(arguments)
    except ParseError as error:
        print(f"parse error: {error}", file=sys.stderr)
        return EXIT_PARSE
    except (EvalError, TypeError_, ArgumentError) as error:
        print(f"eval error [{error.code}]: {error}", file=sys.stderr)
        return EXIT_EVAL
    except ConfigError as error:
        print(f"config error: {error}", file=sys.stderr)
        return EXIT_USAGE
    except OracleError as error:
        print(f"oracle error: {error}", file=sys.stderr)
        return EXIT_ORACLE
    except FeelError as error:  # pragma: no cover - defensive
        print(f"error [{error.code}]: {error}", file=sys.stderr)
        return EXIT_EVAL
    raise AssertionError(f"unhandled command {arguments.command}")  # pragma: no cover


def _load_json(path: str, what: str) -> Any:
    target = Path(path)
    try:
        size = target.stat().st_size
    except OSError as error:
        raise ConfigError(f"cannot read {what} file '{path}': {error}") from error
    if size > MAX_JSON_BYTES:
        raise ConfigError(f"{what} file '{path}' is larger than {MAX_JSON_BYTES} bytes")
    try:
        return json.loads(target.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError) as error:
        raise ConfigError(f"cannot read {what} file '{path}': {error}") from error
    except json.JSONDecodeError as error:
        raise ConfigError(f"{what} file '{path}' is not valid JSON: {error}") from error


def _command_eval(arguments: argparse.Namespace) -> int:
    context = _load_json(arguments.context, "context") if arguments.context else {}
    if not isinstance(context, dict):
        raise ConfigError("context must be a JSON object")
    value = Evaluator(context).evaluate(parse(arguments.expression))
    if arguments.json:
        print(json.dumps({"expression": arguments.expression, "result": to_jsonable(value)}, ensure_ascii=False))
    else:
        print(render(value))
    return EXIT_OK


def _command_parse(arguments: argparse.Namespace) -> int:
    node = parse(arguments.expression)
    if arguments.json:
        print(json.dumps(_node_to_dict(node), ensure_ascii=False))
    else:
        print(_format_node(node))
    return EXIT_OK


def _command_table(arguments: argparse.Namespace) -> int:
    table = _load_json(arguments.table, "table")
    inputs = _load_json(arguments.inputs, "inputs")
    if not isinstance(inputs, dict):
        raise ConfigError("inputs must be a JSON object")
    result = decision_table(table, inputs)
    if arguments.json:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    else:
        for name, value in result.items():
            print(f"{name}: {render(value)}")
        if not result:
            print("no match")
    return EXIT_OK


def _command_oracle(arguments: argparse.Namespace) -> int:
    cases = load_cases(arguments.expressions)
    oracle_path = find_oracle(arguments.oracle)
    results = evaluate_cases(cases, oracle_path)
    mismatches = [item for item in results if item.status != "match"]
    if arguments.json:
        print(json.dumps({"oracle": oracle_path, "results": [item.to_dict() for item in results]}, ensure_ascii=False))
    else:
        for item in results:
            if item.status == "match":
                print(f"match    {item.case.expression} -> {item.ours}")
            else:
                print(f"{item.status:8} {item.case.expression} -> ours: {item.ours} | dsntk: {item.theirs}")
        print(f"{len(results) - len(mismatches)}/{len(results)} match")
    return EXIT_OK if not mismatches else EXIT_EVAL


def _command_doctor(arguments: argparse.Namespace) -> int:
    oracle = None
    try:
        oracle = find_oracle(None)
    except OracleError:
        oracle = None
    report = {
        "version": __version__,
        "python": sys.version.split()[0],
        "platform": sys.platform,
        "oracle": oracle,
        "subset": 52,
    }
    if arguments.json:
        print(json.dumps(report, ensure_ascii=False))
    else:
        print(f"feel-lang {report['version']}")
        print(f"python: {report['python']} ({report['platform']})")
        print(f"oracle: {oracle or 'not found (optional; needed only for diff-oracle)'}")
        print("subset: literals, arithmetic, comparison, three-valued logic, ranges, lists,")
        print("        contexts, if-then-else, filters, 16 built-in functions, decision tables")
        print("OK")
    return EXIT_OK


def _node_to_dict(node: Node) -> dict[str, Any]:
    payload: dict[str, Any] = {"type": type(node).__name__}
    for field_info in fields(node):
        if field_info.name == "position":
            continue
        payload[field_info.name] = _ast_value(getattr(node, field_info.name))
    return payload


def _ast_value(value: object) -> Any:
    if isinstance(value, Node):
        return _node_to_dict(value)
    if isinstance(value, tuple):
        return [_ast_value(item) for item in value]
    return to_jsonable(value)


def _format_node(node: Node) -> str:
    return json.dumps(_node_to_dict(node), ensure_ascii=False, indent=2)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
