# Nothing renders a seed and gates the copy any more

`bootstraps/python/seeded-artifacts.md` and `bootstraps/rust/seeded-artifacts.md`
("Rendered, then gated"), the header comments of `bootstraps/python/render` and
`bootstraps/rust/render`, the closing paragraph of
`bootstraps/python/nothing-unconsumed.md` and `bootstraps/rust/nothing-unconsumed.md`,
and DR-091 and DR-094 say a `python seed` / `rust
seed` job in `.github/workflows/gate.yml` renders each seed as `acme` and runs
its gate on the result. That workflow was removed with the pull-request flow,
and no recipe, gate step or pair-loop step does the same now. Only the seeds'
in-place gates (`work:project/python-seed`, `work:project/rust-seed` in
`.meta/assertions/structure.yaml`) run, so a fault that only shows in a
rendered copy (a missed rename, a lockfile that no longer matches) goes
unseen.

Either restore a rendered-then-gated run somewhere the pair loop reaches, or
correct the prose and Decision Records to say the in-place gate is all there
is. Found while grooming `bootstrap-render-step`.
