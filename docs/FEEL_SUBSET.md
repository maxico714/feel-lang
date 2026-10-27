# FEEL subset — v0.1 (normative)

This document is the contract for `feel-lang` v0.1. Everything here is covered by tests; anything not
listed is out of scope. Semantics were checked against **dsntk v0.3.0** where the two overlap — the
differential corpus in `fixtures/oracle/expressions.json` matches 73/73 cases.

## Grammar (informal)

```
expression  := "if" expression "then" expression "else" expression | or
or          := and ("or" and)*
and         := comparison ("and" comparison)*
comparison  := additive (("="|"!="|"<"|"<="|">"|">=") additive)?
             | additive "between" additive "and" additive
             | additive "in" tests
tests       := "(" test ("," test)* ")" | test
additive    := multiplicative (("+"|"-") multiplicative)*
multiplicative := power (("*"|"/") power)*
power       := unary ("**" power)?
unary       := ("-"|"+") unary | postfix
postfix     := primary (("[" expression "]") | ("." name))*
primary     := number | string | boolean | "null" | not-call | "?" 
             | "(" expression ")"
             | "[" list-or-range
             | "]" range
             | "{" context "}"
             | name-or-call
name        := NAME (NAME)*            # multi-word names join with a single space
```

## Values

| FEEL | Python (public API) | Notes |
|---|---|---|
| number | `int` / `float` | exact `Decimal` internally; `evaluate(..., raw=True)` returns `Decimal` |
| string | `str` | double quotes; escapes `\" \\ \n \t \r \uXXXX` |
| boolean | `bool` | |
| null | `None` | |
| date | `datetime.date` | `date("2024-02-29")`, `date(2024, 2, 29)`, `@"2024-02-29"` |
| time | `datetime.time` | `time("13:45:30")`, `time(13, 45, 30)`, `@"13:45:30"` |
| date and time | `datetime.datetime` | `date and time("…")`, `date and time(date, time)`, `@"…"` |
| duration | `feel_lang.Duration` | years/months and days/time are tracked separately |
| list | `list` | 1-based indexing, negative indexes count from the end |
| context | `dict` | literal `{a: 1}` and access `x.y` |
| range | internal `RangeValue` | `[1..10]`, `]1..10[`, `[61..]`, `(1..10)` inside `in` |

## Operators and precedence

`if … then … else …` < `or` < `and` < comparison/`between`/`in` < `+ -` < `* /` < `**` < unary `-` <
postfix `.`/`[]`.

- `**` is right-associative; unary minus binds tighter (`-2 ** 2` = 4, matching dsntk).
- `<`, `<=`, `>`, `>=` compare numbers, strings and same-type temporals/durations; anything else is
  `null`.
- `between` is inclusive on both ends.
- `in` accepts a range, a list literal, a parenthesised list of tests, or a parenthesised range.
  Bracket meaning: `[`/`]` include the bound, `]`/`[` exclude it. `(1..10)` is the exclusive range
  `]1..10[`.

## Three-valued logic

`and`/`or` follow Kleene logic and are evaluated left to right with short-circuiting where the result is
already determined:

| `a` | `b` | `a and b` | `a or b` |
|---|---|---|---|
| true | true | true | true |
| true | false | false | true |
| false | _ | false | _ |
| null | true | null | true |
| null | false | false | null |
| null | null | null | null |

`not(x)` is `null` for `null` and non-boolean values. `if` takes the `then` branch only when the condition
is exactly `true`; `false` and `null` take the `else` branch.

## Equality and null

- `null = null` → `true`; `x = null` → `true` iff `x` is null, otherwise `false`.
- `!=` is the negation of `=` for every pair, including nulls.
- Numbers compare by value (`1 = 1.0`), lists element-wise, contexts by keys and values, temporals by
  instant/date, ranges structurally.

**Divergence from dsntk 0.3.0:** dsntk returns `null` for `null = 1` and `null != 1`. This
implementation follows the DMN specification's equality rule (false / true respectively) and documents
the difference instead of copying it.

## Arithmetic and null propagation

