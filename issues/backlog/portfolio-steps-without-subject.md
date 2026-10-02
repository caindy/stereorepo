---
difficulty: medium
---

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

## How to reproduce it

Run `just test-specialization` with `CI=1` in the environment. Step 8 runs
the portfolio's gate, which lists both steps under "steps that could not
run" and exits non-zero.

## Wanted

A freshly specialized portfolio's `meta` gate reports no step as `?`, so it
passes with `CI` set.

## Out of scope

- How `closing_block` treats a `?` under CI (DR-261 stands).
- Any other step that is `?` in the scaffold itself.

## Done when

- `just test-specialization` run with `CI=1` passes step 8, and its gate
  output names neither `brownfield adoption probes` nor `comment probes` as a
  step that could not run.
- The scaffold's own `meta` gate still runs both steps and they pass.

# Needs elaboration

Each step can leave the portfolio in one of two ways, and which is right is a
decision about what a portfolio is, so it is the developer's:

1. **`brownfield adoption probes`.** `.meta/adapt.py`, `lib/adapt` and their
   probe plan adoption from the scaffold's `template/`, which a portfolio
   does not have. Should specialization remove all three from a portfolio
   (recommended: they have no subject there), or should a portfolio keep
   them, with the probe running against a fixture template it carries?
2. **`comment probes`.** In a portfolio, should the seed gate
   synchronization check the Python Project that `just bootstrap python` laid
   down (`core-lib/gate` in the specialization fixture) instead of the
   scaffold's seed, or does that Project's gate drift from
   `.meta/checks/comments.py` by design, in which case the synchronization
   half of the step is scaffold-only and only that half should go?
3. **How removal is expressed**, if either answer is removal.
   `SCAFFOLD_ONLY_PATHS` (`.meta/test_specialization.py`) and `SCAFFOLD_ONLY`
   (`.meta/checks/files/scaffold.py`) match only top-level names, so a single
   probe module under `.meta/checks/probes/` cannot be one today. Should they
   accept nested paths (recommended), or should a scaffold-only step instead
   answer `Passed` with a scope saying it has no subject in a portfolio?

Once these are answered, record them as a Decision Record and drop this
section.
