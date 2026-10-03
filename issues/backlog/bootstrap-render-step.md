---
difficulty: easy
waits_on: [bootstrap-audit]
---

# Make the bootstraps' `render` step real, or stop naming it

Both bootstraps in `.meta/assertions/bootstraps.yaml` (`work:bootstrap/python`
and `work:bootstrap/rust`) say Seeded Artifacts is held by a gate step called
`render`. Neither seed's gate has one: python-seed's `STEPS` in
`bootstraps/python/seed/gate/src/gate/__init__.py` run `lints` through
`mutants`, and the Rust seed's xtask (`bootstraps/rust/seed/xtask/src/lib.rs`)
has no `render` either. So the reference names a step its own seeds don't
report, and `just audit` flags it against both of them.

## How to reproduce

`just audit python-seed python` and `just audit rust-seed rust` each print a
gap for the missing `render` step and exit non-zero.

## Wanted

A Bootstrap describes what a Project built from it inherits. Seeded Artifacts
asks that a seed (a template) be gated by rendering it and gating the
result. A Project instantiated from either seed holds no template of its own,
so there is nothing for a `render` step in its gate to render; adding an
empty step would be the "suite nothing runs" the Discipline itself warns of.

So, in both bootstraps, Seeded Artifacts becomes `status: exempt` with an
`exemption_reason` saying that a Project built from the seed holds no seed,
and naming what does gate the seed itself (find it: the stereorepo gate step
or recipe that instantiates the seed and gates the result, such as
`just test-specialization` or the seed Projects' own gates in
`.meta/assertions/structure.yaml`). If the search finds that a seed's gate
does already render and gate a template under another step name, set
`held_by` to that step instead, for that bootstrap.

Write the choice as a Decision Record if it settles anything beyond these
two entries (for example, that a Bootstrap exempts a Discipline whose
subject its Projects do not hold).

## Out of scope

- Adding a `render` step to either seed's gate.
- Any other gap `just audit` reports.

## Done when

`just audit python-seed python` and `just audit rust-seed rust` report no
`render` gap, and the `exemption_reason` (or `held_by`) names a mechanism
that exists in the tree.
