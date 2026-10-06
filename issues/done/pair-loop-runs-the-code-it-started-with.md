---
difficulty: developer
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

After the restart the loop runs as `uv` → `uv` → `python`, all in the
terminal's foreground process group, so a Ctrl-C reaches the new `pair.py`
from the terminal and may reach it again if either `uv` forwards it. The
`stop` handler in `main` in `pair/pair.py` takes a second SIGINT as "abandon
the turn", so one Ctrl-C delivered twice would abandon the turn instead of
stopping after it. The restart must not change what one Ctrl-C does: if `uv`
forwards it, the re-execution has to make sure the new `pair.py` sees one
Ctrl-C once, and a test of the `stop` handler covers whatever it does.

The re-execution is a seam the `Loop` or `main` is given, as `provision` and
`deliver` are, so that a test can see it asked for without a process being
replaced. So is the fingerprint of the pair code, so that a test can change it
without touching the files under `pair/`. Where the restart seam returns, as
a test's does, the run returns without taking up the next Issue.

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

The tests replace the re-execution, so the real `os.execvp` through `uv`
is checked by hand, which is why the difficulty is `developer`. Before it
goes to `main`, the developer runs the reproduction above and sees the new
message for the second Issue. A
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

## The plan

### Seams in `Loop` (`pair/loop.py`)

`Loop.__init__` takes two more keyword-only seams, both `None` by default so
the grooming loop, `accept`, `resume` and every existing test are unchanged:

- `code_changed: Callable[[], bool] | None`: whether the pair code on disk
  differs from the code the process started with.
- `restart: Callable[[], None] | None`: re-executes the process. In
  production it never returns.

In `Loop.run`, at the bottom of the `while True`, just before `st = None`
(after the `once`/pause/stop/desk-check returns and the Flight desk-check
return, so none of those restart), add:

```python
if self.restart and self.code_changed and not self.stop_requested and self.code_changed():
    self.event("restarted")
    self.say("pair code changed; restarting")
    self.restart()
    return outcome
```

This is the one point where the loop is about to take up another Issue, and
it is reached after a landing, a sent-back Issue or a split. `work` has
already stopped the seats in its `finally`, so the exec leaves no child behind,
and `reap` in the new process handles any it misses. Returning `outcome`
(`landed`) when the seam returns keeps `EXIT` as it is: no new outcome.
`append_event` opens, writes and closes the log on each event, so the log
needs no flush of its own; `say` already prints with `flush=True`.

### The production seams (`pair/pair.py`)

- `code_fingerprint(here: Path) -> str`: SHA-256 over the sorted relative
  path and bytes of each `*.py` in `here` and each file in `here/"prompts"`.
  A test file's change also restarts the loop; that is harmless and keeps
  the rule simple.
- `reexec() -> None`: flushes `sys.stdout` and `sys.stderr`, then
  `os.execvp("uv", ["uv", "run", "--quiet", "--script", str(HERE / "pair.py"), *sys.argv[1:]])`.
  `sys.argv[1:]` carries `run` and every flag, `--flight SLUG` included. The
  working directory survives the exec, so `repo_root` finds the same
  repository.
- `main` computes `started = code_fingerprint(HERE)` first thing, before it
  reads the system prompts, and passes
  `code_changed=lambda: code_fingerprint(HERE) != started` and
  `restart=reexec` to the `Loop` only when `args.command == "run"`.

The lock needs no code: Python opens `run.lock` non-inheritable (PEP 446),
so the exec closes it and frees the `flock`; the new process takes it in
`hold_lock` or exits `LOCKED`.

### Ctrl-C (`stop` in `main`)

Measured while planning, with `uv` 0.11.29: a SIGINT sent to the process
group of `uv run --quiet --script` reached the Python script **2** times,
and **3** times once that script had re-executed itself through `uv`. `uv`
passes the signal on, so even today one group SIGINT can count as two. A
Ctrl-C from a terminal may differ from a `killpg`, which is why the
developer checks it by hand, but the handler should not depend on it.

