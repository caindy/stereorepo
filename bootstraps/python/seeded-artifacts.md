# Seeded Artifacts, in Python

A seed is data, and it must not violate the rules it seeds.

Nothing in a Project built from the seed implements this, because that
Project holds no seed of its own and its gate has nothing to render. The seed
is held to it here, in the portfolio, by the gate of `work:project/python-seed`,
run on a rendered copy of the seed (DR-356, DR-360).

## Rendered, then gated

[`render`](render) copies the seed to a destination and names its package. The
gate of the `python-seed` Project renders it as a package called `acme` in a
temporary directory and runs `uv run --locked gate` on the result — A9: not
linted in place, gated by rendering it and running the real gates on what
comes out (DR-360). It runs on the support floor rather than the interpreter
developed on, so the floor is executed and not asserted (DR-095).

The seed also builds as it sits, under the name `seed`, which is what `render`
copies (DR-091). The rendered copy is the stronger claim, so it is the one the
gate runs. The lockfile is renamed with the rest, and `uv run --locked` in the
destination is what proves it still matches.

## Where the seed cannot yet satisfy a rule, it says why, in the seed

- `example.history.md` has no entry, and says so: the Evidence rule binds
  entries, and the form of one sits in the log as a comment the check ignores.
- The module docstring cites no Decision, and says what a citation there
  looks like.
- No coverage floor is set, and `observed-failure.md` says what would set one.
- The example is a loop and not a comprehension, and its docstring says why.

Each is written where whoever fills it in will read it, which is the step of
the Discipline that distinguishes an honest omission from a missing one.
