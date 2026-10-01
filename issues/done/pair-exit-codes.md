---
difficulty: easy
parent: flight-instruments
---

# Exit codes that say what the loop did

`pair/pair.py` exits 0 whatever `Loop.run`, `Loop.groom`, `Loop.accept` or
`Loop.resume` returned: `landed`, `desk-check`, `paused`, `stopped`, `empty`,
`groomed` and the rest are only printed as `pair: <outcome>`. A session driving
the loop has to parse that line to learn what happened. The one non-zero exit
today is 1, when another process holds the run lock, and that is also the code
Python gives an uncaught exception.

## What is wanted

- `main` in `pair/pair.py` maps each outcome string the `Loop` entry points
  return to its own exit code, in one table, and exits with it: for `run`,
  `groom`, `accept` and `resume`. The strings today are `landed`,
  `desk-check`, `kicked` (from `run --once` when the Issue is sent back),
  `paused`, `stopped`, `empty` (`run`, nothing ripe), `nothing` (`groom`,
  nothing to groom), `refused` (`run --flight` it cannot work), `none` (no
  desk check to answer), `groomed`, `accepted` and `resumed`.
- The early branch in `main` that answers a Flight's desk check
  (`just pair-accept <slug>`, `just pair-resume <slug>`) and returns 0 before
  taking the lock uses the same table.
- An outcome where the loop did what it was asked and needs nothing more
  (`landed`, `groomed`, `accepted`, `resumed`) exits 0. Every other outcome
  has a distinct non-zero code. "Another process holds the lock" gets its own
  code too. No code is 1 (an uncaught exception) or 2 (argparse's usage
  error), so neither is mistaken for an outcome.
- An Issue of `difficulty: developer` reaching its desk check makes `run`
  return `desk-check`, not `paused` as `Loop.pause(..., kind="desk-check")`
  does today, and `run` still ends there rather than taking up the next Issue.
  `desk-check` then has one code whether the Issue or a Flight
  (`just pair --flight <slug>`) waits on the developer.
- An outcome string with no entry in the table fails loudly (an exception),
  not a silent 0.
- `pair/README.md` lists the codes in a table.

## Out of scope

- The event log and `just pair-watch` (`pair-event-log`). The `ended` event
  of a developer Issue's desk check will carry `desk-check` instead of
  `paused`; `watch.WAITING` already holds both, so nothing there changes.
- Changing what any other outcome means, or when it is returned.
- `status` and `watch`, which keep their exit codes.

## Done when

- Each outcome of each command exits with the code in the table; the pair
  tests check the code for each outcome, including a developer Issue reaching
  its desk check under `run`.
- `just pair`, `just groom`, `just pair-accept` and `just pair-resume` exit
  with the same code as `pair.py`.
- `pair/README.md` lists the codes, and `just gate` passes.

## The plan

1. **A developer Issue's desk check returns `desk-check`** (`pair/loop.py`).
   `Loop.pause` returns its `kind` instead of the literal `"paused"`; only
   two callers pass a `kind`: the desk check in `advance` (whose return
   value already flows up through `decide` and `work`) and the stop in
   `work`, which becomes `return self.pause(..., kind="stopped")`. In
   `run`, the tuple that ends the loop, `("paused", "stopped")`, gains
   `"desk-check"`, so `run` still stops there instead of picking the next
   Issue. `accept` and `resume` pass `work`'s outcome straight through, so
   an Issue reaching its desk check again after a failed gate returns
   `desk-check` from them too, which the table covers. Update the docstring
   of `pause`.
2. **The table** (`pair/pair.py`). A module-level `EXIT: dict[str, int]`
   beside `PROMPTS`, plus `LOCKED`:
   `landed`, `groomed`, `accepted`, `resumed` → 0; `desk-check` 3,
   `paused` 4, `stopped` 5, `kicked` 6, `empty` 7, `nothing` 8,
   `refused` 9, `none` 10; `LOCKED = 11`. 1 and 2 stay with Python and
   `argparse`. A one-line comment on the table says why 1 and 2 are
   missing. `main` prints `pair: <outcome>` as now and returns
   `EXIT[outcome]` in both places (the Flight desk-check branch and the end);
   the lock branch returns `LOCKED`. An unknown outcome raises `KeyError`
   after the line is printed, which is the loud failure the issue asks for.
3. **Tests** (`pair/test_pair.py`).
   - In `test_a_developer_issue_logs_its_desk_check_and_not_a_pause` and
     the desk-check test at line 544, the first `run()` now returns
     `"desk-check"`.
   - A new test, beside the `supervise` test, imports `EXIT` and `LOCKED`
     and checks: the set of keys is exactly the twelve outcomes listed in
     "What is wanted"; the four success outcomes map to 0; every other
     code, and `LOCKED`, is distinct, non-zero and neither 1 nor 2. The
     listed set in the test is the check that a new outcome string gets a
     row: every scenario test already asserts the outcome strings it
     drives, so a new one fails here until added.
   - An end-to-end test runs `pair.py accept` and `pair.py resume` with
     `sys.executable` in the fake repository with nothing at a desk check,
     and `pair.py accept nosuch` for the Flight branch, and asserts each
     exits `EXIT["none"]`. These need no seats, so they cover `main` itself
     and not only the table. In the same test, with the test process holding
     `run.lock` through `hold_lock` (an `flock`, so a separate process is
     refused it), `pair.py accept` exits `LOCKED`.
4. **README** (`pair/README.md`). A short `## Exit codes` section after
   "Using it": a table of outcome, code and meaning, with the lock's code,
   and a line that 1 is a crash and 2 a usage error. The `ended` row of the
   event log already says the outcome is "as `pair:` prints it"; no change
   there.
5. **By hand**: `just pair-accept; echo $?` and `just pair-accept nosuch;
   echo $?` in this repository print 10, confirming `just` passes the code
   through. Then `just gate pair`, and `just gate` before landing.

### As built

- The codes table sits under "Using it" in `pair/README.md` as
  `### Exit codes`, beside the commands it describes, not as its own `##`.
- Step 5 by hand: only `just pair-accept nosuch` was run, and it exited 10.
  A bare `just pair-accept` must not be run from inside a loop that is
  working this repository: it would meet the running loop's `run.lock`
  (exit 11) at best, and without the lock, `Loop.accept` calls `reap`,
  which stops processes left in `worktrees/pair`, the seats' own tree. The
  subprocess test in `ExitCodeTest` covers the bare form and the lock in a
  scratch repository instead.
- `kicked` is not only `run --once`'s: `accept` and `resume` hand back
  `work`'s outcome, which is `kicked` when a seat sends the Issue back. The
  README row says so.
- `watch` still exits 1 and 2, which this Issue keeps clear of crashes and
  usage errors elsewhere; `issues/backlog/pair-watch-exit-codes.md` carries
  that.

Risky: making `pause` return its `kind` changes what any future caller
passing a new `kind` gets back; the table's `KeyError` catches that at the
first run. Nothing else reads `run`'s return value except `main` and the
tests.
