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

## Out of scope

- How the gate splits work into workers (`parallel-pair-tests`).
- Lengthening any timeout in the class.

## Done when

- The cause, or the strongest evidence for it, is written in this file.
- Twenty runs of the pair tests in a row through `pair/gate.py`, at the
  default worker count and starting from a pause of several minutes, show
  no `ClaudeSeatTest` failure; the count is noted here.
- `ClaudeSeat` still starts `claude` by name when nothing else is given.
