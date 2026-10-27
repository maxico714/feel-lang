# EVIDENCE — feel-lang

Research judgement (2026-10-12, round-4 verifier + skeptic, ADR-004, ledger row 48), followed by
build-time verification on **2026-10-26**. Claims are dated so older research is not presented as fresh
evidence.

## Gap class: F (exists but incomplete in a specific, nameable way)

- **zen-engine** — native Rust wheels; Windows ARM and locked-down fleet pain.
- **pySFeel** — GPL; licence contamination for commercial products.
- **dsntk** — external Rust binary (v0.3.0); not importable as Python.
- **feelin** — TypeScript.
- No Python option was both pure-Python (zero native wheels) and permissively licensed with
  decision-table support.

**Corrected at build time:** the scaffold described dsntk as Java. The current release is a Rust binary
(`dsntk-v0.3.0-x86_64-pc-windows-msvc.zip`), dual-licensed Apache-2.0/MIT. It works headlessly
(`dsntk efe <input.json> <expr.feel>`), which is what made the differential corpus possible.

## Demand hook: 3/5 (capped per D-006)

DMN adoption in insurance/banking and native-wheel pain on Windows ARM are documented across GitHub
issues; the gap is niche (DMN + Python + pure-Python + permissive), so the hook is deliberately capped.
Hook sentence: "DMN/FEEL in Python means native wheels or GPL — here is the pure-Python, MIT evaluator
with decision tables, installable anywhere."

## Gate 0 semantic spike (2026-10-26)

Before writing the evaluator, 64 FEEL expressions were run through dsntk v0.3.0 to freeze semantics:
null equality, Kleene `and`/`or`/`not`, division by zero, `if` with a null condition, open/closed range
brackets, `in` with test lists, 1-based and negative list indexes, `count(1)`, empty-list aggregates,
`substring` bounds, `number()` with separators, temporal constructors, duration kinds, `@"…"` literals,
`-2 ** 2`, and multi-word names. Findings are recorded in `docs/FEEL_SUBSET.md`; two behaviours worth
calling out:

- dsntk returns `null` for `null = 1`; this package follows the DMN equality rule (`false`) and documents
  the divergence instead of copying an apparent oracle bug.
- dsntk 0.3.0 does not parse `starts with` / `ends with` / `matches`; those were dropped from the v0.1
  subset rather than shipped untested.

## Verification evidence (2026-10-26)

| Check | Command | Result |
|---|---|---|
| Static | `ruff check .`, `ruff format --check .`, `mypy` | clean; strict mypy over 10 modules |
| Tests | `pytest` | **220 passed** |
| Differential (L3) | `feel-lang diff-oracle --expressions fixtures/oracle/expressions.json --oracle dsntk.exe` | **73/73 match** vs dsntk v0.3.0 |
| Mutation 1 | range low-inclusivity inverted | `test_between_and_membership` failed |
| Mutation 2 | Kleene `and` collapsed to two-valued | 2 tests failed (unit + fixture) |
| Mutation 3 | 1-based indexing made 0-based | 3 tests failed (unit, fixture, adversarial) |
| Decision tables | fixtures in `fixtures/tables/` | discount 5/5, shipping 4/4 cases |
| Packaging | `python -m build`, `twine check` | wheel `py3-none-any`, sdist, metadata clean |
| L4 | fresh copy → `pip install .` → `pytest` | green (see `BUILD_CHECKLIST.md`) |
| Secrets | `detect-secrets` over the tree | see checklist record |

## Failure modes encountered while building

| Symptom | Cause | Fix |
|---|---|---|
| `2 ** 3 ** 2` parsed left-associatively | initial power loop | right-associative recursive parse |
| `5 in ]1..10[` ate the closing bracket as an index | postfix `[]` applied while parsing a range bound | a `no_index` guard around range bounds |
| `mean([])` failed to parse | empty list literal unsupported | `[]` handled in `list_or_range` |
| `@"2024-01-01" + @"P1D"` concatenated strings | `@` literals were plain strings | parse `@` literals into temporal values |
| public `evaluate()` returned ISO strings | it reused the JSON conversion | separate `to_public` keeps native temporals |
| table cell `"1"` did not match input `1` | unary cells used truthiness | non-boolean cell results compare by equality |

## Not verified

- The DMN TCK (out of scope for v0.1) and DMN XML import.
- macOS/Linux execution locally (CI covers Ubuntu and Windows, Python 3.10/3.12/3.13).
- Behaviour of dsntk versions other than 0.3.0.
- PyPI publication (G3 gate not approved).

## Score

61/105 (round-4 runner-up, cleanest skeptic verdict). Conditions — v0.1 evaluator-only, TCK as a separate
milestone, pitch honesty, GPL hygiene, differential verification — are met: the subset is frozen and
documented, the TCK is explicitly future work, the README states the boundary, a licence-hygiene test runs
in CI, and 73 cases match the oracle.
