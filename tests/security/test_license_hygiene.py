"""GPL hygiene and dependency checks for the shipped tree."""

from __future__ import annotations

import ast
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SRC = REPO / "src" / "feel_lang"
FIXTURES = REPO / "fixtures"
TESTS = REPO / "tests"

GPL_MARKERS = (
    "GNU General Public License",
    "GNU GENERAL PUBLIC LICENSE",
    "GPL-2.0",
    "GPL-3.0",
    "AGPL",
    "pySFeel",
)

STDLIB_ONLY = {
    "__future__",
    "argparse",
    "ast",
    "collections",
    "contextlib",
    "dataclasses",
    "datetime",
    "decimal",
    "json",
    "math",
    "os",
    "pathlib",
    "re",
    "shutil",
    "subprocess",
    "sys",
    "tempfile",
    "typing",
}


def iter_text_files(root: Path) -> list[Path]:
    return sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and path.suffix in {".py", ".json", ".md", ".toml", ".txt", ".yml", ".yaml", ".cff", ".jsonl"}
    )


def test_no_gpl_markers_in_fixtures_or_tests() -> None:
    offenders: list[str] = []
    for path in iter_text_files(FIXTURES) + iter_text_files(TESTS):
        if path == Path(__file__).resolve():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for marker in GPL_MARKERS:
            if marker in text:
                offenders.append(f"{path.relative_to(REPO)}: {marker}")
    assert offenders == []


def test_no_gpl_markers_in_source() -> None:
    offenders: list[str] = []
    for path in iter_text_files(SRC):
        text = path.read_text(encoding="utf-8", errors="replace")
        for marker in GPL_MARKERS:
            if marker in text:
                offenders.append(f"{path.relative_to(REPO)}: {marker}")
    assert offenders == []


def test_core_imports_only_the_standard_library_and_itself() -> None:
    offenders: list[str] = []
    for path in SRC.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root = alias.name.split(".")[0]
                    if root not in STDLIB_ONLY:
                        offenders.append(f"{path.name}: import {alias.name}")
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                root = node.module.split(".")[0]
                if root not in STDLIB_ONLY and root != "feel_lang":
                    offenders.append(f"{path.name}: from {node.module}")
    assert offenders == []


def test_third_party_notices_name_the_oracle_and_licence() -> None:
    notices = REPO / "THIRD_PARTY_NOTICES.md"
    text = notices.read_text(encoding="utf-8")
    assert "dsntk" in text
    assert "Apache-2.0" in text
    assert "MIT" in text


def test_pyproject_declares_the_mit_licence_and_no_runtime_dependencies() -> None:
    text = (REPO / "pyproject.toml").read_text(encoding="utf-8")
    assert 'license = { text = "MIT" }' in text
    data = json.loads((REPO / "fixtures" / "fixtures.json").read_text(encoding="utf-8"))
    assert "dependencies" not in data  # fixtures are plain data, no hidden imports
    assert "dependencies" not in text.split("[project.optional-dependencies]")[0]
