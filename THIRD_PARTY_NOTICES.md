# Third-party notices

## Runtime

`feel-lang` has **no runtime dependencies**. The package imports only the Python standard library
(`argparse`, `dataclasses`, `datetime`, `decimal`, `json`, `os`, `pathlib`, `re`, `shutil`,
`subprocess`, `sys`, `tempfile`, `typing`). A test enforces this.

## Development

| Package | Version range | Licence | Purpose |
|---|---|---|---|
| `pytest` | >= 8.3 | MIT | Test runner |
| `ruff` | >= 0.9 | MIT | Linter and formatter |
| `mypy` | >= 1.14 | MIT | Static type checking |
| `build` | >= 1.2 | MIT | Wheel and sdist builds |
| `twine` | >= 6.1 | Apache-2.0 | Package metadata checks |

## Optional external oracle (not bundled, not a dependency)

- **dsntk** — DecisionToolkit, <https://github.com/DecisionToolkit/dsntk>, Apache-2.0 (with an MIT
  component noted upstream). The `diff-oracle` command runs a dsntk executable **you provide** to compare
  FEEL results. Version used for the recorded differential runs: `v0.3.0` (Windows x86-64 release asset).
  No dsntk code, data or fixtures are copied into this repository: its role is a black-box subprocess that
  receives a JSON context file and a `.feel` file and prints a result.

## Explicitly not used

- `pySFeel` (GPL) — no code, tests or fixtures are derived from it.
- `zen-engine`, `feelin` — comparison targets only; no code or fixtures copied.

Fixtures were written for this project from the DMN FEEL semantics and checked against the oracle; the
per-expression results are recorded in `fixtures/oracle/expressions.json` and the test suite.
