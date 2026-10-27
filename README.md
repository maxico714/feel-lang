# feel-lang

Pure-Python, MIT-licensed **FEEL** expression evaluator and decision-table engine for DMN-style business
rules. No native wheels, no compilers, no GPL, no runtime dependencies.

```console
$ pip install feel-lang
$ python -c "import feel_lang; print(feel_lang.evaluate('if age >= 18 then \"adult\" else \"minor\"', {'age': 20}))"
adult
```

FEEL is the expression language of DMN (Decision Model and Notation), used for decision tables in
insurance, banking and compliance. This package implements the decision-table-focused subset of FEEL with
exact decimal arithmetic, three-valued logic and a first-match decision-table evaluator, in plain Python
3.10+.

**Status:** v0.1.0, alpha. The subset is frozen in [docs/FEEL_SUBSET.md](docs/FEEL_SUBSET.md); results
match the dsntk 0.3.0 oracle on the 73-case differential corpus in `fixtures/oracle/`. Not yet published
to PyPI.

## Why this package

| Option | Why not |
|---|---|
| `zen-engine` | Native Rust wheels; platform pain on Windows ARM and locked-down fleets |
| `pySFeel` | GPL — licence contamination for commercial products |
| `dsntk` | Excellent, but a separate Rust/Java binary, not importable as Python |
| `feelin` | TypeScript |

`feel-lang` is the Python-native, permissively licensed, pure-Python path. It does less than a full DMN
engine; see the non-goals.

## Install

```console
$ pip install feel-lang          # once published; until then install from a checkout:
$ git clone https://github.com/maxico714/feel-lang && cd feel-lang
$ pip install .
```

Requires Python 3.10 or newer. No compiler, no build step, no wheels beyond `py3-none-any`.

## Usage

```python
import feel_lang

feel_lang.evaluate("1 + 2 * 3")  # 7
feel_lang.evaluate("0.1 + 0.2")  # 0.3 (exact decimal, not 0.30000000000000004)
feel_lang.evaluate("5 in [1..10]")  # True
feel_lang.evaluate('if score > 0.8 then "A" else "B"', {"score": 0.9})  # "A"
feel_lang.evaluate('date("2024-01-31") + duration("P1M")')  # datetime.date(2024, 2, 29)
```

Decision tables:

```python
from feel_lang import decision_table

table = {
    "inputs": ["age", "risk"],
    "outputs": ["discount"],
    "rules": [
        {"when": {"age": "[18..25]", "risk": "high"}, "then": {"discount": 0.1}},
        {"when": {"age": "[26..]", "risk": "-"}, "then": {"discount": 0.05}},
    ],
    "default": {"discount": 0.0},
}

decision_table(table, {"age": 20, "risk": "high"})  # {"discount": 0.1}
```

Cell text is a FEEL unary test with `?` bound to the input (`">= 65"`, `"? in [1..5]"`), a range
(`"[18..25]"`), a list (any-of), `-` (always), or a plain string. Outputs starting with `=` are FEEL
expressions over the inputs (`"= amount * 0.05"`).

## CLI

```console
$ feel-lang eval 'age >= 18 and risk = "low"' --context ctx.json
true

$ feel-lang eval 'substring("hello", 2, 3)' --json
{"expression": "substring(\"hello\", 2, 3)", "result": "ell"}

$ feel-lang parse '1 + 2 * 3' --json
{"type": "Binary", "operator": "+", ...}

$ feel-lang table fixtures/tables/discount.json --inputs inputs.json --json
{"band": "young-high", "discount": 0.1}

$ feel-lang doctor
feel-lang 0.1.0
python: 3.12.10 (win32)
oracle: not found (optional; needed only for diff-oracle)
...
OK
```

Exit codes: `0` ok, `1` evaluation error or oracle mismatch, `2` parse error, `3` oracle unavailable,
`4` usage/config error.

## Differential oracle

`feel-lang diff-oracle` compares results with a **dsntk** executable you provide (Apache-2.0, not bundled
and not a dependency):

```console
$ feel-lang diff-oracle --expressions fixtures/oracle/expressions.json --oracle /path/to/dsntk
...
73/73 match
```

`--oracle` or `FEEL_DSNTK` must point at the binary; otherwise the command exits `3`. Each case runs with
a fixed argument list, no shell, and a 20-second timeout. Cases that intentionally diverge are documented
in [docs/FEEL_SUBSET.md](docs/FEEL_SUBSET.md), not silently ignored.

## What is supported (v0.1)

Literals (numbers, strings, booleans, null, dates, times, date-times, durations), variables and context
access, arithmetic, comparison, Kleene `and`/`or`/`not`, `in`, `between`, ranges, lists with 1-based
indexing, contexts, `if-then-else`, 16 built-in functions, and first-match decision tables. Details,
limits and non-goals: [docs/FEEL_SUBSET.md](docs/FEEL_SUBSET.md).

## Honest limitations

- **Subset, not the whole language.** No `instance of`, `for … return`, expression filters,
  `starts with`/`ends with`/`matches`, or non-`first` hit policies. Unsupported syntax raises
  `E_PARSE` rather than guessing.
- **Temporal algebra is partial.** Dates/times/durations add and compare; time zones and the full DMN
  temporal function set are out of scope.
- **Type errors are `null`.** FEEL treats invalid operations as null; only unknown functions and wrong
  arity raise. A silent `null` can hide a modelling mistake, so check results in tests.
- **Oracle coverage is a snapshot.** The 73-case corpus was checked against dsntk v0.3.0 on 2026-10-26;
  the DMN TCK is not part of v0.1.
- **One platform was tested directly.** Development verification ran on Windows 10 with Python 3.12; CI
  covers Ubuntu and Windows on 3.10, 3.12 and 3.13.
- **Not published to PyPI yet.**

## Development

```console
$ pip install -e ".[dev]"
$ ruff check . && ruff format --check .
$ mypy
$ pytest
```

220 tests cover the lexer, parser, evaluator, values, decision tables, fixtures, CLI, adversarial input
and licence hygiene. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Licence

MIT — see [LICENSE](LICENSE) and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