`stop` therefore counts SIGINTs that arrive within `CTRL_C_ECHO` seconds
(0.5 s) of the last Ctrl-C it counted as that same Ctrl-C. A second Ctrl-C
after that window still abandons the turn, and its own copies are ignored
too, so they do not interrupt the `finally` blocks the abandonment unwinds
through. Pull `stop` out of `main` into a module-level
`stopper(loop, clock=time.monotonic)` that answers the handler, so a test can
call it with a fake clock.

### Watch, README

`pair/watch.py` needs no code: `restarted` is not `ended`, so `watch` keeps
the pid, and the pid stays alive (as `uv`) across the exec. Add a `restarted`
row to the event table in `pair/README.md` ("the loop working Issues finds
its own code changed on disk after an Issue and re-executes itself in
place, so the pid in `run.lock` when it started lives on as the `uv` above
the new loop; no `slug`"), and a sentence under it that a restart logs no
`ended`, so a watcher follows the loop across it. Mention the restart in the
docstring of `pair/pair.py` beside `run`.

### Order

1. `stopper` and its tests, since it is the one change that also affects the
   loop as it runs today.
2. The two seams in `Loop` and the check in `Loop.run`, with the loop tests.
3. `code_fingerprint`, `reexec` and the wiring in `main`, with the
   fingerprint test.
4. The watch test, the README row and the docstring.

### Tests (`pair/test_pair.py`)

A new `RestartTest` sets `code_changed` and `restart` on its bench's
`loop` in `setUp`, from a list of booleans popped per call (`False` once
empty) and a count of restarts; the `Bench` itself is unchanged.

- Two easy Issues (`easy_turns`), `code_changes = [True]`: `run` answers
  `landed`, `restarts == 1`, the first Issue is in `done/` on `main`, the
  second is still in `backlog/` with no seat opened for it, and the event log
  ends `landed`, `restarted` with no `ended`.
- Two easy Issues, `code_changes` empty: both land, `restarts == 0`, no
  `restarted` event.
- `code_changes = [True]` with `once=True`; and again with a seat that sets
  `stop_requested` during the first Issue's last turn: `restarts == 0`.
- `code_fingerprint` over a temporary directory changes when a `.py` or a
  prompt changes, and not when another file does.
- `WatchTest`: with a live supervisor, events `restarted` then `landed`;
  `watch("landed")` answers 0 and prints the `restarted` line. With
  `restarted` alone, `watch("flight", "big")` is still running after a few
  polls.
- `stopper`: one call sets `stop_requested`; a second within the window
  (fake clock) does nothing; a second after it raises `KeyboardInterrupt`.

### Risky

- The exec itself, through `uv`, is covered only by the developer's hand
  check (the reproduction, a watcher across the restart, one Ctrl-C after it).
- If `uv` is not on `PATH`, `os.execvp` raises and the run ends `crashed`
  after the landing has already happened; nothing is lost but the next
  Issue waits for a restart by hand. `just pair` itself needs `uv`, so this
  should not happen.
- The Ctrl-C window could swallow a deliberate double Ctrl-C pressed within
  half a second; the developer then presses it once more.
- Each restart adds one resident `uv` to the chain (`uv` → `uv` → … →
  `python`), and one more copy of each SIGINT (the 2 → 3 above), so after
  N restarts one Ctrl-C arrives N + 2 times. The `CTRL_C_ECHO` window
  absorbs them all, as long as they arrive within it. `uv` also counts its
  own nesting in `UV_RUN_RECURSION_DEPTH`, which the exec inherits and each
  restart raises by one, and `uv run` refuses to go past its limit. A run
  would need about a hundred restarts to reach it, which a loop never does.
- `VIRTUAL_ENV`, which the first `uv` sets to the script's environment, is
  inherited by the exec. `uv run --script` builds the script's own
  environment regardless, so a changed dependency header still takes effect.
  The developer's hand check should confirm this once, by checking that the
  restarted process imports the landed code.
- With `stop_requested` set when a landing happens, the plan's check skips
  the restart and the loop goes on round its `while True`, as it does today:
  `start` takes up the next Issue, and `work` pauses it at once with
  `stopped by the developer`. That is today's behaviour, which this Issue
  leaves alone.

## Pair notes

> **primary, backlog turn 1**
>
> The Issue was already precise enough to plan, so I left its difficulty at `medium` and added one paragraph to it.
>
> **What I checked.** I compared the Issue's claims against the code and they hold:
> - `Loop.run` in `pair/loop.py` loops with `while True` and returns early on `once`, a pause, a stop request or a desk check.
> - `HERE`, `LOCKED`, `hold_lock`, and `ended` being logged in the `finally` of `supervise` are all in `pair/pair.py` as described.
> - In `pair/watch.py`, `running` looks for `pair.py` in the process's command line, and `watch` only reports that the loop ended first once every pid it is watching has gone.
> - The `pair` recipe runs `uv run --quiet --script pair/pair.py run`, so re-executing in place leaves the original pid alive as `uv`, and its command line still names `pair.py`.
>
> **What I added.** The "Wanted" section now says that the pair code's fingerprint is a seam as well as the restart. That lets a test change the fingerprint without editing files under `pair/`. It also says that if the restart seam returns, as a test's would, the run ends without taking up the next Issue. Without that, the planned tests couldn't show that "the second Issue is not started in the same process".

> **secondary, backlog turn 2**
>
> I checked the Issue against the code and its claims are accurate, including how `watch` follows the loop's pid and how the lock is released and taken again. I made two changes and committed them:
>
> - **Ctrl-C after a restart.** Once the loop restarts itself, it runs as `uv` → `uv` → `python`, and all three are in the terminal's foreground process group. A single Ctrl-C reaches the new `pair.py` from the terminal, and may reach it a second time if either `uv` passes it on. The `stop` handler in `main` in `pair/pair.py` treats a second SIGINT as "abandon the turn", so one Ctrl-C could abandon the turn instead of stopping after it. The Issue now requires that one Ctrl-C does the same thing after a restart as before, and that a test of the `stop` handler covers whatever the fix does. I didn't confirm whether `uv` actually passes the signal on; the implementer needs to find out.
> - **Difficulty raised from `medium` to `developer`.** The tests replace the real restart with a stand-in, so the actual restart through `uv` is never run by any test. The Issue now says the developer runs the reproduction by hand before it goes to `main`.

> **primary, backlog turn 3**
>
> I'm leaving the Issue as it stands; my partner's two changes are right.
>
> - **Ctrl-C after a restart.** The worry is real. The `stop` handler in `main` in `pair/pair.py` treats a second SIGINT as "abandon the turn". After a restart, each `uv` layer might pass the signal on, so one Ctrl-C could arrive twice. The Issue now says what must not change, and that a test of the handler must cover it; it leaves it to whoever implements it to find out whether `uv` actually passes the signal on.
> - **`developer` difficulty.** Agreed. The tests use a stand-in for the restart, so the real one (`os.execvp` through `uv run --script`) only gets checked when the developer runs the reproduction by hand before it goes to `main`.

> **primary, todo turn 1**
>
> I wrote `## The plan`. The loop gets two seams, `code_changed` and `restart`, and checks them at the bottom of `Loop.run`, just before it takes up the next Issue. In production, `main` gives it a SHA-256 fingerprint of `pair/*.py` and `pair/prompts/`, and an `os.execvp` through `uv run --quiet --script` with the same arguments. `pair/watch.py` needs no change; the README gains a `restarted` event.
>
> While planning I checked the Ctrl-C worry. With `uv` 0.11.29, one SIGINT sent to the process group reached the script 2 times under `uv run --script`, and 3 times after it re-executed itself through `uv`. So the plan also makes the `stop` handler count SIGINTs within 0.5 s of the first as one Ctrl-C, and tests that with a fake clock. A Ctrl-C from a real terminal may behave differently, which the developer's hand check covers.

> **primary, todo turn 1**
>
> I've written `## The plan` in `issues/todo/pair-loop-runs-the-code-it-started-with.md` and committed it; nothing is implemented yet.
>
> **How the restart works**
> - **In the loop:** `Loop` in `pair/loop.py` gets two new seams, `code_changed` and `restart`, both off by default. `Loop.run` checks them at one place: just before it takes up the next Issue. If the pair code has changed and no Ctrl-C is pending, it logs a `restarted` event, prints "pair code changed; restarting" and calls `restart`. The `--once`, pause, stop and desk-check exits all return before that check, so none of them restart.
> - **In `pair/pair.py`:** a new `code_fingerprint` takes a SHA-256 of `pair/*.py` and `pair/prompts/`. A new `reexec` flushes output and replaces the process with `uv run --quiet --script …/pair.py` and the same arguments, so `--flight` survives. `main` takes the fingerprint at start and passes both seams only to `run`.
> - **No code needed** for the lock, which the exec frees and the new process takes again, or for `pair/watch.py`. The README's event table gets a `restarted` row.
>
> **Ctrl-C needs fixing too.** I tested how `uv` 0.11.29 passes on a signal sent to its whole process group. A script under `uv run --script` received it twice, and three times after re-executing itself through `uv`. Since the `stop` handler treats a second SIGINT as "abandon the turn", one such signal can already abandon the turn instead of stopping after it, even before this change. The plan moves `stop` out of `main` into a testable function and has it count SIGINTs within 0.5 s of the first as one Ctrl-C. A Ctrl-C typed at a real terminal may behave differently from my test, so the developer's hand check still covers it.
>
> **Order:** the Ctrl-C fix first, then the seams in the loop, then the production wiring, then the watch test and the README.
>
> **Tests in `pair/test_pair.py`:**
> - a restart after the first of two Issues, with the second never started and no `ended` logged;
> - no restart when the code is unchanged, with `--once`, or when a stop has been asked for;
> - the fingerprint changes when a `.py` file or a prompt changes, and not for other files;
> - `watch` keeps following the loop across a `restarted` event;
> - the Ctrl-C window, tested with a fake clock.
>
> **Risks:**
> - No test runs the real exec; only the developer's hand check does.
> - If `uv` were missing from `PATH`, the run would crash right after a landing. `just pair` itself needs `uv`, so that shouldn't happen.
> - A deliberate double Ctrl-C pressed within half a second would count as one, so the developer would have to press it again.

> **secondary, todo turn 2**
>
> I checked my partner's plan against `pair/loop.py` and `pair/pair.py`, and it holds. The check sits where the plan says, after every `once`, pause, stop and desk-check return in `Loop.run`. The seats are stopped in the `finally` of `work` before the restart. `say` already flushes its output, and each event is written to the log and closed straight away. I left the plan as written and added three risks to its "Risky" section, committed:
>
> - **Each restart adds one more `uv` that stays running.** A loop started by `just pair` runs as `uv` → `python`. Each restart turns the running `python` into another `uv` above the new `python`, so the chain grows by one `uv` per restart. Going by my partner's measurement, one Ctrl-C would then arrive one more time per restart, and the plan's half-second Ctrl-C window has to catch every copy. `uv` also counts how deeply it is nested in `UV_RUN_RECURSION_DEPTH`; I confirmed it sets that variable, and a restart inherits it. I believe `uv run` stops at about 100 levels, but I didn't check that limit; a loop won't restart that often anyway.
> - **`VIRTUAL_ENV` from the first `uv` carries over into the restart.** I confirmed `uv` sets it. `uv run --script` should still build the script's own environment, so a changed dependency header should still take effect, but I didn't test that. I added a note asking the developer to confirm it once during the hand check.
> - **A Ctrl-C pressed during an Issue's last turn.** With a stop already asked for when the landing happens, the plan's check skips the restart. The loop then does what it does today: it takes up the next Issue and pauses it straight away with "stopped by the developer". The plan keeps that behaviour unchanged.

> **primary, todo turn 3**
>
> I'm leaving the plan as it stands. My partner's three additions to the "Risky" section are sound, and none of them changes the plan:
>
> - **The `uv` chain grows by one per restart.** That follows from my own measurement: one signal reached the script 2 times under `uv`, and 3 times after one restart. Each restart therefore delivers one more copy of every Ctrl-C, and the planned half-second window in the `stop` handler catches all of them. No real run restarts often enough to reach `uv`'s nesting limit.
> - **`VIRTUAL_ENV` carries over into the restarted process.** Whether `uv run --script` still builds the script's own environment is untested, so asking the developer to confirm it during the hand check is the right place for it.
> - **A Ctrl-C during an Issue's last turn.** Skipping the restart when a stop has been asked for is what the Issue's "Wanted" section requires. What follows is unchanged from today: the loop takes up the next Issue and pauses it straight away.

> **primary, in-progress turn 1**
>
> Implemented as planned. `pair/pair.py` gains `code_fingerprint`, `reexec`, `CTRL_C_ECHO` and `stopper` (the old inline `stop` handler, now ignoring a SIGINT within 0.5 s of the first). `main` takes the fingerprint before it reads the prompts, and gives `restart=reexec` only to `run`. `Loop` in `pair/loop.py` takes `code_changed` and `restart`; `Loop.run` calls `stale` just before `st = None`, and on a change logs `restarted`, says `pair code changed; restarting`, calls `restart` and returns the last outcome. `pair/README.md` has a `restarted` row in the event table, and a paragraph on watching across a restart and on the Ctrl-C window.
>
> Where it differs from the plan: the tests set the two seams on the bench's loop in `RestartTest.setUp` instead of adding fields to `Bench`. `Loop.run` went over ruff's branch limit, so its existing `noqa` now names `PLR0912` too, with the same reason.
>
> Tests in `RestartTest`: a restart after the first of two Issues, with the second untouched and `restarted` as the last event, with no `ended`; no restart when the code is unchanged; none with `--once` or after a stop; the fingerprint following `.py` files and prompts but not the README; and `stopper` with a fake clock. `WatchTest.test_a_restarted_supervisor_is_still_watched` covers the watcher, though `WatchTest` is skipped in my sandbox because it cannot run `ps`. The `pair` gate passed here (275 tests), so that test is left to the supervisor's gate.
>
> Still for the developer by hand, as the Issue says: the real exec through `uv` (the reproduction), a watcher across the restart, and one Ctrl-C from a real terminal after it.

> **primary, in-progress turn 1**
>
> I've implemented the restart and committed it. `just gate pair` passed (275 tests) and `just gate meta` passed. The new test of `pair-watch` (`WatchTest`) is skipped in my sandbox because it can't run `ps`, so it's left to the supervisor's gate. The real restart through `uv` has not been run at all; that stays for the developer's hand check, as the Issue says.
>
> **What changed**
> - **`pair/pair.py`:**
>   - `code_fingerprint` hashes `pair/*.py` and `pair/prompts/`.
>   - `reexec` flushes output and replaces the process with `uv run --quiet --script …/pair.py`, passing the same arguments.
>   - `main` takes the fingerprint at start and gives the restart only to `run`.
> - **Ctrl-C:** the SIGINT handler that was inline in `main` is now `stopper`. It ignores any SIGINT that arrives within 0.5 s (`CTRL_C_ECHO`) of the first, because `uv` passes one Ctrl-C on as more than one signal.
> - **`pair/loop.py`:** `Loop` takes two new seams, `code_changed` and `restart`. Just before it takes up the next Issue, `Loop.run` checks whether the code changed and no stop has been asked. If so, it logs `restarted`, prints "pair code changed; restarting" and calls `restart`.
> - **`pair/README.md`:** a `restarted` row in the event table, and a paragraph on how `pair-watch`, the lock and Ctrl-C behave across a restart.
>
> **Tests in `pair/test_pair.py`**
> - **`RestartTest`:**
>   - When the code changes, the loop restarts after the first of two Issues. The second Issue is never started, `restarted` is the last event logged, and no `ended` is logged.
>   - There is no restart when the code is unchanged, with `--once`, or after a Ctrl-C.
>   - The fingerprint changes when a `.py` file or a prompt changes, and not for other files.
>   - The Ctrl-C window, tested with a fake clock.
> - **`WatchTest`:** `pair-watch` keeps following the loop across a `restarted` event.
>
> **Differences from the plan** (both recorded in the Issue file)
> - The tests set the two seams on the test loop directly instead of adding fields to the shared test bench.
> - `Loop.run` went over the linter's branch limit, so its existing lint exception now covers that rule too, with the same reason.
>
> **Still for the developer to check by hand before `main`:**
> - the reproduction, which runs the real restart through `uv`;
> - a `pair-watch` started before the restart still following the loop after it;
> - one Ctrl-C from a real terminal after the restart stopping the loop after its current turn, not abandoning the turn.

> **secondary, in-progress turn 2**
>
> I fixed one bug in my partner's implementation and corrected the README; the rest checked out against the plan. `just gate pair` (275 tests) and `just gate meta` pass, and the change is committed.
>
> - **Bug in the Ctrl-C handler (`stopper` in `pair/pair.py`).** It ignored repeat SIGINTs only after the first Ctrl-C. The second Ctrl-C, the one that abandons the turn, also arrives through `uv` as several signals. Each extra copy raised `KeyboardInterrupt` again while the loop was shutting down. That could break into the cleanup that stops the seats, or into the step that logs `ended`. Now any SIGINT within 0.5 s of the last Ctrl-C the handler counted is ignored, including copies of the abandoning one. The existing `stopper` test now also checks that such a copy does nothing.
> - **README wording.** The `restarted` row in `pair/README.md` said the loop keeps its pid. In fact the new `pair.py` gets a new pid, and the original pid lives on as a `uv` process above it. That is why `just pair-watch` keeps following the loop, and the row now says so.
>
> The plan section and the notes in the Issue file are updated to match. The new `pair-watch` test in `WatchTest` is skipped in our sandbox because it can't run `ps`, so it is left to the supervisor's gate.
>
> No test runs the real restart through `uv`. The developer still has to check three things by hand before this goes to `main`:
> - the reproduction in the Issue;
> - that a `just pair-watch` started before the restart is still following the loop after it;
> - that one Ctrl-C from a real terminal after the restart stops the loop after its current turn instead of abandoning it.

> **primary, in-progress turn 3**
>
> My partner's `stopper` fix is right: copies of the abandoning Ctrl-C must not raise again inside the `finally` blocks. I carried their pid correction into the two places that still said the pid "stays": the docstring of `reexec` in `pair/pair.py`, and the paragraph under the event table in `pair/README.md`. The plan's "Watch, README" section now says the same. I also removed a duplicate of their turn-2 note. The `pair` and `meta` gates pass; `WatchTest` is still left to the supervisor's gate, since this sandbox cannot run `ps`.

> **primary, in-progress turn 3**
>
> My partner's fix to the Ctrl-C handler (`stopper`) is right, and I kept it. Before, extra copies of the second Ctrl-C, the one that abandons the turn, could raise `KeyboardInterrupt` again while the loop was shutting down. That could break into the cleanup that stops the seats, or into logging `ended`. The handler now ignores them.
>
> **What I changed**
> - **The pid wording.** My partner corrected the README row: after a restart the new `pair.py` gets a new pid, and the original one lives on as the `uv` above it. Two places still said the pid "stays":
>   - the docstring of `reexec` in `pair/pair.py`;
>   - the paragraph under the event table in `pair/README.md`.
>
>   Both now match the corrected row. So does the plan's "Watch, README" section in the Issue file.
> - **The Issue file** had my partner's turn-2 note twice, so I removed the shorter copy.
>
> `just gate pair` (275 tests) and `just gate meta` both pass, and the change is committed. The new `pair-watch` test (`WatchTest`) is skipped here because this sandbox can't run `ps`, so it is left to the supervisor's gate. The developer still has to check the real restart through `uv` by hand before this goes to `main`.

> **secondary, in-progress turn 4**
>
> I'm leaving this turn's changes as they are. My partner's pid corrections to the docstring of `reexec` in `pair/pair.py` and to the paragraph under the event table in `pair/README.md` are accurate, and they match the corrected `restarted` row. I found nothing else to fix in the implementation or the Issue file, so I didn't rerun the gates.
>
> The developer still has to check the real restart through `uv` by hand before this goes to `main`.

Gated by the supervisor at 13:05: `meta`, `pair`; 97 steps passed.
