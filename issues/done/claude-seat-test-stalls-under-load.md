---
difficulty: medium
---

# ClaudeSeatTest's stand-in claude stalls under load

`ClaudeSeatTest` in `pair/test_pair.py` runs `ClaudeSeat` against a stand-in
`claude`. The stand-in is a Python script written to a temporary `bin/` with
a `#!{sys.executable}` line, made executable, and put first on `PATH`
(`ClaudeSeatTest.setUp`); `pair/seats.py` starts it by the bare name
`claude` in its argv. While `parallel-pair-tests` was in progress, the gate
ran the tests across 9 worker processes on an 18-CPU machine, inside a
seat's sandbox. There, every test in the class sometimes failed together,
in 2 of 14 runs:

- The stand-in wrote nothing to stdout for 40 s: a 10 s wait for its first
  line, then the 30 s turn timeout.
- `test_a_task_that_never_finishes_times_the_turn_out` reported
  `turn timed out after 1s` with no `t9` task seen.

The same six tests, run at the same time with no other tests alongside,
passed in about 1 s each. Seven runs with the stand-in instrumented to write
a timestamp at start all passed, so the stall was not caught in the act.

Later the same day the failures were seen to come in time clusters. The
first run of a seat's turn failed with the whole class timing out, and the
next 21 runs, with and without instrumentation, all passed. In passing
runs the stand-in starts 0.2 to 0.6 s after `ClaudeSeat` is created. That
is already over half of the 1 s timeout in
`test_a_task_that_never_finishes_times_the_turn_out`.

On 2026-10-02 the loop's gate of the `pair/grooming` branch, whose diff
touched only `issues/`, failed the same way:
`test_a_task_that_never_finishes_times_the_turn_out` alone failed with
`'t9' not found in 'turn timed out after 1s'`, and the rest of the class
passed. So the stall still occurs after `parallel-pair-tests` landed, and it
can fail one test of the class rather than all of them.

## How to reproduce

Run the pair tests through `pair/gate.py` at the default worker count (one
per two CPUs, `PAIR_TEST_WORKERS` unset) from inside a seat's sandbox, on
macOS, as the first test run of a turn. It fails intermittently, most often
on the first run after a pause; repeated runs straight after tend to pass.

## Wanted

- Find out whether the stand-in's `exec` stalls (for example while macOS
  assesses a newly written executable) or whether it starts and then
  blocks, and whether a serial run (`PAIR_TEST_WORKERS=1`) also shows it.
  Write the cause here.
- Make the class pass reliably under parallel workers without lengthening
  its timeouts. One way might be to start the stand-in as
  `sys.executable <script>` instead of exec'ing a fresh `#!` file, if
  `ClaudeSeat` can be given the command it starts without changing its
  behaviour for a real `claude`.

The argv is built by `command()` in `pair/seats.py`, whose first element is
the literal `"claude"`, and `ClaudeSeat.__init__` passes it to
`subprocess.Popen`. A way in for the test is a `ClaudeSeat` (or `command()`)
parameter naming the program, defaulting to `["claude"]`; an environment
variable read in production code is not, since it would let the environment
change which program a real seat runs.

## Out of scope

- How the gate splits work into workers (`parallel-pair-tests`).
- Lengthening any timeout in the class, or loosening what its assertions
  check.
- The stall of any test class other than `ClaudeSeatTest`.

## Done when

- The cause, or the strongest evidence for it, is written in this file,
  including what a serial run showed.
- The stand-in's start latency (from `ClaudeSeat` being created to the
  stand-in's first instruction) is measured once before the change and once
  after, under the default worker count, and both are recorded here.
- Twenty runs of the pair tests in a row through `pair/gate.py`, at the
  default worker count, the first of them after a pause of several minutes,
  show no `ClaudeSeatTest` failure; the count is noted here.
- A test shows that `ClaudeSeat` given no program starts an argv whose first
  element is `claude`, so a real seat's command is unchanged.

## The plan

Two separate weaknesses could explain what was seen, and the plan deals with
both:

- **The exec of a new `#!` file.** Every test writes a fresh executable and
  execs it by name through `PATH`. On macOS a newly written executable can
  be held while the system assesses it, and under load that wait can be
  long. That fits the 40 s stalls that took the whole class down together.
- **Start-up counted against the turn.** `ClaudeSeat.send` starts its clock
  when it is called (`pair/seats.py`, `started = time.monotonic()`), and the
  stand-in is often still starting at that moment (0.2 to 0.6 s in passing
  runs). Under load, Python's start-up alone can take longer than the 1 s
  timeout of `test_a_task_that_never_finishes_times_the_turn_out`. That fits
  the 2026-10-02 failure, where that test alone failed.

Steps, in order:

1. **Diagnose and measure before.** Temporarily make `STAND_IN` append
   `time.time()` to a file named by an environment variable as its first
   statement, and have `ClaudeSeatTest.seat` note the time just before it
   creates `ClaudeSeat`. Run the pair tests once through `pair/gate.py` at
   the default worker count, after a pause, and once with
   `PAIR_TEST_WORKERS=1`. Record the largest start latency of each run.
   A stall with no start timestamp means the exec stalled; a timestamp
   followed by silence means the stand-in started and then blocked. Write
   the cause, or the best evidence for it, under a `## Cause` heading.
   This instrumentation is not committed.
