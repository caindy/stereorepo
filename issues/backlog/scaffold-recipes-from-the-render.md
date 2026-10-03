# Derive the scaffold-only recipes from the render

`SCAFFOLD_RECIPES` in `.meta/checks/files/justfile.py` lists by hand the
recipes a portfolio's `justfile` does not hold. The render decides the same
thing separately: `.meta/lib/render/writers.py` writes `pair`, `groom` and
the `pair-*` recipes only under `work:artifact/pair`, `test-specialization`
under `work:artifact/meta-test-specialization`, `release` under
`work:artifact/meta-release`, and `adapt` under `work:artifact/meta-adapt`.
When a recipe is added under one of those conditions and not to the tuple,
every portfolio's `justfile recipe shape` step fails while stereorepo's
passes; `release` did exactly that (`release-recipe-is-scaffold-only`).

## Wanted

The set of recipes a portfolio does not hold comes from one place that both
the render and the step read, so a new conditional recipe cannot be left out
of it.

## Out of scope

- Running a portfolio's gate before landing (`portfolio-gate-before-landing`).
