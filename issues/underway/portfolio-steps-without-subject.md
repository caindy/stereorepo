---
difficulty: medium
parent: onboard-fitch-mvp
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

Since `landing-gate-holds-on-could-not-run`, the pair loop also holds every
landing whose gate reports a step that could not run. fitch-mvp's `meta` gate
reports both, so no Issue can land in fitch-mvp until this one does.

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

## The developer's answers (2026-10-02)

1. **`brownfield adoption probes`: remove.** Specialization removes
   `.meta/adapt.py`, `lib/adapt` and their probe from a portfolio, since they
   have no subject there.
2. **`comment probes`: keep the Projects in lockstep.** In a portfolio, the
   synchronization half of the step checks every Python Project's `gate`
   package (each one `just bootstrap python` laid down, such as
   `core-lib/gate` in the specialization fixture) against
   `.meta/checks/comments.py`, in place of the scaffold's seed. A Project's
   `uv run gate` and the root `just gate` must give the same verdict on the
   same code. Otherwise a seat's targeted gate can pass a change that the
   landing gate refuses. The cost is accepted: a change to `comments.py`
   updates every Python Project's copy in the same change. A portfolio with
   no Python Project has nothing to synchronize, and the step says so in its
   scope and passes.
3. **How removal is expressed: accept nested paths.** `SCAFFOLD_ONLY_PATHS`
   (`.meta/test_specialization.py`) and `SCAFFOLD_ONLY`
   (`.meta/checks/files/scaffold.py`) accept paths below the top level, so a
   single probe module under `.meta/checks/probes/` can be scaffold-only.

Record these answers as a Decision Record, with the change.
