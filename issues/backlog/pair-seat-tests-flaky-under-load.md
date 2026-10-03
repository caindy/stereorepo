# Make the seat's timing tests pass when the gate runs under load

Two tests in `pair/test_pair.py` failed in `just gate meta pair` on
`render-in-seat-sandbox`. That branch touches nothing under `pair/`, and both
tests pass in `just gate pair` alone and when run on their own:

- `ClaudeSeatTest.test_a_task_that_never_finishes_times_the_turn_out` failed
  with `AssertionError: 't9' not found in 'turn timed out after 1s'`. It
  gives the seat `timeout=1`. Under load, the turn seems to time out before
  the fake seat's `task_started` line for `t9` is read, so the error never
  names the task.
- `ClaudeSeatTest.test_a_result_waiting_before_the_message_is_not_the_turns`
  failed on `turn.text`, with `+ answer` in the diff. It polls `seat.lines`
  for up to 10 seconds and then sends. Under load, the stale result seems to
  arrive after the send has started, or the poll ends on a different line.

## Wanted

- Both tests pass whatever the machine's load, without slower timeouts that
  make the suite slower when it is not under load.

## Done when

- Both tests pass while the `meta` and `pair` projects are gated together,
  and the timing they depend on is set by the test rather than by how fast
  a subprocess starts.
