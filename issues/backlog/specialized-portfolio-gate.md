# Make a freshly specialized portfolio pass its own gate

`just test-specialization` specializes the scaffold into a scratch repository
and runs that portfolio's gate. The portfolio's `meta` Project fails five
steps. Every one of them also failed before the bootstrap removed PR First; it
went unnoticed because the test ran only in a weekly workflow.

- `rendered artifact probes`: `rendered(None)` fails to render the default
  targets.
- `dereference probes`: `--sample 4` finds 2 pairs, since a portfolio's record
  is smaller than the scaffold's.
- `brownfield adoption probes`: the probe reads `template/.meta/README.md`,
  which a portfolio does not have.
- `comment probes`: the probe imports the Python seed's `gate` module, which a
  portfolio has only once it bootstraps Python.
- `scaffold-only paths`: the Python bootstrap's APM skills, copied into
  `.meta/.apm/skills/`, name `bootstraps/`.

A probe that exercises something only the scaffold has belongs among the
scaffold-only paths, or must pass over its absence the way the specialization
probe already does.

Done when `just test-specialization` passes.