2. **Name the program in `command()`.** Add a parameter
   `program: Sequence[str] = ("claude",)` to `command()` and to
   `ClaudeSeat.__init__`, which passes it on. `command()` builds
   `[*program, "-p", ...]`. `pair/pair.py` gives no program, so a real
   seat still runs `claude` found through `PATH`.
3. **Start the stand-in through the interpreter.** In
   `ClaudeSeatTest.setUp`, write `STAND_IN` to `stand_in.py` in the
   temporary directory, with no `#!` line, no `chmod` and no `bin/` on
   `PATH`. Patch only `STAND_IN_SCRIPT` into the environment. In
   `ClaudeSeatTest.seat`, pass `program=[sys.executable, str(stand_in)]`.
   Only the interpreter, which has already been assessed, is exec'd.
4. **Keep start-up out of the 1 s turn.** In
   `test_a_task_that_never_finishes_times_the_turn_out`, give the stand-in a
   `start` step (`{"emit": {"type": "system", "subtype": "init",
   "session_id": "s1"}}`, the shape `STAND_IN`'s `play` reads), and wait
   for it with the same 10 s polling loop that
   `test_a_result_waiting_before_the_message_is_not_the_turns` uses before
   calling `send`. The 1 s timeout and the assertions stay as they are. The
   timeout then measures only the turn, which is what the test is about.
   `send` logs and drops output that is already waiting, so the early event
   changes nothing else in the test.
5. **Test that a real seat's command is unchanged.** Add these tests:
   - In the class that holds
     `test_a_seat_loads_the_project_settings_alone`: `command("p", CONFINED)`
     starts with `"claude", "-p"`, and
     `command("p", CONFINED, program=["py", "s"])` starts with
     `"py", "s", "-p"`.
   - In `ClaudeSeatTest`: a `ClaudeSeat` built with no program, with
     `subprocess.Popen` patched to record its argv and then raise an
     exception the test defines, raises that exception, and the recorded
     argv's first element is `claude`. Raising stops `__init__` before the
     pid file, the reader thread or any process exists, so nothing needs
     stopping. `confinement()` runs `git` through `subprocess` before the
     seat starts, so the patched `Popen` hands any command without
     `stream-json` in it to the real `Popen`.
6. **Measure after, and run twenty.** Repeat step 1's start-latency
   measurement once, at the default worker count, and record it beside the
   first. Then remove the instrumentation. After a pause of several
   minutes, run the pair tests twenty times in a row through `pair/gate.py`
   at the default worker count. Note how many runs there were and any
   `ClaudeSeatTest` failure.

Risks:

- If step 1 shows that the stand-in starts and then blocks, then step 3 does
  not explain the 40 s stalls. Step 4 still covers the 1 s test. If the
  twenty runs still fail, the case for blocking goes under `## Cause` and
  the stall goes back as a new Issue, so that this one is not stretched.
- A seat cannot wait in the foreground (a foreground `sleep` is refused).
  The several-minute pause comes from a background wait, or from the gap
  between turns.
- The twenty runs cost twenty runs of every pair test module, not only
  `ClaudeSeatTest`. This is the evidence the Issue asks for, and it is not a
  benchmark, so it is run once.

## Cause

The stall was not caught in the act: no run here failed. The strongest
evidence is that exec'ing the newly written `#!` file was the slow part of
the stand-in's start.

The stand-in's start latency was measured from just before `ClaudeSeat` was
created to the first statement of the stand-in. In the before runs, every
stand-in started and none stayed silent after starting, so nothing showed it
starting and then blocking.

| Run | Stand-ins | Min | Median | Max |
|---|---|---|---|---|
| Before, `pair/gate.py`, default workers | 6 | 0.216 s | 0.475 s | 0.659 s |
| Before, `ClaudeSeatTest` alone, serial | 6 | 0.157 s | 0.182 s | 0.204 s |
| After, `pair/gate.py`, default workers | 6 | 0.078 s | 0.097 s | 0.110 s |

Under parallel workers, starting through the interpreter took about a fifth
of the time the fresh `#!` file took, and less than the fresh file took in a
serial run with nothing else running. The cost of a fresh file therefore
grows with load. That matches macOS assessing each new executable before it
runs, as the plan supposed.

The serial run was `python -m unittest test_pair.ClaudeSeatTest`, not
`pair/gate.py` with `PAIR_TEST_WORKERS=1`. The seat's harness asks for
approval before running a command with an environment-variable prefix, and
no approval was given.

## Result

- The stand-in is now started as `[sys.executable, stand_in.py]`, through
  the new `program` parameter of `command()` and `ClaudeSeat`. A real seat
  gives no program and still runs `claude`; two new tests,
  `test_a_seat_runs_claude_unless_given_a_program` and
  `test_a_seat_given_no_program_starts_claude`, show this.
- Two things no longer count against a turn's timeout:
  - The stand-in's start-up in
    `test_a_task_that_never_finishes_times_the_turn_out`: the stand-in
    emits an `init` event first, and the test waits for it before `send`.
  - The stand-in's start-up in the two tests that already waited this way:
    they now use the same `ClaudeSeatTest.started` helper. It fails the
    test with how many lines the stand-in wrote if it has not started
    within 10 s, so a stall that recurs reads as a stall rather than as a
    turn timeout.
- Twenty runs in a row of the pair tests through `just gate pair` (which
  runs `pair/gate.py` at the default worker count) began after a 5-minute
  pause. All 20 passed, 225 tests each, with no `ClaudeSeatTest` failure.

## Pair notes

> **primary, in-progress turn 1**
>
> The fix is in and committed: the tests now start the stand-in `claude` through the Python interpreter. Twenty runs of the pair tests in a row, the first after a 5-minute pause, all passed with no `ClaudeSeatTest` failure. The stall was never caught happening here, so the cause rests on timing evidence rather than a reproduced failure.
>
> **What changed**
> - **`pair/seats.py`:** `command()` and `ClaudeSeat` take a new `program` argument, defaulting to `("claude",)`. A real seat passes nothing and still runs `claude` by name.
> - **Stand-in:** `ClaudeSeatTest` writes it as `stand_in.py` and runs it as `[sys.executable, stand_in.py]`, instead of writing a fresh executable `#!` file and putting it first on `PATH`.
> - **1 s timeout test:** in `test_a_task_that_never_finishes_times_the_turn_out` the stand-in now sends a start line, and the test waits for it before calling `send`. The stand-in's start-up no longer counts against the 1 s turn, and the timeout and assertions are unchanged. Two tests that already waited this way now share a small `started` helper.
> - **New tests:** two tests show that a seat given no program still starts `claude`. One checks the argument list `command()` builds. The other catches what `ClaudeSeat` hands to `subprocess.Popen` and lets its own `git` calls through.
>
> **Evidence for the cause**, measured from creating the seat to the stand-in's first line of code:
>
> | Run | Min | Median | Max |
> |---|---|---|---|
> | Before, parallel workers | 0.22 s | 0.48 s | 0.66 s |
> | Before, the class run alone, serially | 0.16 s | 0.18 s | 0.20 s |
> | After, parallel workers | 0.08 s | 0.10 s | 0.11 s |
>
> Every stand-in started, and none started and then went quiet. So the slow part was launching the newly written file, and it got worse under load, which fits macOS checking each new executable before it runs.
>
> **Departures from the plan**
> - **Serial run:** I couldn't run the gate with `PAIR_TEST_WORKERS=1`, because the sandbox asks for approval for a command with an environment variable in front. The serial row above comes from running the class alone with `python -m unittest` instead.
> - **`Popen` patch:** `ClaudeSeat` runs `git` before it starts the seat, so the patched `Popen` passes those calls to the real one. The plan in the Issue file now says so.
>
> I added a `## Cause` and a `## Result` section to the Issue file with the table and these details. `just gate meta` and `just gate pair` both pass. The meta gate first failed on the two code comments I'd added, so I moved that explanation into docstrings.

> **secondary, in-progress turn 2**
>
> My partner's fix holds up, and I made one change on top of it. `just gate pair` (225 tests) and `just gate meta` both pass.
>
> What I checked in their work:
> - **Real seats are unchanged.** A real seat passes no `program`, so it still runs `claude` by name. The stand-in now starts as `[sys.executable, stand_in.py]`.
> - **The stand-in is no longer an executable file on `PATH`,** and nothing else in the repository depended on that setup.
> - **The new test can't interfere with the setup code.** It intercepts `subprocess.Popen` to catch the command a seat would start, and passes the `git` calls the seat makes while setting up straight through to the real `Popen`.
> - **The issue file is complete.** It records the start delay measured before and after (median 0.48 s down to 0.10 s under parallel workers), the serial run, and the twenty passing runs in a row.
>
> The serial run differs from the plan. It ran `ClaudeSeatTest` alone with `python -m unittest` rather than `pair/gate.py` with `PAIR_TEST_WORKERS=1`, because the sandbox wanted approval for a command with an environment variable in front. The issue file says so.
>
> **My change:** the `started` helper in `pair/test_pair.py` waited up to 10 s for the stand-in, then let the test carry on even if it had written nothing. If the stall came back, it would have shown up as a confusing "turn timed out after 1s". Now the test fails with how many lines the stand-in wrote in 10 s, so a stall reads as a stall. I noted this under `## Result` in the issue file and committed it.

> **primary, in-progress turn 3**
>
> I'm keeping your partner's change as it is and adding nothing. In `pair/test_pair.py`, the `started` helper now fails the test after 10 s if the stand-in hasn't written its lines, and says how many it did write. Before, if the stall came back, the test would have carried on and failed later with a misleading "turn timed out after 1s". The helper's docstring still describes what it does, and the Issue file already notes the change under `## Result`. Your partner reported that `just gate pair` and `just gate meta` pass with the change; I didn't rerun them, since nothing has changed since.
