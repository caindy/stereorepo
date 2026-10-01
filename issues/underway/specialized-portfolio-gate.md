---
difficulty: medium
---

# Make a freshly specialized portfolio pass its own gate

`just test-specialization` specializes the scaffold into a scratch repository
and runs that portfolio's gate. The portfolio's `meta` Project fails five
steps. Every one of them also failed before the bootstrap removed PR First;
it went unnoticed because the test ran only in a weekly workflow.

## How to reproduce

Run `just test-specialization` at the root. The portfolio's gate reports `x`
on these steps:

- `rendered artifact probes`: `rendered(None)` fails to render the default
  targets.
- `dereference probes`: `--sample 4` finds 2 pairs, since a portfolio's
  record is smaller than the scaffold's.
- `brownfield adoption probes`: the probe reads `template/.meta/README.md`,
  which a portfolio does not have.
- `comment probes`: the probe imports the Python seed's `gate` module, which
  a portfolio has only once it bootstraps Python.
- `scaffold-only paths`: the Python bootstrap's APM skills, copied into
  `.meta/.apm/skills/`, name `bootstraps/`.

## Wanted

Each step passes in a portfolio without being weakened in the scaffold. A
probe that exercises something only the scaffold has either moves among the
scaffold-only paths, so specialization removes it, or passes over the absence
the way the specialization probe already does, reporting `?` with what it
could not check rather than `ok`. A probe whose threshold assumes the
scaffold's size (the dereference sample) scales to what the portfolio has.

## Out of scope

Running `just test-specialization` from `just gate`: it is slow, and whether
it belongs there is a separate question. Other failures a portfolio's other
Projects might have once it bootstraps a language.

## Done when

`just test-specialization` passes, the scaffold's `just gate` still passes
with every one of those five steps reporting what it did before, and neither
reports a step as `ok` that checked nothing.
