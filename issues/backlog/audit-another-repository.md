---
waits_on: [bootstrap-audit]
---

# Audit a Project that lives in another repository

`just audit <project> <bootstrap>` (DR-353) runs from a stereorepo checkout
and audits only the Projects stereorepo's own `structure.yaml` asserts. It is
scaffold-only because the bootstrap records it compares with
(`.meta/assertions/bootstraps.yaml`) do not ship to a portfolio. DR-312's
audit is for a brownfield product, which lives in its own repository, so
today the audit cannot reach the product it exists for.

## Wanted

The audit takes a target repository, as `just adapt plan <repository>`
does, reads the named Project and its gate from that repository's
`.meta/assertions/structure.yaml`, runs the gate there, and compares it with
stereorepo's bootstrap. Decide whether the target is a recipe flag or a
second recipe, within DR-349's atomic identifiers.

## Done when

A probe audits a temporary repository whose `structure.yaml` asserts one
Project with a stub gate, from the scaffold, and finds the same gaps the
existing probe cases find.
