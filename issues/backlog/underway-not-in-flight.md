---
difficulty: easy
parent: flights
---

# Call the Issue being worked *underway*, not *in flight*

One part of `flights`. "In flight" today means the one Issue the loop is
working. `flights` gives the phrase to a Flight's parts, so the Issue being
worked becomes *underway*.

## Wanted

Replace "in flight" meaning the Issue being worked with "underway" (or "being
worked" where that reads better) in:

- `pair/loop.py` (the `status` docstring and its `in flight:` and
  `nothing in flight` lines), `pair/pair.py` (the `status` help);
- `pair/README.md` (three uses: "the turn in flight", "steer an Issue in
  flight" and "the Issue or grooming pass in flight"), `issues/README.md`,
  `template/issues/README.md`, and `AGENTS.md`, where the phrase is wrapped
  across lines 38–39 (then re-render so `CLAUDE.md` and its siblings follow);
- the `pair-status` recipe comment in `.meta/lib/render/writers.py`, then
  re-render the `justfile`;
- `.meta/checks/files/board.py` and `.meta/checks/probes/files/board.py`;
- `.gitignore`;
- `issues/backlog/cockpit-status-convention.md`.

Update any test in `pair/test_pair.py` that matches the old status text.

## Out of scope

`WHY_FORK.md`, `apm_modules/` (derived), and Issues in `issues/done/`, which
are history. Defining Flight (`flight-vocabulary`).

## Done when

Run at the repository root,
`rg --hidden -U -i -l 'in\s+flight' -g '!.git' -g '!WHY_FORK.md' -g '!issues/done/**' -g '!apm_modules/**' -g '!issues/backlog/flight*.md' -g '!issues/backlog/underway-not-in-flight.md'`
finds nothing. The search spans line breaks: `git grep "in flight"` would miss
the use in `AGENTS.md`. `just pair-status` says "underway", and `just gate`
passes.
