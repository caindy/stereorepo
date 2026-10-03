---
difficulty: medium
waits_on: [bootstrap-audit]
---

# Audit a Project that lives in another repository

`just audit <project> <bootstrap>` (DR-353) runs from a stereorepo checkout
and audits only the Projects stereorepo's own `structure.yaml` asserts:
`.meta/audit.py`'s `main` reads the Projects through `gate.structure()` and
`audit` runs the gate with `cwd=gate.ROOT`, both stereorepo's root. It is
scaffold-only because the bootstrap records it compares with
(`.meta/assertions/bootstraps.yaml`) do not ship to a portfolio. DR-312's
audit is for a brownfield product, which lives in its own repository, so
today the audit cannot reach the product it exists for.

## Wanted

- The audit takes a target repository, as `just adapt plan <repository>`
  does. It reads the named Project and its gate from that repository's
  `.meta/assertions/structure.yaml`, runs the gate with that repository's
  root as its working directory, and compares what it reports with
  stereorepo's Bootstrap, exactly as it does today.
- With no target, it behaves as today.
- How the target is passed (an optional flag on `audit`, such as
  `--repository <path>`, or a second recipe) is the pair's choice within
  DR-349: recipes take only flags, subcommands and atomic identifiers. If
  the recipe's signature changes, the `audit` entry in `justfile()` in
  `.meta/lib/render/writers.py` and the recipe contract in
  `.meta/checks/files/justfile.py` change with it.
- A target with no `.meta/assertions/structure.yaml`, or one that does not
  assert the named Project, exits with a message naming the repository and
  what is missing, as an unknown Project does today.

## Out of scope

- Adopting a repository that has no `structure.yaml` yet; that is
  `just adapt`'s business.
- Shipping the audit or the bootstrap records to a portfolio.

## Done when

- A probe case in `.meta/checks/probes/tools/audit.py` builds a temporary
  repository whose `structure.yaml` asserts one Project with a stub gate,
  audits it from the scaffold, and finds the same gaps the existing probe
  cases find for the same stub output.
- A probe case audits a temporary directory with no `structure.yaml` and
  gets the message, not a traceback.
- The existing probe cases, which audit with no target, pass unchanged.
