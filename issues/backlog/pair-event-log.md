---
difficulty: medium
parent: flight-instruments
---

# The loop's event log, and `just pair-watch`

A session that runs the loop for the developer learns what happened by
scraping the supervisor's printed lines, and its watchers have failed: some
never exited, one read the wrong file. The supervisor already writes one row
per turn to `.pair/turns.jsonl`, but nothing for the transitions between
turns.

## What is wanted

- **An event log.** The supervisor appends one JSON object per line to
  `.pair/events.jsonl` for every transition: an Issue started, a stage
  advanced (`Loop.move`), a grooming pass started or landed, an Issue landed
  (with the commit on `main`), an Issue sent back, a Flight moved to
  `desk-check/`, the loop paused (with its reason), stopped, or found nothing
  ripe, and the supervisor process ending (with its outcome). Each event
  carries a timestamp, a `kind` and the slug. The log holds nothing the board,
  `.pair/` and git do not; it records when things happened.
- **`just pair-watch`** prints events as they are appended and exits when its
  condition is met:
  - `--until landed`: the next landing;
  - `--until developer`: anything that waits on the developer, which is a
    desk check, a pause or a send-back;
  - `--until flight <slug>`: that Flight reaches `desk-check/`.

  It exits non-zero if the supervisor ends without meeting the condition, and
  at once if no supervisor holds a lock in `.pair/` when it starts, so a
  watcher never outlives the loop it watches. It reads only events appended
  after it starts.
- `pair/README.md` documents the event kinds and their fields, and the
  recipe's flags.

## Out of scope

- Exit codes (`pair-exit-codes`), and `pair-status --json`
  (`pair-status-json`).
- Notifications, and anything across repositories
  (`cockpit-status-convention`, which may build on this log later).

## Done when

- Every transition the pair tests drive appends the matching event, once.
- `just pair-watch` exits 0 on each condition above, non-zero when the
  supervisor ends first, and non-zero at once when no supervisor is running.
- `pair/README.md` lists the event kinds, and `just gate` passes.
