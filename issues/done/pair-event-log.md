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
  (with the commit on `main`), an Issue sent back to `backlog/` with a
  `Needs elaboration` section (`Loop.kick_back`), an Issue or a Flight
  reaching its desk check, the loop paused (with its reason), stopped, or
  found nothing ripe, and the supervisor process ending (with its outcome).
  Each event carries a timestamp, a `kind`, the slug where there is one (none
  when nothing was ripe), and `loop`: `pair` for the loop
  holding `run.lock`, `groom` for a grooming pass holding `groom.lock`. Both
  append to the one file, a line per write. The log holds nothing the board,
  `.pair/` and git do not; it records when things happened.
- **`just pair-watch`** prints events as they are appended and exits when its
  condition is met:
  - `--until landed`: the next Issue landing on `main` (a grooming pass
    landing does not count);
  - `--until developer`: anything that waits on the developer, which is a
    desk check, a pause or a send-back;
  - `--until flight <slug>`: that Flight reaches `desk-check/`.

  It watches the supervisors holding a lock in `.pair/` when it starts. It
  exits non-zero once all of them have ended without meeting the condition,
  whether they logged their end or were killed and released their lock, and at
  once if none holds a lock when it starts, so a watcher never outlives the
  loop it watches. It reads only events appended after it starts.
- `pair/README.md` documents the event kinds and their fields, and the
  recipe's flags.

## Out of scope

- Exit codes (`pair-exit-codes`), and `pair-status --json`
  (`pair-status-json`).
- An event for the developer's answer to a desk check (`pair-accept`,
  `pair-resume`). With a Flight's slug they hold no lock and write nothing.
  Without one they take `run.lock` and go on working the Issue, so the
  moves, landings and pauses that follow log as any loop's do.
- Notifications, and anything across repositories
  (`cockpit-status-convention`, which may build on this log later).

## Done when

- Every transition the pair tests drive appends the matching event, once.
- `just pair-watch` exits 0 on each condition above, non-zero when the
  supervisor ends first (including one killed without logging its end), and
  non-zero at once when no supervisor is running; tests in
  `pair/test_pair.py` cover each case.
- `pair/README.md` lists the event kinds, and `just gate` passes.

## The plan

### Files and seams

- `pair/loop.py`
  - A function `event_log(repo)` returning `.pair/events.jsonl`. It is
    `runtime_dir(repo, "pair")`, whatever the loop's kind, so both loops
    write the one file.
  - A method `Loop.event(kind, slug=None, **fields)`. It writes
    `{"at", "kind", "loop": self.kind, "slug"?, **fields}`, with `at` in the
    local `%Y-%m-%dT%H:%M:%S` that `record` writes to `turns.jsonl`, as one
    line through a single `write()` on a file opened for appending. That
    append is atomic for lines this small on a local disk, so the two loops
    can't interleave within a line.
  - Kinds, and where each is called:

    | kind | where | fields |
    |---|---|---|
    | `started` | the end of `start` (an Issue, or a pass with slug `grooming`) | `stage` |
    | `moved` | `move` | `from`, `to` |
    | `landed` | `merge` after `land` answers `landed` (not for a pass) | `sha`, `stage` (where the file sits on `main`: `done`, `desk-check` or `backlog`) |
    | `groomed` | `groomed` | `sha` |
    | `sent-back` | `kick_back` after it lands | `reason` |
    | `desk-check` | `advance` for a `developer` Issue; `merge` after landing a Flight whose file is now in `desk-check/` | `stage` |
    | `paused` | `pause` | `reason`, `retry` |
    | `stopped` | `work` when `stop_requested` | `reason` |
    | `empty` | `run` when nothing is ripe; `groom` when there is nothing to groom | `message` |
    | `ended` | `pair.py` `main`, once the lock is held | `outcome` |

  - `pause` takes a keyword `kind="paused"`. `advance` passes `"desk-check"`
    and `work` passes `"stopped"`. Each pause then logs exactly one event, and
    a desk check is not also logged as `paused`. A Flight's desk check doesn't
    go through `pause`, so `merge` logs it straight after its `landed`.
- `pair/pair.py`
  - Once the lock is held, wrap the outcome in `try/finally` and log `ended`
    with the outcome. That is `crashed` on an exception and `abandoned` on
    `KeyboardInterrupt`. The event is written through a small helper that
    shares `Loop.event`'s line format, so `main` doesn't depend on a `Loop`
    existing.
  - A `watch` subcommand: `--until landed | developer | flight SLUG`, with
    `nargs="+"`, checked after parsing so that only `flight` takes a slug.
    It needs no seats or `Loop`, so it goes before the `Loop` is built, next
    to `status`.
