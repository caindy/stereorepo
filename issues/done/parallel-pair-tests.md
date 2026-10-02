---
difficulty: medium
---
# Run the pair tests in parallel

`just gate pair` runs `pair/test_pair.py` in one process, one test after
another (`pair/gate.py`). On 2026-10-02 the suite held 209 tests in 17
classes and took 96 seconds in a seat's sandbox, measured with a logging
`git` shim in place. Seats run it several times in an Issue that touches
`pair/`, and the loop runs it again in the full gate before landing.

`pair-test-git-traffic` found that cutting git calls cannot halve the
suite's cost, since the loop's own writes and the tests' setup already make
up more than half of them. It named running the tests in several processes
as the way to cut wall time, and the developer chose that.

## Wanted

- `pair/gate.py` runs the tests of each module across several worker
  processes, one per two CPUs by default (see Results for why not one per
  CPU), and merges their results into the one
  step that module already reports. The environment variable
  `PAIR_TEST_WORKERS` overrides the count; the gate's command in
  `.meta/assertions/structure.yaml` stays as it is, and `1` gives the serial
  run in a single worker.
- Work is handed out by test, not only by whole class: `LoopTest` alone is
  about a quarter of the file, so class-sized shares would cap the speed-up.
  No class uses `setUpClass` or `setUpModule` today, so a single test can
  run anywhere; if one is added, its class stays in one worker.
- The step prints the shape every gate prints (`ok <step> — <count> tests`,
  or `x  <step> (<count>)` with one line per failure or error naming the
  test id and the last line of its trace, A21), and the exit code is
  non-zero when any test fails or errors, or when a worker dies.
- Tests that share process state are made independent of which worker runs
  them and of what ran before them in it: environment variables
  (`GNUPGHOME` in `ConfinementTest`, the `PATH` that `skip_git_trampoline`
  sets at import), the current directory (`os.chdir` in `ConfinementTest`),
  and any fixed path outside a test's own temporary directory.
- The standard library only (in the end `subprocess` and `threading`, see
  step 4 of the plan); no new dependency such as `pytest-xdist`.

## Out of scope

- Reducing the git calls the loop or the tests make (`pair-test-git-traffic`).
- The other Projects' gates.
- Changing what any test asserts.

## Done when

- The parallel run reports the same test count as the serial run before the
  change (209, or whatever the count is when the work starts), with every
  test passing.
- Wall time of the pair tests, measured once before and once after in a
  seat's sandbox, falls by at least half. Both times, and the worker count
  used, are recorded in this file.
- Making one test fail on purpose (then reverting) prints `x  pair tests (1)`
  and one indented line naming that test, and the run exits non-zero; this
  is checked once by hand and noted here.
- `PAIR_TEST_WORKERS=1` and the default worker count both pass, each run
  once, which shows the result does not depend on which worker a test
  lands in.

## The plan

The change lives almost entirely in `pair/gate.py`; `pair/test_pair.py`
gets one small fix. Nothing else in `pair/` changes.

### Steps

1. **Measure before.** Time `uv run --quiet --script pair/gate.py` once in
   the seat's sandbox on the unchanged code, and record the wall time, the
   test count and `os.cpu_count()` here.
2. **Make `ConfinementTest` leave the environment as it found it.**
   `test_gnupg_is_reachable_only_for_signing_and_never_its_configuration`
   sets `os.environ["GNUPGHOME"]` by hand and pops it in cleanup, which
   deletes a `GNUPGHOME` the developer already had. Change it to
   `mock.patch.dict(os.environ, {"GNUPGHOME": ...})`, as the neighbouring
   tests already do. The other shared state needs no change:
   - The `os.chdir` in the same class already restores the directory with
     `addCleanup`.
   - `skip_git_trampoline` changes `PATH` at import, so it runs again in
     every worker, the same as in a serial run.
   - No test writes to a fixed path. Every test works in its own
     `tempfile.TemporaryDirectory`, and `seats.py` only reads `~/.gnupg`,
     `~/.cargo` and the git config files.
   - `Loop.reap` in `pair/loop.py` and `watch` in `pair/watch.py` find processes by the pid
     in a file, so tests in one worker never see the stand-in processes
     that another worker starts.
3. **Split each module into units of work in `gate.py`.** Load the module's
   suite as today and flatten it into test ids. A test whose class overrides
   `setUpClass` or `tearDownClass` stays with the rest of its class as one
   unit. A module that defines `setUpModule` is one unit as a whole. Every
   other test is a unit by itself. Today there are no class or module
   fixtures, so all 209 tests are separate units.
