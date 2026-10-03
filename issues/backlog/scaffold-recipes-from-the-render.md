---
difficulty: medium
---

# Derive the scaffold-only recipes from the render

`SCAFFOLD_RECIPES` in `.meta/checks/files/justfile.py` lists by hand the
recipes a portfolio's `justfile` does not hold. The render decides the same
thing separately, in `justfile()` in `.meta/lib/render/writers.py`, by which
Artifacts `structure.yaml` asserts:

| Artifact | Recipes |
|---|---|
| `work:artifact/pair` | `pair`, `groom`, `pair-status`, `pair-accept`, `pair-resume`, `pair-watch` |
| `work:artifact/meta-test-specialization` | `test-specialization` |
| `work:artifact/meta-release` | `release` |
| `work:artifact/meta-audit` | `audit` |
| `work:artifact/meta-adapt` | `adapt` |

When a recipe is added under one of those conditions and not to the tuple,
every portfolio's `justfile recipe shape` step fails while stereorepo's
passes; `release` did exactly that (`release-recipe-is-scaffold-only`).

## Wanted

- The set of conditional recipes, each with the Artifact it depends on, is
  declared once, in one place that both the render and the check read (for
  example a table in `.meta/lib/render/writers.py` that `justfile()` iterates
  and `justfile.py` imports, or the reverse).
- `justfile()` renders each conditional recipe from that table, so a recipe
  added to it is both rendered under its condition and known to the check,
  and a recipe written outside it is unconditional.
- `SCAFFOLD_RECIPES` is derived from the table, or replaced by it, and the
  rendered `justfile` is byte-identical to today's.
- The probe in `.meta/checks/probes/surface.py` that mentions
  `SCAFFOLD_RECIPES` still describes what it tests.

## Out of scope

- Running a portfolio's gate before landing (`portfolio-gate-before-landing`).
- Changing which recipes are scaffold-only.

## Done when

- `SCAFFOLD_RECIPES` is no longer a hand-written list of names: a grep of
  `.meta/checks/` finds no literal list of the ten recipe names.
- A test (or probe) adds an entry to the table under an Artifact a
  portfolio's `structure.yaml` lacks, and shows the check exempts it for that
  portfolio and the render omits it, with no other edit.
- `just render` leaves the root `justfile` unchanged.
