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

## Desk-check brief

All three parts have landed on `main`: `pair-exit-codes`, `pair-event-log`
and `pair-status-json`. A session driving the loop can now learn what happened
without reading the loop's printed output.

**What was delivered**

- **The event log.** The loop working Issues and a grooming pass both append
  one JSON object per line to `.pair/events.jsonl` at the repository root.
  Every event carries `at`, `kind` and `loop`, plus `slug` where there is one.
  The kinds are `started`, `moved`, `landed` (with `sha` and `stage`),
  `groomed`, `sent-back`, `desk-check`, `paused` and `stopped` (each with
  `reason` and `retry`), `empty`, and `ended` (with the run's `outcome`). The
  table is in `pair/README.md` under "The event log", and the code is
  `append_event` in `pair/loop.py`.
- **`just pair-watch --until landed | developer | flight <slug>`**
  (`pair/watch.py`). It prints each event appended after it starts. It exits
  0 when its condition is met, 1 when every loop it watches has ended first
  (whether the loop logged `ended` or was killed), and 2 at once when no loop
  is running. It watches only the loops whose pid is in `run.lock` or
  `groom.lock` when it starts, so it never outlives them.
- **`just pair-status --json`**. It prints the same state as the human
  screen, derived once (`status_view` in `pair/loop.py`), as one object keyed
  `waiting`, `underway`, `order`, `to_groom`, `counts`, `sessions` and `turns`.
- **Exit codes.** `run`, `groom`, `accept` and `resume` print
  `pair: <outcome>` and exit with that outcome's code: 0 when nothing more is
  needed, 3 desk-check, 4 paused, 5 stopped, 6 kicked, 7 empty, 8 nothing,
  9 refused, 10 none, and 11 when another loop holds the lock. The codes skip
  1 (a crash) and 2 (a usage error). The table is in `pair/README.md` under
  "Exit codes".

**Checked on this branch, which is at `main`'s head**

- `just gate` passes: 104 steps across 4 projects, including 127 pair tests.
  `ExitCodeTest`, `EventLogTest` and `WatchTest` in `pair/test_pair.py`
  together cover every event kind, every watch condition, a loop that ends
  first, a killed loop, no loop, and a distinct code for each outcome.
- `just pair-status --json` parses as JSON and shows this Flight underway at
  `flight-check`.
- `just pair-watch --until landed`, run while this loop was running, waited
  for a landing rather than exiting. I stopped it by hand.

**Worth trying**

- Run `just pair --once` in one terminal and `just pair-watch --until landed`
  in another, starting the watcher only once the loop has printed its first
  line: a watcher started before the loop holds `run.lock` exits 2 at once.
  The watcher should exit 0 at the landing. Then run `echo $?`
  after `just pair --once` to see the run's code.
- Run `just pair-watch --until developer` across a run that reaches a desk
  check or a pause, and `--until flight <slug>` across a Flight's last part.
- Press Ctrl-C on the loop while a watcher waits. The watcher should exit 1
  once the loop has logged `ended`.
- Run `just pair-status --json | jq .waiting` while something waits on you.

**Not in this Flight**

- `just pair-watch` still exits with 1 and 2, the same codes as a crash and a
  usage error. `issues/backlog/pair-watch-exit-codes.md` already carries that
  follow-up. The Flight's "Done when" asks only for a non-zero exit, so I have
  not made it a part of this Flight.
