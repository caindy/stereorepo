---
difficulty: medium
---

# Make the seat's timing tests pass when the gate runs under load

Two tests in `ClaudeSeatTest` (`pair/test_pair.py`) failed in
`just gate meta pair` on `render-in-seat-sandbox`. That branch touches
nothing under `pair/`, and both tests pass in `just gate pair` alone and
when run on their own. `claude-seat-test-stalls-under-load` (done) fixed the
stand-in's start-up stall; these are what is left.

- `test_a_task_that_never_finishes_times_the_turn_out` failed with
  `AssertionError: 't9' not found in 'turn timed out after 1s'`. It gives the
  seat `timeout=1`, and the turn's script emits `task_started` for `t9` only
  after the stand-in reads the message. Under load, the 1 s timeout seems to
  expire before that line is read, so the error never names the task.
- `test_a_result_waiting_before_the_message_is_not_the_turns` failed on
  `turn.text`, with `+ answer` in the diff. `started()` polls `seat.lines`
  for up to 10 s until the stale `result` is queued, then sends. Under load,
  the stale result seems to be taken as the turn's, or the turn's own
  `result` arrives after the turn has already ended.

## How to reproduce

Run the two tests while every CPU is busy, for example with one
`yes > /dev/null` per core running alongside, or inside `just gate meta pair`.
They fail intermittently; on their own on an idle machine they pass.

## Wanted

- Each test controls the timing it asserts on, rather than racing a
  subprocess: for example, the timeout test lets the stand-in confirm it has
  emitted `task_started` before the clock is allowed to run out (a timeout
  that starts after the task line is read, or a stand-in that waits for a
  signal from the test), and the stale-result test waits for the stale line
  to be consumed as stale, not merely queued.
- If a test shows `ClaudeSeat` itself mis-assigns a result that arrives
  before the message, as opposed to the test racing, fix `pair/seats.py` and
  say so in this file.
- No timeout in the suite grows to hide the race; the class runs no slower
  on an idle machine than today.

## Out of scope

- Other tests in `pair/test_pair.py`.
- The stand-in's start-up, which `claude-seat-test-stalls-under-load` fixed.

## Done when

- Both tests pass 20 runs in a row with every CPU loaded as in the
  reproduction (one measurement, recorded here).
- Neither test's outcome depends on a sleep or timeout racing a subprocess:
  the ordering each asserts is established by the test before it asserts.
