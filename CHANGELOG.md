# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] — 2026-10-26

### Added

- Lexer and recursive-descent parser for the decision-table-focused FEEL subset, with hard caps on input
  length, tokens and nesting depth.
- Evaluator with exact `Decimal` arithmetic, Kleene three-valued logic, ranges, 1-based list indexing,
  contexts, temporals, durations and 16 built-in functions.
- Decision tables with a first-match hit policy: unary-test cells, ranges, any-of lists, `-`, literal
  text, computed outputs and a default row; fail-closed schema validation.
- Python API: `evaluate`, `parse`, `decision_table`, `Evaluator`, `render`, typed errors with stable
  codes.
- CLI: `eval`, `parse`, `table`, `diff-oracle`, `doctor`; exit codes 0/1/2/3/4.
- Optional differential oracle against dsntk (Apache-2.0, user-supplied executable), with a 73-case
  corpus that matches 73/73 on dsntk v0.3.0.
- 220 tests including adversarial input, licence hygiene and fixture-driven decision tables.
- Pure-Python wheel (`py3-none-any`) and sdist; zero runtime dependencies.

### Notes

- Token/type errors follow FEEL's null-on-error model; unknown functions and wrong arity raise.
- `null = 1` follows the DMN equality rule (false), a documented divergence from dsntk.
- Not published to PyPI yet.

[Unreleased]: https://github.com/maxico714/feel-lang/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/maxico714/feel-lang/releases/tag/v0.1.0
