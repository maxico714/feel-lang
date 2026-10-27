## What changed

<!-- One paragraph: the failure or gap and the fix. -->

## How it was verified

- [ ] `ruff check . && ruff format --check . && mypy && pytest` pass locally
- [ ] New or changed behaviour has a test that failed before the change
- [ ] For operator/range changes: mutation check described below (break it, see the test fail, restore)
- [ ] `docs/FEEL_SUBSET.md` updated if semantics or limits changed

Commands and results:

```console
$ python -m pytest -q
```

## Checklist

- [ ] No new runtime dependencies (stdlib-only test still passes)
- [ ] No GPL-derived code, tests or fixtures
- [ ] New syntax respects the input/token/depth caps
- [ ] No TODO/FIXME left in `src/`
