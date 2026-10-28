from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from feel_lang.cli import EXIT_EVAL, EXIT_OK, EXIT_ORACLE, EXIT_PARSE, EXIT_USAGE, main

REPO = Path(__file__).resolve().parents[2]
FIXTURES = REPO / "fixtures"


def run(capsys: pytest.CaptureFixture[str], *argv: str) -> tuple[int, str, str]:
    code = main(list(argv))
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def test_eval_prints_the_result(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, err = run(capsys, "eval", "1 + 2 * 3")
    assert code == EXIT_OK and out.strip() == "7" and err == ""


def test_eval_with_context(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    context = tmp_path / "ctx.json"
    context.write_text(json.dumps({"age": 20}), encoding="utf-8")
    code, out, _ = run(capsys, "eval", "age >= 18", "--context", str(context))
    assert code == EXIT_OK and out.strip() == "true"


def test_eval_json_output(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = run(capsys, "eval", 'substring("hello", 2, 3)', "--json")
    payload = json.loads(out)
    assert code == EXIT_OK and payload == {"expression": 'substring("hello", 2, 3)', "result": "ell"}


def test_eval_parse_error_exit_code(capsys: pytest.CaptureFixture[str]) -> None:
    code, _, err = run(capsys, "eval", "1 +")
    assert code == EXIT_PARSE and "parse error" in err


def test_eval_runtime_error_exit_code(capsys: pytest.CaptureFixture[str]) -> None:
    code, _, err = run(capsys, "eval", "mystery(1)")
    assert code == EXIT_EVAL and "unknown function" in err


def test_eval_bad_context_is_a_config_error(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    context = tmp_path / "ctx.json"
    context.write_text("[1, 2]", encoding="utf-8")
    code, _, err = run(capsys, "eval", "1", "--context", str(context))
    assert code == EXIT_USAGE and "context must be a JSON object" in err


def test_eval_missing_context_file(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    code, _, err = run(capsys, "eval", "1", "--context", str(tmp_path / "missing.json"))
    assert code == EXIT_USAGE and "cannot read context file" in err


def test_eval_oversized_context_file(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    context = tmp_path / "ctx.json"
    context.write_text("{}", encoding="utf-8")
    context.write_text("{" + " " * (5 * 1024 * 1024) + "}", encoding="utf-8")
    code, _, err = run(capsys, "eval", "1", "--context", str(context))
    assert code == EXIT_USAGE and "larger than" in err


def test_eval_oversized_integer_is_a_config_error(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    context = tmp_path / "ctx.json"
    context.write_text('{"x": ' + "9" * 5_000 + "}", encoding="utf-8")
    code, _, err = run(capsys, "eval", "x", "--context", str(context))
    assert code == EXIT_USAGE and "not valid JSON" in err


def test_parse_prints_ast(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = run(capsys, "parse", "1 + 2", "--json")
    payload = json.loads(out)
    assert code == EXIT_OK and payload["type"] == "Binary" and payload["operator"] == "+"


def test_parse_dry_run(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = run(capsys, "parse", "1 + 2", "--dry-run")
    assert code == EXIT_OK and '"type": "Binary"' in out


def test_table_fixture(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    inputs = tmp_path / "in.json"
    inputs.write_text(json.dumps({"age": 20, "risk": "high"}), encoding="utf-8")
    code, out, _ = run(capsys, "table", str(FIXTURES / "tables" / "discount.json"), "--inputs", str(inputs), "--json")
    assert code == EXIT_OK
    assert json.loads(out) == {"discount": 0.1, "band": "young-high"}


def test_table_no_match(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    table = tmp_path / "table.json"
    table.write_text(
        json.dumps({"inputs": ["x"], "outputs": ["y"], "rules": [{"when": {"x": "1"}, "then": {"y": 2}}]}),
        encoding="utf-8",
    )
    inputs = tmp_path / "in.json"
    inputs.write_text(json.dumps({"x": 5}), encoding="utf-8")
    code, out, _ = run(capsys, "table", str(table), "--inputs", str(inputs))
    assert code == EXIT_OK and "no match" in out


def test_table_invalid_schema(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    table = tmp_path / "table.json"
    table.write_text("{}", encoding="utf-8")
    inputs = tmp_path / "in.json"
    inputs.write_text("{}", encoding="utf-8")
    code, _, err = run(capsys, "table", str(table), "--inputs", str(inputs))
    assert code == EXIT_USAGE and "config error" in err


def test_doctor(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = run(capsys, "doctor")
    assert code == EXIT_OK
    assert "feel-lang 0.1.0" in out and "OK" in out


def test_doctor_json(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = run(capsys, "doctor", "--json")
    payload = json.loads(out)
    assert code == EXIT_OK and payload["version"] == "0.1.0" and "python" in payload


def test_usage_error_exit_code(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as caught:
        main(["eval"])
    assert caught.value.code == EXIT_USAGE


def test_unknown_command_exit_code(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as caught:
        main(["frobnicate"])
    assert caught.value.code == EXIT_USAGE


def test_oracle_missing(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("FEEL_DSNTK", raising=False)
    monkeypatch.setenv("PATH", str(tmp_path))
    cases = tmp_path / "cases.json"
    cases.write_text(json.dumps([{"expression": "1 + 1", "context": {}}]), encoding="utf-8")
    code, _, err = run(capsys, "diff-oracle", "--expressions", str(cases))
    assert code == EXIT_ORACLE and "dsntk not found" in err


def test_unicode_output_does_not_crash_on_lone_surrogates(tmp_path: Path) -> None:
    import os

    context = tmp_path / "ctx.json"
    context.write_text('{"x": "\\ud800"}', encoding="ascii")
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO / "src")
    env["PYTHONIOENCODING"] = "utf-8"
    result = subprocess.run(
        [sys.executable, "-m", "feel_lang.cli", "eval", "x", "--context", str(context)],
        cwd=REPO,
        env=env,
        capture_output=True,
        text=False,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0
    assert b"\\ud800" in result.stdout


def test_oracle_cases_oversized_file_is_an_error(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    cases = tmp_path / "cases.json"
    cases.write_text("[" + " " * (5 * 1024 * 1024) + "]", encoding="utf-8")
    code, _, err = run(capsys, "diff-oracle", "--expressions", str(cases))
    assert code == EXIT_ORACLE and "larger than" in err


def test_oracle_cases_oversized_integer_is_an_error(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    cases = tmp_path / "cases.json"
    cases.write_text('[{"expression": "x", "context": {"x": ' + "9" * 5_000 + "}}]", encoding="utf-8")
    code, _, err = run(capsys, "diff-oracle", "--expressions", str(cases))
    assert code == EXIT_ORACLE and "not valid JSON" in err


def test_console_script_entry_point() -> None:
    import os

    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO / "src")
    result = subprocess.run(
        [sys.executable, "-m", "feel_lang.cli", "--version"],
        cwd=REPO,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0
    assert result.stdout.strip() == "feel-lang 0.1.0"