- `pair/watch.py`, new, with no dependencies:
  - `watch(repo, until, poll=0.5, out=print) -> int` holds the logic, so the
    tests call it directly.
  - Watched supervisors: for each of `run.lock` and `groom.lock`, read the
    pid in the file and keep it if the process is alive and its command line
    contains `pair.py`, and is not the watcher's own pid (it too runs
    `pair.py`, and could reuse a dead supervisor's pid). That check is
    `ps -p PID -o command=`, as `Loop.owns` already does. If none is kept,
    it returns 2 at once.
  - It reads the pid rather than probing with `flock`. A probe briefly takes
    the lock, and a supervisor starting at that moment would be refused.
    Checking the command line stops a reused pid from keeping a watcher
    alive.
  - It records the end offset of `events.jsonl` (0 if the file is missing)
    and only ever reads past it. A trailing partial line is buffered until
    its newline arrives. It prints each event as one line: `at loop kind
    slug` plus its fields.
  - Each poll first reads every whole new line and returns 0 on a match:
    `landed` for `landed`; `desk-check`, `paused` or `sent-back` for
    `developer`; `desk-check` whose slug is the Flight's for `flight`. Only
    then does it drop the supervisors that logged `ended` or whose pid is
    gone. For `developer`, an `ended` whose outcome is `desk-check` or
    `paused` also matches: `run` returns `desk-check` at once, logging
    nothing else, when the Issue or Flight underway already waits on its
    desk check. Draining first means an `ended` written just after a matching
    event never wins. When no watched supervisor is left, it returns 1.
- `justfile`: `pair-watch *args:` running `pair.py watch {{args}}`, with a
  comment line like its neighbours.
- `pair/README.md`: a section on the event log listing the kinds and fields
  from the table, and `just pair-watch` with its three conditions and exit
  codes.

### Steps

1. `Loop.event`, `event_log` and the calls in `loop.py`; the `kind` keyword
   on `pause`.
2. `ended` and the `watch` subcommand in `pair.py`; `pair/watch.py`.
3. The recipe and the README.
4. `just gate pair`, then `just gate`.

### Tests (`pair/test_pair.py`)

- `EventLogTest` on the existing `Bench`. A helper reads
  `.pair/events.jsonl` as a list of `(loop, kind, slug)`. Scripted runs
  assert the exact sequence:
  - an easy Issue: `started`, `moved` ×3 (to `todo`, `in-progress`, and
    `done` from `merge`'s retirement), `landed`;
  - a `developer` Issue: `… moved(to desk-check), desk-check`, with no
    `paused`;
  - a kick-back: `sent-back`;
  - a Flight check: `landed` (stage `desk-check`), then `desk-check`;
  - a pause on a refused landing: `paused`;
  - `stop_requested`: `stopped`;
  - an empty backlog: `empty`;
  - a grooming pass: `started`, `groomed`, all with `loop: groom`.

  Each event appears once.
- `WatchTest` calls `watch.watch` with a short poll, appends lines to
  `events.jsonl` from a thread, and stands in for a supervisor with a
  subprocess (`python -c` sleeping, with `pair.py` in its argv) whose pid is
  written to `run.lock`:
  - each condition returns 0;
  - `ended` with no match returns 1, and `ended` with outcome `desk-check`
    returns 0 under `developer`;
  - killing the subprocess with no `ended` returns 1;
  - no live pid in either lock returns 2 at once;
  - lines written before `watch` starts are ignored;
  - a line written in two pieces is read once, whole.
- The `ended` event in `pair.py`: test the helper it uses, rather than
  running the whole CLI.

### Risks

- **Duplicate events on a retry.** `merge` and `kick_back` loop on `moved`,
  and a paused merge is retried. So `landed` and `sent-back` are logged only
  after the landing succeeds, and `moved` is logged once per `git mv`
  (`move` runs once per retirement, since `retirement` answers `None` once
  moved). The once-only test covers the retry path: a landing refused once
  with `moved` must still log a single `landed`.
- **Watcher exit codes.** `watch` returns 1 and 2 here.
  `pair-exit-codes` may give them names later; this issue doesn't
  define any exit codes for the loop itself.
- **Timing in the watch tests.** Threads and subprocesses with a 0.05s poll
  and a timeout on every join, so a broken watcher fails the test rather
  than hanging it.

## Notes for the next reader

- The plan held. The differences are these:
  - `ended` is written by `supervise(repo, kind, work)` in `pair.py`, so it
    can be tested without running the CLI.
  - `stopped` carries `retry` as well as `reason`, since it goes through
    `pause`.
  - The watch tests poll every 0.02s, not the 0.05s the plan named.
  - `pair-watch` is a rendered recipe, so it is added in
    `.meta/lib/render/writers.py` and declared in the justfile contract
    (`.meta/checks/files/justfile.py`, both `CONTRACT` and
    `SCAFFOLD_RECIPES`). The `justfile` is re-rendered from those, not
    edited by hand.
- On each poll, `watch` checks which supervisors are still alive *before* it
  reads the new events. That way it reads whatever a dying supervisor wrote,
  and a matching event wins over the `ended` that follows it, with no
  second read.
- `pair/loop.py` has a baseline of no body comments (`meta/inline
  commentary`). Why only a Flight logs `desk-check` from `merge` is
  therefore explained in `merge`'s docstring.
- `AGENTS.md`'s Delivery section lists the pair recipes, so it names
  `just pair-watch` too.
- The exit codes are 0 (met), 1 (the supervisors ended first) and 2 (none
  running). `pair-exit-codes` may want to name them.
