---
difficulty: hard
parent: onboard-fitch-mvp
waits_on:
  - sync-portfolio-recipe
  - portfolio-owns-ratchet-baselines
  - adoption-plan-omits-scaffold-only-paths
---

# Write Adoption as a Discipline beside Specialization

Specialization covers an empty repository, and nothing covers an existing
one. Write Adoption as a Discipline beside Specialization, rendered as
`SPECIALIZE.md` is, from what fitch-mvp needed.

It covers:

- the ten findings under "Findings for the adoption procedure" in the
  Flight `onboard-fitch-mvp`;
- the sync recipe of `sync-portfolio-recipe`;
- keeping product tools out of the loop's worktree. The worktree sits at
  `worktrees/pair`, inside the portfolio's tree, so a product tool that walks
  the tree finds it. fitch-mvp's pytest collected the worktree's copy of its
  tests and failed on duplicate modules until a `pytest.ini` set
  `testpaths = tests`;
- pinning the interpreter for an adopted repository's gate where it needs
  one. `uv` defaults to Python 3.14, on which one of fitch-mvp's pinned
  requirements does not build, so its gate runs under `--python 3.13`;
- declaring the product's schemas before the first gate. Prose about a
  product's own schema slots is checked against that schema only once the
  Project's `schemas` names it (DR-304).

## Done when

- An Adoption Discipline exists in `.meta/assertions/disciplines.yaml` and
  renders to a generated page at the root, as Specialization renders to
  `SPECIALIZE.md`.
- Each item above is a step of it, or is named as handled by a tool that a
  step runs.
- Each finding in the Flight that says *Waits for the procedure* names the
  step that covers it.
