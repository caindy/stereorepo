# python-seed's tests pass when its wheel names a package that is not there

Found while implementing `seed-rendered-gate-lost`. With the
`'packages = ["src/seed"]'` entry dropped from `RENAMES` in
`bootstraps/python/render`, the rendered copy's
`packages/acme/pyproject.toml` tells hatch to package `src/seed`, which no
longer exists. The `python-seed` gate still reported `ok` for `test`, `types`
and `mutants`; only `evidence` reported
`?  python-seed/evidence: pytest --collect-only in acme exited with 2`, and the
gate exited 0. The pair loop holds a landing on any `?`, so the fault would
reach the developer, but as a step that could not run rather than a failure.

A portfolio built from such a render would ship a wheel without its package.
Find out why `test` passes (an editable install that puts `src/` on the path
whatever `packages` says is the likely reason) and decide whether the seed's
gate should build and import the wheel, so that this fails a step.
