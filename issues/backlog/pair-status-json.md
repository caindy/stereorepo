---
difficulty: medium
parent: flight-instruments
waits_on: [status-lists-what-waits-on-the-developer]
---

# `just pair-status --json`

`just pair-status` prints a screen for the developer. A session driving the
loop needs the same state as data, without parsing that screen.

## What is wanted

- `just pair-status --json` prints one JSON object holding the state the human
  screen shows once `status-lists-what-waits-on-the-developer` has landed:
  what waits on the developer, each with its reason; the Issue underway, its
  stage and turn, or none; the running order, with ripe and waiting Issues
  told apart and what each waiting one waits on; and the counts per stage.
- The state is derived once, in `pair/loop.py`, and both the screen and
  `--json` render it, so the two cannot disagree.
- `pair/README.md` documents the object's fields.

## Out of scope

- Publishing the state outside the repository (`cockpit-status-convention`).
- Anything the human screen does not show.

## Done when

- For every state the pair tests drive the loop into, `--json` parses and
  holds what the screen shows.
- `pair/README.md` documents the fields, and `just gate` passes.
