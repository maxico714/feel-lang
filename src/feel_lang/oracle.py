"""Optional differential oracle: run dsntk (Apache-2.0) on the same expressions."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .errors import OracleError
from .evaluator import Evaluator, render
from .parser import parse
from .values import to_jsonable

TIMEOUT_SECONDS = 20
MAX_EXPRESSIONS = 500
MAX_CASES_BYTES = 5 * 1024 * 1024


@dataclass(frozen=True)
class OracleCase:
    expression: str
    context: dict[str, Any]
    expected: str | None = None


@dataclass(frozen=True)
class OracleResult:
    case: OracleCase
    ours: str
    theirs: str
    status: str  # "match" | "mismatch" | "error"

    def to_dict(self) -> dict[str, Any]:
        return {
            "expression": self.case.expression,
            "context": to_jsonable(self.case.context),
            "ours": self.ours,
            "theirs": self.theirs,
            "status": self.status,
        }


def find_oracle(explicit: str | None = None) -> str:
    candidate = explicit or os.environ.get("FEEL_DSNTK")
    if candidate:
        path = Path(candidate)
        if path.is_file():
            return str(path)
        raise OracleError(f"oracle not found at '{candidate}'")
    found = shutil.which("dsntk")
    if found:
        return found
    raise OracleError("dsntk not found; pass --oracle <path> or set FEEL_DSNTK")


def load_cases(path: str | Path) -> list[OracleCase]:
    target = Path(path)
    try:
        size = target.stat().st_size
    except OSError as error:
        raise OracleError(f"cannot read cases file: {error}") from error
    if size > MAX_CASES_BYTES:
        raise OracleError(f"cases file is larger than {MAX_CASES_BYTES} bytes")
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except OSError as error:
        raise OracleError(f"cannot read cases file: {error}") from error
    except json.JSONDecodeError as error:
        raise OracleError(f"cases file is not valid JSON: {error}") from error
    except ValueError as error:  # e.g. an integer beyond CPython's int-string limit
        raise OracleError(f"cases file is not valid JSON: {error}") from error
    if isinstance(data, dict) and "cases" in data:
        data = data["cases"]
    if not isinstance(data, list) or not data:
        raise OracleError("cases file must contain a non-empty list")
    if len(data) > MAX_EXPRESSIONS:
        raise OracleError(f"cases file has more than {MAX_EXPRESSIONS} expressions")
    cases: list[OracleCase] = []
    for index, item in enumerate(data):
        if not isinstance(item, dict) or not isinstance(item.get("expression"), str):
            raise OracleError(f"case {index} needs a string 'expression'")
        context = item.get("context", {})
        if not isinstance(context, dict):
            raise OracleError(f"case {index} has a non-object 'context'")
        expected = item.get("expected")
        if expected is not None and not isinstance(expected, str):
            raise OracleError(f"case {index} has a non-string 'expected'")
        cases.append(OracleCase(item["expression"], context, expected))
    return cases


def evaluate_cases(cases: list[OracleCase], oracle_path: str) -> list[OracleResult]:
    results: list[OracleResult] = []
    with tempfile.TemporaryDirectory(prefix="feel-oracle-") as directory:
        work = Path(directory)
        for index, case in enumerate(cases):
            try:
                ours = render(Evaluator(case.context).evaluate(parse(case.expression)))
            except Exception as error:
                ours = f"<error: {error}>"
            theirs = _run_oracle(oracle_path, work, index, case)
            if ours.startswith("<error:"):
                status = "error"
            elif _normalize(ours) == _normalize(theirs):
                status = "match"
            else:
                status = "mismatch"
            results.append(OracleResult(case, ours, theirs, status))
    return results


def _run_oracle(oracle_path: str, work: Path, index: int, case: OracleCase) -> str:
    input_file = work / f"in-{index}.json"
    feel_file = work / f"case-{index}.feel"
    input_file.write_text(json.dumps(case.context), encoding="utf-8")
    feel_file.write_text(case.expression + "\n", encoding="utf-8")
    try:
        completed = subprocess.run(  # noqa: S603 - fixed argv, no shell, validated path
            [oracle_path, "efe", str(input_file), str(feel_file)],
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return f"<oracle error: {error}>"
    output = completed.stdout.strip() or completed.stderr.strip()
    return output.replace("\n", " ")


def _normalize(text: str) -> str:
    collapsed = " ".join(text.strip().split())
    if collapsed.startswith("null(") and collapsed.endswith(")"):
        return "null"
    return collapsed
