# ROADMAP — feel-lang

Status: v0.1.0 built and verified (2026-10-26). SemVer; Keep a Changelog. GPL hygiene is permanent.
The DMN TCK harness is a separate milestone and not part of v0.1.

## v0.1 — Walking skeleton (done)

- [x] Lexer and parser for the decision-table-focused FEEL subset, with hard input caps.
- [x] Evaluator: literals, arithmetic, comparison, Kleene logic, `in`/`between`, ranges, list functions,
      `if-then-else`, contexts, temporals, 16 built-ins.
- [x] Decision-table evaluation with a first-match hit policy, unary-test cells and computed outputs.
- [x] Python API (`evaluate`, `parse`, `decision_table`, `Evaluator`) and CLI (`eval`, `parse`, `table`,
      `diff-oracle`, `doctor`).
- [x] Differential fixtures: 73/73 match against dsntk v0.3.0; no GPL-derived fixtures.
- [x] 220 tests, adversarial suite, licence-hygiene test, strict mypy, ruff, CI matrix.

**Riskiest assumption, now retired:** three-valued logic and range boundary semantics. Ten edge cases
were probed in dsntk before coding (`docs/EVIDENCE.md`), then the full 73-case corpus was adopted as the
regression oracle. One divergence (`null = 1`) is documented instead of copied.

## v0.5 — Core value

- [ ] Broader function coverage: `sort`, `flatten`, `distinct values`, `replace`, `upper case`,
      `lower case`, `string length`, date/time component extractors.
- [ ] Expression-level filters (`list[item > 2]`) and `for … return`.
- [ ] DMN XML import for decision tables (subset), with a fail-closed parser.
- [ ] Expression cache keyed by source text; benchmark suite against the stated budgets.
- [ ] Cross-language differential against `feelin` (TypeScript) documented with gaps.
- [ ] `starts with` / `ends with` / `matches` once (and if) the oracle supports them.

## v1.0 — Production-ready

- [ ] DMN TCK harness (milestone N), run as a separate report with honest pass rates.
- [ ] Type checks for expressions; optional REPL.
- [ ] SBOM and signed releases; registry publish via trusted publishing (G3-gated).
- [ ] Broader platform verification (macOS, Linux, ARM).

## Post-1.0 (parked)

Full DMN engine, BPMN, GUI editor, every FEEL built-in, non-`first` hit policies.

## Maintenance cadence

- New functions and rule data are minor releases.
- Changes to three-valued logic, comparison or range semantics are major releases.
- The dsntk oracle version is recorded in `docs/EVIDENCE.md`; re-run the corpus when it changes.