- Numeric `+ - * / **` on numbers; `+` also concatenates two strings and adds a duration to a temporal.
- Division by zero and `0 ** negative` return `null`; type mismatches return `null`.
- Any arithmetic with a `null` operand returns `null` (except duration + temporal, see below).
- Dates/times: `date + duration`, `time + duration`, `date and time + duration`, `duration + temporal`.
  A months-only duration shifts calendar months (2024-01-31 + P1M = 2024-02-29); a seconds-only duration
  shifts by elapsed time. A duration with both months and seconds cannot be added to a temporal (`null`).
  Months cannot be added to a time (`null`); adding hours that cross midnight to a time (`null`).

## Functions (16)

| Name | Arity | Behaviour |
|---|---|---|
| `count(x)` | 1 | list length; `1` for a scalar; `0` for null |
| `sum(list)` | 1 | numeric sum; `null` for empty or non-numeric input |
| `min(x, …)` / `max(x, …)` | 1..1000 | list or positional numbers; `null` for empty |
| `mean(list)` | 1 | arithmetic mean; `null` for empty |
| `all(list)` | 1 | `true` for `[]`; `null` if a non-boolean is present and no `false` decides it |
| `any(list)` | 1 | `false` for `[]`; `null` if a non-boolean is present and no `true` decides it |
| `contains(text, match)` | 2 | substring test |
| `substring(text, start[, length])` | 2..3 | 1-based; zero or out-of-range start is `null` |
| `string(x)` | 1 | number/boolean/text/temporal/duration; `null` for null or compound values |
| `number(from, group_sep, decimal_sep)` | 3 | parses with separators; `null` when invalid |
| `date(...)` / `time(...)` / `date and time(...)` | 1 or 3 / 1 or 3 / 1 or 2 | constructors and parsers |
| `duration(text)` | 1 | ISO 8601 duration; `null` when invalid |
| `not(x)` | 1 | Kleene negation |

Unknown function names raise `EvalError`; wrong arity raises `E_ARG`; invalid values return `null`.
Names resolve from the context; an unknown name evaluates to `null`.

## Decision tables

```json
{
  "inputs": ["age", "risk"],
  "outputs": ["discount"],
  "hit_policy": "first",
  "rules": [
    { "when": { "age": "[18..25]", "risk": "high" }, "then": { "discount": 0.1 } }
  ],
  "default": { "discount": 0 }
}
```

- `hit_policy` is `first` only; rules are evaluated in order and every `when` entry must match.
- A cell is a scalar (equality), a list (any-of), `-` (always), or text:
  - text is parsed as a FEEL expression with `?` bound to the input value (`? >= 18`, `? in [1..5]`);
  - text that starts with a comparison operator is read as `? <operator> …` (`>= 65`);
  - a bare name or a text that is not valid FEEL is compared as a string (`"high"`, `"in progress"`);
  - a range literal (`[18..25]`) is a membership test.
- `then` values starting with `=` are FEEL expressions over the inputs (`"= amount * 0.05"`); anything
  else is a literal passed through (numbers become int/float).
- Missing inputs raise `E_CONFIG`; no matching rule without a `default` yields `{}`.
- Validation: unknown keys, duplicate inputs, unknown inputs in rules, missing outputs, non-`first` hit
  policies, empty rule lists, more than 1,000 rules, and non-scalar cells are rejected with `E_CONFIG`.

## Limits

| Limit | Value |
|---|---|
| Expression length | 20,000 characters |
| Tokens per expression | 5,000 |
| Nesting depth | 100 |
| List literal / call arguments | 10,000 items |
| Table rules | 1,000 |
| Cell list items | 100 |
| Decimal digits | 100 |
| Oracle cases per run | 500, 20 s each |
| CLI JSON files | 5 MiB |

## Explicitly out of scope for v0.1

`instance of`, `for … return`, filters with expressions (`list[item > 2]`), `%`, `starts with` / `ends
with` / `matches`, string functions beyond `contains`/`substring`, boxed expressions, DMN XML import,
non-`first` hit policies, and the DMN TCK harness. `parse`, `render`, `evaluate` and `decision_table` are
the supported API; anything else may change.