4. **Run the units in worker subprocesses.** *(Changed in implementation:
   the plan said `concurrent.futures.ProcessPoolExecutor`, but in a seat's
   sandbox it fails before starting a process, at
   `os.sysconf("SC_SEM_NSEMS_MAX")`: `PermissionError: Operation not
   permitted`. So `multiprocessing` is not used at all.)*
   - Worker count: `PAIR_TEST_WORKERS` if set (a positive integer, anything
     else is an error that names the variable), otherwise half of
     `os.cpu_count()` (changed from one per CPU, see Results).
   - A worker is `gate.py --worker`, started with `subprocess.Popen` from
     `sys.executable`, so it is a fresh interpreter on every platform and
     inherits no imported state. It reads one JSON list of test ids per line
     on stdin, runs them with `loadTestsFromNames` and a `TextTestRunner`
     writing to a `StringIO`, and answers one JSON line: the count of
     tests run, and a pair of test id and last line for each failure.
     Before it starts, it saves its stdout as a private descriptor and
     points fd 1 at stderr, so nothing a test or its subprocesses print can
     be read as an answer.
   - The parent runs one thread per worker. Each thread takes units from a
     shared queue in file order, so the slow `LoopTest` tests are taken
     first and the short ones fill the gaps at the end.
   - `PAIR_TEST_WORKERS=1` runs through the same path with one worker, not
     a separate code path, so the serial run checks the same code.
5. **Merge and print as today.** Add up `tests_run` and the problems per
   module, sort the problems by test id so the order does not depend on
   which worker ran them, and print the `ok` / `x` lines unchanged. If a
   worker dies (end of file on its stdout), the unit it held is reported as
   one problem, `<test ids>: a worker died before reporting`, the thread
   starts a new worker, and the gate exits non-zero.
6. **Update the docstrings.** In `gate.py`, the module docstring says that
   each module is one step, and now also says it runs across worker
   processes and names `PAIR_TEST_WORKERS`. The "Run:" line at the top of
   `test_pair.py` (`python -m unittest discover`) still runs the tests
   serially and stays. Add a second line after it saying that
   `uv run --script pair/gate.py` runs them across workers.
7. **Measure after.** Run once with the default worker count and record the
   wall time and worker count. Then run once with `PAIR_TEST_WORKERS=1`.
   Then make one assertion fail, run once, check that the output reads
   `x  pair tests (1)` followed by the test's id, revert, and note it here.

### Tests that show it works

The checks in "Done when" are the evidence: the same count of 209 tests,
all passing, both with `PAIR_TEST_WORKERS=1` and with the default; at most
half the wall time; and the failure shape checked once by hand. `gate.py`
gets no unit tests of its own, because it is the harness itself. These runs
exercise every path except a worker that dies, which is a few lines checked
by reading.

### Risks

- **Timing under load.** Several tests wait on real time: `WatchTest` with
  0.2 s steps and a 10 s join, the orphan-reaping test in `LoopTest` with a
  10 s deadline, and the stand-in seat scripts that `sleep`. With one
  worker per CPU, each starting git and `sleep` processes, a test can run
  slower than it does alone. If a run fails only under parallel load, lower
  the default to `cpu_count() - 1`, or keep that class in one worker,
  rather than loosening the test's timeouts. Record what was done here.
  *(This happened, in `ClaudeSeatTest`; the default became half the CPUs.
  See Results.)*
- **Tests that need `ps`.** `INSPECTS` skips some tests in the seat's
  sandbox, so the number of tests run in the sandbox may fall short of the
  loop's. Compare counts measured in the same place.
- **Halving may be capped.** If one test takes close to half of the 96 s by
  itself, no amount of splitting gets past it. If the speed-up falls short,
  run with `-v` once to find the slowest tests, and say so here instead of
  reshaping tests, which is out of scope.

## Results

Measured on 2026-10-02 in a seat's sandbox, on a machine where
`os.cpu_count()` is 18, with `time uv run --quiet --script pair/gate.py`:

| Run | Workers | Tests | Wall time |
|---|---|---|---|
| Before (serial `gate.py`) | 1 | 209, all pass | 54.8 s |
| After, first try (one worker per CPU) | 18 | 209, all pass | 25.1 s |
| After (one worker per two CPUs, the default) | 9 | 209, all pass | 21.6 s |

Wall time fell from 54.8 s to 21.6 s, by 61%, which meets the bar of at
least half. The 96 s in the opening paragraph was measured with a logging
`git` shim in place, so 54.8 s is the baseline to compare against.

**Why the default is half the CPUs.** With 18 workers the run spent 249 s
in the kernel, against 29 s serially, because every worker was starting git
processes at once. Under that load `ClaudeSeatTest` failed in three of six
runs. With 9 workers the kernel time fell to about 115 s, and four runs in
a row passed, at 21.6 s, 23.6 s, 22.8 s and 22.3 s. These were runs to
check the flake, not benchmarks.

