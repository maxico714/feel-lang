# BUILD CHECKLIST — feel-lang

Status: v0.1.0 built and verified 2026-10-26 (Windows 10 26200, Python 3.12.10, dsntk 0.3.0).
Each gate lists the command that produced the evidence. Gate 8 (PyPI publish) stays open: G3 is not
approved.

## Gate 0 — Semantic spike

- [x] 64 edge-case expressions evaluated in dsntk before coding (null equality, Kleene logic, division by
      zero, empty lists, open/closed ranges, index bounds, substring bounds, separators, temporals,
      duration kinds, `-2 ** 2`, multi-word names). Findings frozen in
      [docs/FEEL_SUBSET.md](docs/FEEL_SUBSET.md) and [docs/EVIDENCE.md](docs/EVIDENCE.md).
- [x] Divergences documented: `null = 1` follows the DMN rule (false) where dsntk returns null;
      `starts with`/`ends with`/`matches` are out of scope because dsntk 0.3.0 cannot parse them.
- [x] Three-valued logic proved tractable: Kleene tables implemented and covered by tests.

## Gate 1 — L0 static

- [x] `ruff check .` — clean (E, F, I, B, UP, S, C4, SIM, RUF).
- [x] `ruff format --check .` — 27 files formatted.
- [x] `mypy` — strict, 10 source modules, no issues.
- [x] `pytest --collect-only` — 220 tests collected.

## Gate 2 — L1 units

- [x] Lexer: 19 tests (literals, escapes, `@` literals, comments, positions, caps, errors).
- [x] Parser: 31 tests (precedence, associativity, ranges, membership, contexts, multi-word names,
      depth/token caps, clear errors).
- [x] Evaluator: 33 tests (exact decimals, Kleene logic, null propagation, index bounds, functions,
      temporals, durations, render, no code execution).
- [x] Values: 19 tests (Decimal conversions, duration parsing/round-trip, temporal arithmetic).
- [x] Tables: 22 tests (first-match, default, unary cells, computed outputs, schema failures, rule cap).
- [x] Mutation sanity (each killed, then restored):
      range low-inclusivity inverted ⇒ `test_between_and_membership` fails;
      Kleene `and` collapsed ⇒ 2 tests fail;
      0-based indexing ⇒ 3 tests fail.

## Gate 3 — L2 integration (decision tables)

- [x] `fixtures/tables/discount.json` — 5 input/expected cases, including the default row.
- [x] `fixtures/tables/shipping.json` — 4 cases: comparison cells, list cells, computed output, default.
- [x] Fixture-driven expression set (`fixtures/fixtures.json`) — 49 expressions checked through the public
      API.
- [x] Fail-closed schema validation: unknown keys, duplicate inputs, unknown rule inputs, missing outputs,
      non-`first` hit policy, empty rules, >1,000 rules, non-scalar cells.

## Gate 4 — Differential oracle (L3)

- [x] `python -m feel_lang.cli diff-oracle --expressions fixtures/oracle/expressions.json --oracle
      <dsntk>` → **73/73 match** against dsntk v0.3.0 (more than the 20 required).
- [x] Divergences documented in `docs/FEEL_SUBSET.md`; cases that would diverge are not in the matching
      corpus.
- [x] No GPL fixtures: `tests/security/test_license_hygiene.py` scans fixtures/tests/source for GPL
      markers and asserts stdlib-only imports.

## Gate 5 — L5 adversarial

- [x] Malformed expressions report `E_PARSE` with a position; unterminated strings/comments covered.
- [x] Division by zero, `0/0`, type mismatches and null arithmetic → `null` (documented).
- [x] Caps: 20k characters, 5k tokens, depth 100, 10,001-item list rejected, 120-deep nesting rejected.
- [x] Hostile tables: nested dict cells rejected, unknown functions in cells never match, large context
      lists evaluated without materialising copies.
- [x] `__import__("os")` raises `E_EVAL` (no code execution path).

## Gate 6 — GPL hygiene and honesty

- [x] Licence scan test passes; `THIRD_PARTY_NOTICES.md` credits dsntk (Apache-2.0) as an optional
      oracle and states pySFeel is not used.
- [x] Pitch honesty: "no native wheels, MIT" — the README states the subset limits, the null-on-error
      policy and the single-platform development verification.
- [x] No TODO/FIXME in `src/` (`grep -rn "TODO\|FIXME" src` returns nothing).
- [x] Secrets scan: `detect-secrets 1.5.0` over all project files → 0 findings.

## Gate 7 — L4 clean environment (pure-Python proof)

- [x] Fresh copy (no `dist`, `build`, egg-info, caches) → `python -m venv` → `pip install .` (no
      compiler, no native wheel) → `pytest` → **220 passed**.
- [x] README quickstart executed in that venv: `import feel_lang`, `doctor`, `eval` with a date, `table`
      with a fixture.

## Gate 8 — Packaging (G3-gated; not executed)

- [x] `python -m build` → `feel_lang-0.1.0-py3-none-any.whl` (24,939 bytes) and
      `feel_lang-0.1.0.tar.gz` (25,055 bytes); `twine check` PASSED for both.
- [x] PyPI name `feel-lang` returned HTTP 404 on 2026-10-26.
- [ ] Publish to PyPI — **blocked on the G3 approval**; re-check the name and competitors first.

## Definition of done (v0.1)

Gates 0–7 green with the evidence above; Gate 8 prepared but not executed. The DMN TCK harness is
milestone N and explicitly not part of v0.1.
