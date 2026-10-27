# TECHNICAL — feel-lang

Status: v0.1.0 built and verified on Windows 10 (26200) with Python 3.12.10; 2026-10-26.
Stack: Python 3.10+ **standard library only** (no C extensions, no runtime dependencies).

## Architecture

```
FEEL text ──► lexer.py ──► parser.py (AST in nodes.py) ──► evaluator.py (values.py)
                                                             │
decision-table JSON ──► tables.py ──────────────────────────┤
                                                             ▼
CLI (cli.py) / public API (__init__.py) / oracle.py (optional dsntk subprocess)
```

| Module | Responsibility |
|---|---|
| `lexer.py` | tokenizer; 20k character and 5k token caps; string/`@"…"` literals; comments |
| `nodes.py` | frozen dataclass AST |
| `parser.py` | recursive descent; precedence, ranges, membership tests, multi-word names; depth 100 |
| `evaluator.py` | Kleene logic, exact decimals, ranges, lists, contexts, 16 built-ins |
| `values.py` | Decimal parsing/formatting, temporals, durations, JSON/public conversions |
| `tables.py` | decision-table schema validation and first-match evaluation |
| `oracle.py` | optional dsntk subprocess runner for differential checks |
| `cli.py` | `eval`, `parse`, `table`, `diff-oracle`, `doctor`; exit codes 0/1/2/3/4 |

## Semantics

Normative: [docs/FEEL_SUBSET.md](docs/FEEL_SUBSET.md). Key choices:

- **Exact decimals.** Every number is a `Decimal` internally; public results are `int` when integral,
  `float` otherwise, and `raw=True` returns the `Decimal`.
- **Three-valued logic.** `and`/`or` follow Kleene tables (see FEEL_SUBSET); `if` takes `then` only for
  `true`.
- **Null on type errors.** Division by zero, mixed-type arithmetic and ordering of incompatible types
  yield `null`, matching FEEL's error-as-null model. Unknown functions (`E_EVAL`) and wrong arity
  (`E_ARG`) raise because they are modelling errors, not data errors.
- **1-based indexing.** `list[1]` is the first element; negative indexes count from the end; index `0`
  and out-of-range are `null`.
- **Durations split by kind.** Years/months and days/time are tracked separately, so `P1M + P1D` is
  invalid and date arithmetic cannot silently mix them. Calendar month shifts clamp the day
  (2024-01-31 + P1M = 2024-02-29).
- **Decision tables.** First-match, all inputs in a rule must match. Cells are equality, any-of lists,
  `-`, range literals, unary tests with `?`, or literal text when the text is not valid FEEL. Outputs
  starting with `=` are FEEL expressions over the inputs.

## Error model

| Code | Class | Raised for |
|---|---|---|
| `E_PARSE` | `ParseError` | invalid syntax, unterminated strings/comments, caps exceeded (with position) |
| `E_EVAL` | `EvalError` | unknown function, unbound `?` |
| `E_ARG` | `ArgumentError` | wrong function arity |
| `E_TYPE` | `TypeError_` | reserved for explicit type assertions (not raised by the current evaluator) |
| `E_CONFIG` | `ConfigError` | invalid decision table or CLI JSON input |
| `E_ORACLE` | `OracleError` | oracle binary missing, unreadable cases file |

Every error carries `.code`, `.message` and, for parse errors, `.position`; `to_dict()` is JSON-ready.

## Limits (bounded input)

20,000 characters per expression, 5,000 tokens, depth 100, 10,000 list items / call arguments, 1,000
table rules, 100 items per cell list, 100 decimal digits, 500 oracle cases × 20 s, 5 MiB CLI JSON files.
No unbounded recursion, allocation or output growth.

## Threat model (STRIDE-lite)

- **Expressions are untrusted data.** No `eval`, no attribute traversal into Python objects, no imports.
  `__import__("os")` is just an unknown function and raises `E_EVAL`; a test pins this.
- **Resource exhaustion.** Every parser and table structure has a hard cap; the lexer rejects oversized
  input before parsing; recursion depth is capped.
- **Decision tables are untrusted data.** Schema is fail-closed: unknown keys, duplicate inputs, unknown
  rule inputs, missing outputs and non-scalar cells are rejected with `E_CONFIG`.
- **External oracle.** Optional, user-supplied executable; fixed argument list, no shell, timeout,
  temporary directory, no network. Not bundled; treated as an untrusted black box whose output is only
  compared as text.
- **Privacy.** No telemetry; no network calls in the library or CLI (the oracle is a local subprocess).
- **Supply chain.** Zero runtime dependencies; a test parses every import and asserts it is stdlib-only.

## Performance

The v0.1 budget is "1,000 simple expressions < 1 s" and "100 rules × 10 inputs < 100 ms". Measured on the
development host (Python 3.12): the 220-test suite, including evaluation of thousands of expressions and
the 73-case fixture set, runs in ~3 s; parsing is linear in tokens with fixed caps. No caching yet (a v0.5
item); the AST is cheap to re-parse at decision-table scale.

## Testing strategy

| Level | Evidence |
|---|---|
| L0 | `ruff check`, `ruff format --check`, strict `mypy` |
| L1 | 220 tests across unit suites (lexer 19, parser 31, evaluator 33, values 19, tables 22) |
| L2 | Fixture-driven expressions and decision tables (`tests/integration/test_fixtures.py`) |
| L3 | `diff-oracle` against dsntk v0.3.0: 73/73 match |
| L4 | Fresh copy → `pip install .` → full test run (recorded in `BUILD_CHECKLIST.md`) |
| L5 | Adversarial suite: caps, deep nesting, nulls, huge lists, hostile tables, zero-width names |

Mutation checks (each killed its intended test, then restored): inverted range inclusivity, collapsed
three-valued `and`, zero-based list indexing.

## Packaging

Pure-Python wheel (`py3-none-any`) and sdist via `python -m build`; `twine check` clean. PyPI name
`feel-lang` returned 404 on 2026-10-26. Publishing is G3-gated and not executed.

## Deviations from the scaffold

| Scaffold | Built | Why |
|---|---|---|
| YAML/JSON everywhere | JSON only | no dependency; decision tables are submitted as JSON |
| `startsWith`/`endsWith` helpers | dropped | dsntk 0.3.0 cannot parse them; the subset stays oracle-compatible |
| dsntk described as Java | dsntk is a Rust binary (v0.3.0) | verified release assets; used as an optional subprocess |
| `--dry-run` on eval | `parse --dry-run` | parsing is the side-effect-free mode; `eval` has no side effects |
| `diff-oracle` exit 3 for gaps | 3 only when the oracle is unavailable; mismatches exit 1 | missing tooling and real mismatches are different failures |
