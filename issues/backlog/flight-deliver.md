---
difficulty: easy
parent: flights
waits_on:
  - flight-desk-check
---

# Run `just deliver`, where defined, before a Flight's desk check

One part of `flights`. Delivery is the repository's business, as provisioning
a worktree is (`just setup`): the loop never knows how a product deploys.

## Wanted

When a Flight passes its check, and before it lands in `desk-check/`, the loop
runs `just deliver` at the root of `main` if the `justfile` defines a
`deliver` recipe (for example, a redeployment to a UAT environment), and
records its outcome in the Flight's brief. If the recipe fails, the Flight does
not go to `desk-check/`: the loop pauses with the recipe's output tail, as it
does for a refused fast-forward. With no `deliver` recipe the step is skipped
silently.

`pair/README.md` says what `deliver` is for, next to `setup`.

## Out of scope

Defining a `deliver` recipe in this repository or in `template/`, and any
release gate after acceptance.

## Done when

The pair tests show the three cases (no recipe, a passing recipe, a failing
one), and `just gate` passes.
