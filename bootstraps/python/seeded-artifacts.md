# Seeded Artifacts, in Python

A seed is data, and it must not violate the rules it seeds. Two ways this seed
is held to that.

## Rendered, then gated

[`render`](render) copies the seed to a destination and names its package. The
`python seed` job in `.github/workflows/gate.yml` renders it as a package
called `acme` and runs `uv run gate` on the result — A9: not linted in place,
gated by rendering it and running the real gates on what comes out. The job
runs on the support floor rather than the interpreter developed on, so the
floor is executed and not asserted (DR-095).

The seed also builds and gates as it sits, under the name `seed`, which is what
lets the Project be asserted with a gate that runs (DR-091). Both are true and
the rendered one is the stronger claim, so the workflow runs that one. The
lockfile is renamed with the rest, and `uv run --locked` in the destination
is what proves it still matches.

## Where the seed cannot yet satisfy a rule, it says why, in the seed

- `example.history.md` has no entry, and says so: the receipt rule binds
  entries, and the form of one sits in the log as a comment the check ignores.
- The module docstring cites no Decision, and says what a citation there
  looks like.
- No coverage floor is set, and `observed-failure.md` says what would set one.
- The example is a loop and not a comprehension, and its docstring says why.

Each is written where whoever fills it in will read it, which is the step of
the Discipline that distinguishes an honest omission from a missing one.
