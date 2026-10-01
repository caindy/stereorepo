# Leave a portfolio no step that can never run there

A freshly specialized portfolio's `meta` gate reports two steps as `?` for
good: `brownfield adoption probes` (no `template/` to adopt from) and
`comment probes` (no `bootstraps/python/seed/gate/src` to keep in step with
`comments.py`). Both steps exercise something only the scaffold has. The
`specialized-portfolio-gate` Issue made them say so rather than fail. But a
`?` fails the run wherever `CI` is set (`.meta/check.py`, `closing_block`,
DR-261). So a portfolio whose CI sets `CI` fails on every run, and so does
`just test-specialization` run under CI, since `step_8_run_gate` passes the
environment through.

Questions to settle:

- Should specialization remove scaffold-only steps from a portfolio? Today
  `SCAFFOLD_ONLY_PATHS` (`.meta/test_specialization.py`) and `SCAFFOLD_ONLY`
  (`.meta/checks/files/scaffold.py`) match only top-level names, so a single
  probe module under `.meta/checks/probes/` cannot be one.
- Does `.meta/adapt.py`, with `lib/adapt` and its probe, belong in a portfolio
  at all? It plans adoption from the scaffold's `template/`, which a
  portfolio does not have.
- Could the seed gate synchronization in a portfolio check the Python Project
  that `just bootstrap python` laid down (`core-lib/gate` in the
  specialization fixture) instead of the scaffold's seed? Or does that
  Project's gate drift from `.meta/checks/comments.py` by design?
