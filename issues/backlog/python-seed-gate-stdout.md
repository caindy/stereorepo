---
difficulty: easy
---

# Keep python-seed's tools off its gate's standard output

python-seed's gate (`bootstraps/python/seed/gate/src/gate/__init__.py`)
runs ruff, mypy, pytest and mutmut with `subprocess.run` and lets them
inherit standard output. Their output lands between the step reports:
`All checks passed!`, pytest's session banners, and mutmut's spinner lines.
`just audit python-seed python` counted 100 such lines on a clean run and
reports them as a gap against Article 21 (DR-092, DR-353). `.meta/gate`
tolerates them only because it sends unshaped lines to standard error.

## Wanted

Each step that runs a tool sends the tool's standard output to standard
error (or captures it and quotes it as problem lines when the step fails),
so the gate's standard output is only its step reports and its closing
block.

## Out of scope

The closing block that `closing_block` prints when a step could not run;
whether it should go to standard error is its own question.

## Done when

- A probe in `bootstraps/python/seed/gate/tests/` runs a step that calls a
  tool printing to standard output, and finds only the step's report on the
  gate's standard output.
- `just audit python-seed python` reports no report-shape gap.
