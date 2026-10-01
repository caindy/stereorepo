---
difficulty: hard
---

# Flight instruments: the loop's event log, `pair-watch` and exit codes

A copilot session that runs the loop for the developer has to know when an
Issue lands, when the loop pauses and why, and when something waits on the
developer. Today it can learn that only by scraping the loop's human-readable
output. Doing so has failed in practice: watchers that never exited, one that
read the wrong file, and a guard that misread a landing and stopped a sequence
that had succeeded. `just pair --once` exits 0 whether it landed an Issue,
paused, or found nothing ripe.

## What is wanted

- **An event log.** The supervisor appends one JSON object per line to
  `.pair/events.jsonl` for every transition: an Issue started, a stage
  advanced, a grooming pass started or landed, an Issue landed (with its slug
  and commit), an Issue sent back, the loop paused (with its reason), stopped,
  or found nothing ripe. Each event carries a timestamp, a kind and the slug.
  The log holds nothing the board, `.pair/` and git do not; it records when
  things happened.
- **`just pair-watch`** prints events as they are appended and exits when a
  condition is met: `--until landed` (the next landing), `--until developer`
  (anything that waits on the developer: a desk check, a pause, a send-back)
  and `--until flight <slug>` (that Flight reaches `desk-check/`). It exits
  non-zero if the loop stops without meeting the condition.
- **`just pair-status --json`** prints the state the human screen shows, as
  one JSON object.
- **Exit codes that say what happened.** `run`, `accept` and `resume` exit
  with distinct codes for landed, desk check, paused, stopped and nothing
  ripe, documented in `pair/README.md`.

## Parts

- `pair-exit-codes`: distinct exit codes for each outcome.
- `pair-event-log`: `.pair/events.jsonl` and `just pair-watch`.
- `pair-status-json`: `just pair-status --json`, after the human screen
  (`status-lists-what-waits-on-the-developer`) settles what the state is.

## Overlaps

- `status-lists-what-waits-on-the-developer` is the human screen;
  `pair-status --json` should be the same state, derived once.
- `cockpit-status-convention` publishes status across repositories; the
  event log should be what that projection is built from.

## Out of scope

- Notifications, and anything across repositories.

## Done when

- Every transition in the pair tests appends the matching event.
- `just pair-watch` exits on each condition above, and non-zero when the loop
  stops first.
- Each outcome of `run` has its own exit code, and `pair/README.md` lists
  them.
- The pair tests cover each of these, and `just gate` passes.
