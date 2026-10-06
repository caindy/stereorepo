---
difficulty: easy
---

# Check formatting in python-seed's gate, or stop expecting it

python-seed's gate runs `ruff check` but never `ruff format --check`, so
formatting drift goes unreported. On `pair/python-seed-gate-stdout`,
`ruff format --check` would reformat code nobody had touched: the `CITATION`
pattern in `bootstraps/python/seed/gate/src/gate/__init__.py` and the
`FLOOR_CASES` table in `bootstraps/python/seed/gate/tests/test_probes.py`.
On this branch, `ruff format --check .` in `bootstraps/python/seed` still
names those two files and no others.

## The developer's decision (2026-10-05)

Honour DR-193, which retired `ruff format --check .` from the Python seed's
gate for its context-window cost and its rebase churn. The gate does not
check formatting, and the rest of the Python standard already says so. The
formatting step an earlier turn wrote was sent back with this Issue and is
not on `main`.

## Wanted

- The `ruff` step's docstring in `bootstraps/python/seed/gate/src/gate/__init__.py`
  says that formatting is not checked, and why, citing DR-193, so the next
  reader does not add the step again.
- A test asserts that the gate has no formatting step.

## Out of scope

- The Rust seed's `fmt` step, which stays.
- Any change to DR-193 or to the files that already describe it.

## Done when

- `just gate python-seed` passes with no formatting step.
- The `ruff` docstring names DR-193.