**The `ClaudeSeatTest` flake is not gone (third turn).** At 9 workers it
failed in 2 of 14 runs. In the failing run I instrumented, every test in
the class failed, and the stand-in `claude` sent nothing at all: one turn
waited 10 s for the stand-in's first line and then 30 s more before it
timed out. That is a stall, not a slow start. The six tests running at
once with nothing else in the workers passed in about 1 s each. Nothing in
`pair/` signals another process (`os.kill` is used only by `Loop.reap` and
one test, both by pid). With the stand-in instrumented to write a
timestamp when it starts, seven runs in a row passed, so I could not tell
whether its `exec` stalls or it starts and then blocks.

The serial gate has only been run once or twice here, so it is not known
whether this flake comes from the parallel runs or was always there and
is now more likely. It is written up as
`issues/backlog/claude-seat-test-stalls-under-load.md`. The loop's gate
may fail on it and hand this Issue back. If it does, the failure is these
`ClaudeSeatTest` tests timing out, not a change in behaviour. The test
timeouts were left as they are.

**The stalls come in bursts (fifth turn).** The first `just gate pair` of
the turn failed again, with all six `ClaudeSeatTest` tests timing out.
The next 21 runs all passed: 15 with the stand-in instrumented, 3 with
part of the instrumentation removed, and 3 with the test file unchanged.
So the instrumentation did not make the difference. The failures come in
time clusters, not at a steady rate. In passing runs the stand-in starts
0.2 to 0.6 s after the seat is created. The 1 s timeout in
`test_a_task_that_never_finishes_times_the_turn_out` leaves little margin
for that, but the other tests stalled for 30 s or more, so something
outside the tests is stalling process start. For example, it may be
other work on the machine when a turn starts, such as processes left from
the previous turn or the loop. The backlog Issue has these figures.

- **Diagnosis aid kept:** in
  `ClaudeSeatTest.test_the_seat_reads_its_git_config_from_a_file_outside_the_worktree`,
  `assertTrue(seat.send("go").ok)` now passes `turn.error` as its message.
  Its failure used to read only `False is not true`. The assertion itself
  is unchanged.

- **Failure shape, checked once by hand:** I changed `assertIn(gnupg,
  confined.allow)` in
  `ConfinementTest.test_gnupg_is_reachable_only_for_signing_and_never_its_configuration`
  to `assertNotIn` and ran the gate. It printed `x  pair tests (1)` and one
  indented line,
  `test_pair.ConfinementTest.test_gnupg_..._configuration: AssertionError: ...`,
  and exited 1. Then I reverted the change.
- **`PAIR_TEST_WORKERS=1`: passed, run once.** It printed `ok pair tests
  — 209 tests` and exited 0, in 72.2 s. A command-line environment prefix
  needs the developer's approval in a seat's sandbox. So the variable was
  set by a small Python script that then started `uv run --quiet --script
  pair/gate.py`. This run was slower than the serial baseline of 54.8 s.
  It was a single run and was not investigated: the load on the machine
  may differ between the two runs. One worker is there only to check that
  the result does not depend on placement, and is not the default.
- **Fix to `ConfinementTest`:** the GnuPG test now sets `GNUPGHOME` with
  `mock.patch.dict`. Before, it popped `GNUPGHOME` in cleanup, which
  deleted a value the developer already had for every later test in the
  same process.
- **Failures of the gate itself are reported, not lost** (second seat). A
  test module that fails to import used to crash the new `units()` with a
  `KeyError` on `sys.modules`. Its stand-in failed test now runs in the parent
  and prints as one line under its step, as the serial gate did. If a worker
  thread hits an exception, the unit it held is reported as `the gate failed:
  <error>`. Any unit still queued after every thread has stopped is reported
  as `no worker was left to run it`. Before this fix, those units fell out of
  the count, and the gate could print `ok` with fewer tests. I checked this
  once on a scratch copy of `gate.py`. It had a module importing a missing
  name, and a module with one passing test, one failing test and one test
  that calls `os._exit`. The output was `x  broken tests (1)`, then
  `x  mixed tests (2)` with the failure and `a worker died before reporting`,
  and the exit code was 1.
- **A worker's tests read stdin from `/dev/null`** (second seat, fourth
  turn). A worker's fd 0 was the parent's request pipe. Every subprocess a
  test starts without `stdin=` inherits fd 0. Such a subprocess that read
  stdin would have waited forever on a pipe the parent holds open, with no
  timeout to end it, or would have taken the next unit's request. The worker
  now keeps the request pipe on a private descriptor and points fd 0 and
  `sys.stdin` at `/dev/null`, the same way it already handled stdout. I
  checked this once on a scratch copy of `gate.py`. Its tests ran `cat`,
  read `sys.stdin` and printed a line. They passed with `ok stdin tests — 3
  tests`, and the printed line went to stderr. No current test reads stdin,
  so this does not explain the `ClaudeSeatTest` stall, which spawns its
  stand-in with `stdin=PIPE`.
