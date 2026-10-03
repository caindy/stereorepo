---
difficulty: medium
---

# Run a portfolio's gate before a change to what portfolios receive lands

A defect that shows only in a portfolio can land in stereorepo unseen.
`_probe_adopt` failed every portfolio's `meta` gate, specialized or adopted,
and landed, because nothing runs a portfolio's gate before landing:
`just test-specialization` (`.meta/test_specialization.py`) builds a
portfolio and runs its gate (step 8), but neither the loop nor `just gate`
runs that recipe. `adopt-probe-passes-in-a-portfolio` made stereorepo's own
gate run that one probe's portfolio branch, which covers that probe and no
other. It was found by hand, in fitch-mvp.

The loop chooses what to gate before landing in `pair/touched.py`
(DR-303): a changed path selects the Project whose directory holds it, and
every path under `.meta/` selects `meta`. `placed()` there already reads
`.meta/bundle.yaml`, but only to keep the bundle's paths with `meta` beside a
root Project; no selection follows from a path being one a portfolio
receives, so nothing gates a portfolio for it.

## Wanted

Before a change lands that alters what a portfolio receives (a path inside
one of the managed or template items in `.meta/bundle.yaml`), a specialized
portfolio's gate runs against it, and a failure there holds the landing as
any gate failure does. A change that touches none of it lands without that
cost, in the spirit of DR-303.

One shape that fits the existing selection: declare the specialization as a
Project (or Product) in `.meta/assertions/structure.yaml` whose gate runs
`.meta/test_specialization.py`, and have `pair/touched.py` select it when a
changed path lies inside a bundle item. Whichever shape is chosen, its gate
reports in the gate contract's shape, and the choice is recorded in a
Decision Record that extends DR-303.

## Out of scope

- Adopting a repository in the test, as well as specializing one.
- Making `test_specialization.py` faster.

## Done when

- A test of the selection in `pair/test_pair.py`: a change to a path inside
  a managed bundle item (for example under `.meta/checks/`) selects the
  portfolio gate; a change only to `issues/` or `pair/` does not.
- Running the selected gates for such a change runs the specialization and
  fails when the specialized portfolio's gate fails. Show it once by hand
  with a managed probe that reads a file only stereorepo has, and note the
  output here.
