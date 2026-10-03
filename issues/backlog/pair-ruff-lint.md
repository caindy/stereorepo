# Lint the pair loop with the repository's ruff configuration

`pair/` is not checked by ruff in any gate. Run against `.meta/ruff.toml`,
`ruff check pair/` reports 60 findings today, almost all from before
`cockpit-status-convention`: long lines (E501), complex functions (C901,
PLR0912), too many arguments (PLR0913, including `append_event`, `Loop.__init__`
and one in `pair/seats.py`), vanilla exception messages (TRY003), and a
handful of single findings (BLE001 in `pair/gate.py`, SIM102, F402, PTH109,
PTH208, RUF021, C416, B905). A `# noqa` written in `pair/` therefore documents
a choice but enforces nothing.

## Wanted

- The `pair` Project's gate runs `ruff check` over `pair/` with
  `.meta/ruff.toml`, as `.meta/check.py` does for the code it lints.
- Each existing finding is fixed, or suppressed in the
  `# noqa: CODE  # reason: ...` form `.meta/check.py` uses, with a reason
  that holds.

## Out of scope

- Changing ruff's rule set for the rest of the repository.
- Restructuring the loop beyond what a finding needs.

## Done when

- `ruff check --config .meta/ruff.toml pair/` reports nothing.
- Introducing a new finding in `pair/loop.py` makes the `pair` gate fail.
