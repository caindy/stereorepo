---
difficulty: medium
---

# Lint the pair loop with the repository's ruff configuration

`pair/` is not checked by ruff in any gate. The `pair` Project's gate is
`pair/gate.py` (`.meta/assertions/structure.yaml`), and it runs only the
tests. Run against `.meta/ruff.toml`,
`ruff check --config .meta/ruff.toml pair/` reports 60 findings today
(counted while grooming): subprocess runs without `check` (PLW1510, 17),
long lines (E501, 13), complex functions (C901, 9; PLR0912, 4), vanilla
exception messages (TRY003, 6), too many arguments (PLR0913, 3, including
`append_event`, `Loop.__init__` and one in `pair/seats.py`), and one each of
BLE001 (in `pair/gate.py`), SIM102, F402, PTH109, PTH208, RUF021, C416 and
B905. A `# noqa` written in `pair/` therefore documents a choice but
enforces nothing.

## Wanted

- `pair/gate.py` runs `ruff check` over `pair/` with `.meta/ruff.toml` as a
  step of its own, reported in the gate contract's shape, as `.meta/check.py`
  does for the code it lints. Pin ruff to the version `meta`'s gate pins
  (`ruff==0.14.0` in `structure.yaml`).
- Each existing finding is fixed, or suppressed in the
  `# noqa: CODE  # reason: ...` form `.meta/check.py` uses, with a reason
  that holds. A PLW1510 finding where the return code is read is fixed with
  an explicit `check=False`, not suppressed.

## Out of scope

- Changing ruff's rule set for the rest of the repository.
- Restructuring the loop beyond what a finding needs; a C901 or PLR0912
  finding that would need a redesign is suppressed with its reason.

## Done when

- `ruff check --config .meta/ruff.toml pair/` reports nothing.
- The `pair` gate's output carries a ruff step reporting `ok`.
- Adding an unused import to `pair/loop.py` makes that step report `x` and
  the `pair` gate fail.
- The pair tests still pass.
