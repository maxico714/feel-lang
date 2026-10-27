# Security policy

## Supported versions

| Version | Supported |
|---|---|
| 0.1.x | yes |

## Reporting a vulnerability

Use GitHub's private "Report a vulnerability" form on the repository's Security tab. Do not open a public
issue for anything that could crash the interpreter, exhaust memory, escape the sandboxed evaluation
model, or execute code.

Include the version (`feel-lang --version`), the Python version, the expression or decision table, and a
minimal reproduction. You can expect an acknowledgement within seven days and a remediation plan or a
reasoned decision within thirty days.

## Threat model in brief

- **Expressions are data, not code.** There is no `eval`, no `exec`, no import machinery and no attribute
  traversal into Python objects. Unknown names evaluate to `null`; unknown functions raise `E_EVAL`.
- **Bounded resources.** Input length (20k characters), token count (5k), nesting depth (100), list items,
  rule counts, decimal digits and CLI file size (5 MiB) all have hard caps, enforced before work grows.
- **Decision tables are validated fail-closed.** Unknown keys, duplicate inputs, unknown rule inputs,
  missing outputs, unsupported hit policies, oversized tables and non-scalar cells are rejected.
- **Optional oracle is a subprocess** with a fixed argument list, no shell, a 20-second timeout and a
  temporary directory. It is a user-supplied executable, treated as untrusted; its output is only
  compared as text.
- **No telemetry, no network access** in the library or CLI.

## Out of scope

- The semantics of values you pass in (for example a custom object with unusual equality).
- The behaviour of a dsntk binary you choose to run.
- Denial of service through repeated calls in your own process; each call is bounded, but callers decide
  how many calls to make.
