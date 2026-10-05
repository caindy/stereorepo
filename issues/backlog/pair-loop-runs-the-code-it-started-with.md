---
difficulty: medium
---

# The pair loop runs the pair code it started with

Found while grooming `seat-shell-rustc-wrapper-returns`. `just pair` imports
`pair/` once and carries Issue after Issue to `main` in the same process:
`Loop.run` in `pair/loop.py` goes round its `while True` to the next ripe
Issue after each landing. Nothing re-executes or reloads it after a landing,
so a change to `pair/` that lands, such as `UNSET_FOR_SEATS` in
`pair/seats.py` gaining `RUSTC_WRAPPER` in `3f92bfe9`, has no effect on the
running loop. The seats that follow keep hitting the problem the change fixed
until the developer restarts the loop, and nothing tells the developer that a
restart is needed.

What goes stale is everything read once at start-up: the modules `pair.py`
imports (`loop`, `board`, `seats`, `gate`, `touched`, `watch`), and the seats'
system prompts `pair/prompts/primary.md` and `pair/prompts/secondary.md`,
which `main` in `pair/pair.py` reads before it builds the `Loop`. The stage
prompts are read again at each turn and do not go stale.

The landing fast-forwards the developer's checkout, so the landed code is
already on disk; only the process is old. In a product repository the loop's
code lives in a stereorepo checkout outside the repository it works (the
docstring of `pair/pair.py`), and a developer who updates that checkout while
the loop runs leaves it just as stale.

## How to reproduce

1. Put two easy Issues in `issues/backlog/` of stereorepo, the first of which
   changes a message the loop prints, such as the `landed …` line `merge` in
   `pair/loop.py` says.
2. Run `just pair`.
3. After the first Issue lands, the checkout holds the new message, but the
   loop prints the old one when the second Issue lands.

## Wanted

After a landing, and before it takes up the next Issue, `just pair` checks
whether the pair code it is running has changed on disk since it started: the
`.py` files and `prompts/` of the directory `pair.py` was loaded from (`HERE`
in `pair/pair.py`). If it has, the loop re-executes itself with the same
arguments, through `uv run --script` so that a change to the script's
dependency header is honoured too, and carries on with the next Issue on the
landed code. If it has not, the loop carries on in the same process, as now.

- The restart says so on the terminal (for instance `pair code changed;
  restarting`) and logs an event of its own to `.pair/events.jsonl`. It does
  not log `ended`.
- `just pair-watch` keeps following a loop that restarted itself, and does not
  report that the loop ended first. A watcher waiting `--until landed` is
  already satisfied by the landing before the restart.
- The restarted process takes `run.lock` again. If another `just pair` took it
  in between, the restarted process says so and exits with `LOCKED`, as any
  second loop does; two loops never run at once.
- No restart happens when the run would end anyway: with `--once`, after a
  Ctrl-C has asked the loop to stop (`stop_requested`), or when the run ends
  at a desk check, a pause or an empty backlog.
- `--flight SLUG` and the other flags survive the restart, so a Flight run
  stays a Flight run.
- The developer's checkout can refuse the landing's fast-forward (`merge` in
  `pair/loop.py` warns `could not fast-forward …`). The landed code is then
  not on disk, so the fingerprint is unchanged and no restart happens. That is
  correct: the restart follows what is on disk, not what is on `main`.

The re-execution replaces the process in place (`os.execvp`), and does not
start a child process and exit. The pid stays the same, so the facts below
hold without changes to `pair/watch.py`:

- A watcher remembers the pid it read from `run.lock` when it started, and
  stops watching once `running` in `pair/watch.py` finds that pid gone. The pid
  outlives the restart, and its command line (`uv run --script …/pair.py`)
  still names `pair.py`. `uv` runs the new `pair.py` as its child, under a new
  pid, which `hold_lock` writes to `run.lock`; the old pid stays alive as that
  `uv` until the child exits, so both the earlier watcher and one started after
  the restart follow the loop to its end.
- The `ended` event is logged by the `finally` of `supervise` in
  `pair/pair.py`. An exec does not unwind it, so no `ended` is logged.
- Python opens the lock file close-on-exec, so the exec releases `run.lock`
  and the new process takes it again through `hold_lock`.

Flush stdout and the event log before the exec, so nothing written just
before it is lost.

The re-execution is a seam the `Loop` or `main` is given, as `provision` and
`deliver` are, so that a test can see it asked for without a process being
replaced.

## How anyone will know it is done

Tests in `pair/test_pair.py`, on the existing fake-seat bench:

- A run over two Issues whose first landing changes the pair code fingerprint
  asks for a restart after the first landing, and does not start the second
  Issue in the same process.
- A run over two Issues whose landings leave the pair code alone works both
  without asking for a restart.
- With `--once`, or with `stop_requested` set, a landing that changes the
  pair code ends the run as it does now, without a restart.
- The restart logs its event and no `ended`, and `watch` given that log and a
  live lock holder keeps watching instead of returning `ENDED_FIRST`.

The reproduction above prints the new message for the second Issue. A
`just pair-watch --until developer` started before the first landing is
still following the loop after the restart. One Ctrl-C after the restart
still stops the loop after its current turn.

## Out of scope

- `just groom`, `just pair-accept` and `just pair-resume`, each of which ends
  after its one piece of work and so picks up landed code on its next run.
- Reloading modules in place with `importlib.reload`, which leaves old
  objects referring to old code; a fresh process is the unit of reload.
- Restarting in the middle of an Issue. The turn that changes `pair/` runs on
  the old code to the landing, and only the next Issue runs on the new code.
- Telling seats or the developer which change caused the restart.
