---
waits_on: [bootstrap-audit]
---

# Make the bootstraps' `render` step real, or stop naming it

Both bootstraps in `.meta/assertions/bootstraps.yaml` say Seeded Artifacts
is held by a gate step called `render`. Neither seed's gate has one:
python-seed's `STEPS` in `bootstraps/python/seed/gate/src/gate/__init__.py`
run `lints` through `mutants`, and the Rust seed's xtask
(`bootstraps/rust/seed/xtask/src/lib.rs`) has no `render` either. So the
reference names a step its own seeds don't report, and `just audit`
(`bootstrap-audit`) flags it against both of them.

## Wanted

Choose one: add a `render` step to both seed gates that holds Seeded
Artifacts, or change `held_by` for Seeded Artifacts to the step that actually
holds it (or mark the Discipline `exempt` with an `exemption_reason`, if the
portfolio's `.meta` gate holds it rather than the seed's).

## Done when

`just audit python-seed python` and `just audit rust-seed rust` report no
`render` gap.
