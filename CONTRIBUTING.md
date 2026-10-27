# Contributing

Thanks for helping. The most useful contributions are conformance cases, clearer errors and missing
subset functions — with tests.

## Setup (under five minutes)

```console
$ git clone https://github.com/maxico714/feel-lang
$ cd feel-lang
$ python -m venv .venv
$ .venv/Scripts/activate        # Windows; use source .venv/bin/activate elsewhere
$ pip install -e ".[dev]"
$ ruff check . && ruff format --check . && mypy && pytest
```

Requires Python 3.10+. The package has no runtime dependencies; the dev extra adds pytest, ruff, mypy,
build and twine.

## Guidelines

- **Every behaviour change needs a test that fails without it.** For operator or range changes, include a
  mutation check in the pull request notes: break the condition, show the failing test, restore.
- **Keep the subset honest.** If you add a construct, update `docs/FEEL_SUBSET.md`, the README and the
  changelog in the same pull request. If dsntk disagrees, document the divergence rather than hiding it.
- **No new runtime dependencies.** The stdlib-only test in `tests/security/` parses every import.
- **No GPL-derived material.** Do not copy tests, fixtures or code from `pySFeel` or other GPL projects.
  Oracle comparisons must use a locally supplied dsntk binary, never vendored output files.
- **Bounded input.** New syntax must respect the existing caps (length, tokens, depth, items) or add a
  new explicit one.
- **Formatting and types are enforced.** Run `ruff format` before committing; mypy is strict.

## Adding a conformance case

1. Put the expression and context in `fixtures/oracle/expressions.json` (the oracle corpus) and, when the
   expected value is part of the documented contract, in `fixtures/fixtures.json`.
2. Run `python -m pytest tests/integration` and, if you have dsntk, `feel-lang diff-oracle --expressions
   fixtures/oracle/expressions.json --oracle <path>`.
3. If the oracle disagrees and this implementation follows the DMN specification instead, add the case to
   the divergence list in `docs/FEEL_SUBSET.md`.

## Commits and pull requests

Conventional Commits, one logical change per pull request, CI green. Describe the failure, the fix and
the command that proves it.
