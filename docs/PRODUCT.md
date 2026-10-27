# PRODUCT — feel-lang

Status: v0.1.0 built, tested and verified (2026-10-26). MIT, alpha.

## Problem

DMN (Decision Model and Notation) is the standard for executable business rules in insurance, banking and
compliance, and FEEL is its expression language. Python teams integrating DMN hit a wall: `zen-engine`
ships native Rust wheels (platform pain on Windows ARM and locked-down fleets), `pySFeel` is GPL
(licence contamination for commercial products), `dsntk` is an external binary and `feelin` is
TypeScript. No Python option was both **pure-Python (zero native wheels)** and **permissively licensed**
with decision-table support.

## Target users (personas)

1. **Insurance/banking rules engineer (primary):** runs decision tables in a Python service. Job: evaluate
   FEEL without native-wheel pain or GPL contamination.
2. **Platform/infra engineer (secondary):** corporate Windows/ARM fleet that cannot install compilers.
   Job: `pip install feel-lang` and have it work anywhere Python runs.
3. **DMN consultant (tertiary):** prototypes decision logic. Job: a lightweight evaluator without a
   Java/Rust toolchain.

## Jobs-to-be-done

- "Evaluate this FEEL expression in Python with no native wheels."
- "Run this decision table (inputs → outputs) without a Java/Rust engine."
- "Keep our commercial product MIT/Apache-clean."

## Value proposition

Pure-Python, MIT-licensed FEEL evaluator and decision tables — installable anywhere Python runs, no
compilers, no wheels, no GPL.

## Non-goals

- Not a full DMN engine (no BPMN, no decision-service orchestration).
- Not the DMN TCK harness in v0.1 (separate milestone).
- Not a replacement for heavy production engines; this is the lightweight Python path.
- No GUI editor; CLI and Python API only.

## MVP scope (v0.1, delivered)

**Delivered:**

- Parser and evaluator for the decision-table-focused FEEL subset: literals (number, string, boolean,
  null, date, time, date-time, duration), variables and context access, arithmetic, comparison, Kleene
  `and`/`or`/`not`, `in`, `between`, ranges, lists with 1-based indexing, contexts, `if-then-else`,
  16 built-in functions.
- Decision tables: first-match hit policy, unary-test cells (`?`, comparison prefixes, ranges, lists,
  `-`, literal text), computed outputs (`= expr`), default row, fail-closed schema validation.
- Python API: `evaluate`, `parse`, `decision_table`, `Evaluator`, typed errors with stable codes.
- CLI: `eval`, `parse`, `table`, `diff-oracle`, `doctor`; exit codes 0/1/2/3/4.
- Differential oracle against dsntk 0.3.0 over a 73-case corpus: **73/73 match**.
- Zero runtime dependencies; pure-Python wheel.

**Deferred from the scaffold:** `startsWith`/`endsWith` string functions (dsntk 0.3.0 does not parse
them either; keeping the subset oracle-compatible), DMN XML import, and the TCK harness.

## Success criteria

| Criterion | Measure | Proof |
|---|---|---|
| L1 units | Parser + evaluator unit tests (≥50 expressions) | 220 tests pass; lexer/parser/evaluator/values/tables suites |
| L2 integration | Decision-table fixtures (inputs → output) green | `tests/integration/test_fixtures.py` |
| L3 differential | ≥20 expressions compared with an oracle | 73/73 match against dsntk v0.3.0 |
| L4 clean env | Fresh copy + `pip install .` + tests green | recorded in `BUILD_CHECKLIST.md` |
| L5 adversarial | Malformed input, division by zero, huge lists, deep nesting | `tests/adversarial/` |
| GPL hygiene | No GPL-derived fixtures/tests/code | `tests/security/test_license_hygiene.py` passes |
| Honesty | Pitch is "no native wheels and MIT", not "FEEL unavailable" | README and this document |

## Honest comparison

- **zen-engine:** heavier production engine with native wheels and more features; this package is lighter,
  pure Python and permissive. If you need full DMN coverage today, use zen-engine.
- **pySFeel:** GPL; this package is MIT.
- **dsntk:** excellent oracle and runtime, but a separate binary; this package is importable Python. It is
  credited in `THIRD_PARTY_NOTICES.md` and used only as an optional differential oracle.
- **feelin:** TypeScript; cross-language differential is a v0.5 idea.

## Naming and licence

- `feel-lang` — PyPI returned 404 on 2026-10-26 (name available). Descriptive, no DMN or vendor marks.
- MIT. No runtime dependencies; dsntk is neither bundled nor required.

## Risk register

| Risk | Severity | Mitigation |
|---|---|---|
| FEEL complexity explodes | High | frozen v0.1 subset; decision-table focus; TCK is a separate milestone |
| GPL contamination via fixtures | High | fixtures written for this project, licence test in CI, dsntk (Apache-2.0) used only as a subprocess |
| Oracle gaps | Medium | documented divergences; diverging cases kept out of the matching corpus and explained in FEEL_SUBSET.md |
| Users expect the full language | Medium | README and FEEL_SUBSET.md state the boundary; unsupported syntax raises instead of guessing |
| Silent nulls hide mistakes | Medium | documented "type errors are null" policy; tests assert null deliberately |
