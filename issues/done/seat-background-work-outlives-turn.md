---
difficulty: medium
---

# Keep a seat's background work from outliving its turn

The loop takes a seat's turn as over when the turn's result comes back, and
it judges the turn quiet or not from the tree at that moment. A seat can start
a command in the background, end its turn, and be woken later by that
command's completion. Its session then goes on editing the worktree after the
loop has judged the turn, committed, or landed.

## What happened

On 2026-10-01, in the in-progress stage of `fresh-seat-after-refusal`, the
primary seat started `just gate pair` and `just gate meta` in the background
during its first turn and ended the turn. The loop committed the work, and
the secondary seat took turn 2. The loop recorded the primary seat's turn 3
at 11:27:20 as quiet, in 0.0 seconds, yet the primary session ran for about
170 more seconds, woken by its background gates. In that time it wrapped two
long lines it had added, in `pair/loop.py` and `pair/README.md` (11:27:27),
and reran the loop tests against them.

Since turn 3 counted as quiet, the loop moved the Issue to `done/` and landed
it as `30f3ab19` at 11:29:43 without the wrapping. It then paused before
`pair-watch-exit-codes` with "worktrees/pair has uncommitted changes from
before this issue". The developer committed the wrapping to `main` by hand.
The primary seat's session log is `.pair/primary.jsonl`, session
`fa68d3d4-86b7-408a-b0e5-65c1b60fc88d`, in the developer's checkout.

## Why turn 3 took 0.0 seconds

`ClaudeSeat.send` in `pair/seats.py` returns at the first `result` event it
reads from the seat's stdout queue. The log shows what happened in order:

1. Turn 1 emitted `system/task_started` for the meta gate, then its `result`
   while that task was still running.
2. While the secondary seat had turn 2, the gate's `system/task_notification`
   woke the primary session, which ran a turn of its own and emitted a second
   `result` ("I've implemented the plan. `just gate pair` passed…"). Nobody
   was reading, so the events waited in the queue.
3. `send` for turn 3 wrote its message, then read that waiting `result` and
   returned at once. The loop judged the tree quiet, while the session was
   only now starting on the turn 3 message, whose own `result` was never read.

So two things are wrong: the loop judges a turn while the seat still has
background work outstanding, and a `result` that answers no message is taken
as the answer to the next one.

## What is wanted

- A turn ends only when the seat's session is idle: its `result` has come
  back and no background task it started (`system/task_started` without a
  `system/task_notification` for the same task id) is outstanding. After
  the last such notification, the turn waits for the `result` of the turn
  the session runs on its own, and the `TurnResult` it returns carries that
  last `result`. Waiting is bounded by the existing turn timeout, and a
  timeout stops the seat as it does now. Turning background tasks off for
  seats (for instance through Claude Code's
  `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS` setting in the seat's environment)
  is an acceptable alternative, if a test shows the seat's command or
  environment carries it.
- Whichever way is chosen, `send` never returns a `result` that was emitted
  before its own message was written: events already in the queue when
  `send` begins are logged and discarded before the message is written.
- `pair/README.md` says a seat's turn ends when its session is idle.

## Out of scope

- Other harnesses than Claude Code, and `FakeSeat`'s scripted turns beyond
  what the test needs.
- Detecting edits made outside any seat session (the developer's own hand).
- Changing how the loop decides a turn is quiet once the turn has ended.

## Done when

Tests in `pair/test_pair.py` drive `ClaudeSeat` against a stand-in `claude`
executable, put first on `PATH`, that reads stream-json messages on stdin and
writes scripted events, and show that:

- when the stand-in emits `task_started`, then `result`, then later
  `task_notification`, an edit to the tree, and a second `result`, `send`
  returns only after the second `result`, and the edit is in the tree when
  it returns (or, if background tasks are turned off instead, the seat's
  command or environment carries that setting);
- a `result` the stand-in emits unprompted, and that is waiting in the
  queue before `send` is called, is not returned as that turn's result: the
  turn returns the `result` the stand-in emits in answer to the message.

## The plan

Wait for an idle session rather than turning background tasks off. A seat
keeps running its gates in the background, which the stage prompts already
lead it to do, and the fix holds for subagents and monitors too, since all
of them report through the same `task_started` and `task_notification`
events. Only `pair/seats.py` changes in code; `loop.py` already treats
whatever `send` returns as the end of the turn.

1. **Discard what is waiting.** At the top of `ClaudeSeat.send`, before the
   `pair/sent` log line and the write, drain `self.lines` without blocking.
   Log each parsed event with `_log` and record its session id as now, so
   `primary.jsonl` keeps the whole history, and feed its task events to the
   set in step 2; take no `result` from it. If
   the drain reaches `None`, the process has ended: return the same "seat
   exited mid-turn" `TurnResult` the read loop returns.
2. **Track outstanding tasks.** Keep a set of task ids on the instance,
   not per call, so a task seen during the drain or in an earlier turn
   still counts:
   add on `{"type": "system", "subtype": "task_started"}`, remove on
   `subtype: "task_notification"`. On a `result`, keep it as the latest
   and return only if the set is empty; otherwise keep reading. A
   notification for a task id the set does not hold (one started in an
   earlier turn that timed out) is removed harmlessly. A foreground command
   also emits `task_started` (`is_backgrounded: false`) and its
   notification before its turn's `result`, so it needs no special case.
3. **Ask once for outstanding tasks to be settled.** The first `result` of
   a `send` that leaves the set non-empty makes `send` write one more user
   message, logged as `pair/sent`, naming each outstanding task by the
   `description` from its `task_started`. The message says the turn ends
   only when they have finished or been stopped, and that a task no longer
   needed can be stopped with `TaskStop`. `ALLOWED` needs no change:
   `TaskStop` already runs in a seat without a prompt (four calls in the
   developer's `.pair/primary.jsonl` on 2026-10-01 succeeded, none denied),
   and each stopped task then emitted its `task_notification` with
   `status: "stopped"`, so stopping a task empties the set as finishing
   does. The reminder is sent once per `send`; after it,
   `send` just reads on.
4. **What the turn returns.** `text`, `error`, `refused` and `cost_usd`
   come from the last `result`. `usage` is summed key by key over every
   `result` in the turn, because each `result` reports only its own turn's
   tokens and `turns.jsonl` should count the self-run turn too. (Turn 3 in
   `.pair/turns.jsonl` shows `total_cost_usd` already cumulative per
   process, so the last one is right as it is.) An error `result` while
   tasks are outstanding still waits: the session may yet recover in its
   self-run turn, and the timeout bounds it.
5. **Timeout.** Unchanged: the deadline runs from the start of `send`, and
   a seat whose tasks never finish is stopped and reported as timed out. The
   error text names the outstanding task ids, so the developer can tell a
   hung background task from a slow turn.
6. **Docs.** The `seats.py` module docstring says the turn ends at the
   `result` that leaves no background task outstanding. In `pair/README.md`,
   "How an Issue moves" gains a sentence after "takes the first turn in each
   stage": a turn ends when the seat's session is idle, its last `result` in
   and no background task it started still running, so a background gate
   counts as part of the turn that started it.

### Tests

A new `ClaudeSeatTest` in `pair/test_pair.py`:

- `setUp` builds a repository with a linked worktree as `ConfinementTest`
  does (`confinement` refuses a cwd that is not one), and writes an
  executable `claude` into a temporary `bin/`, put first on `PATH` with
  `mock.patch.dict(os.environ, ...)`. The stand-in is a short Python script
  that ignores its arguments and reads a JSON script from a path in an
  environment variable (the seat passes its environment through): a list of
  steps to play at start, and a list per incoming stdin line. A step emits
  an event, sleeps, or writes a file relative to its cwd. Each `result` it
  emits carries `session_id` and `usage`.
- *A background task holds the turn open:* on the message, emit
  `task_started` (id `t1`), `result` ("first"), sleep 0.3 s,
  `task_notification` (`t1`), write `late.txt`, `result` ("second").
  `send` returns `text == "second"`, `late.txt` exists in the worktree when
  it returns, `usage` is the sum of both, and `primary.jsonl` holds one
  reminder `pair/sent` after the first `result` naming the task's
  description. The stand-in plays no steps for the reminder line.
- *A waiting result is not this turn's:* at start, emit a `result`
  ("stale"); the test waits until `seat.lines` is non-empty, then sends. On
  the message the stand-in emits `result` ("answer"). `send` returns
  "answer", and `primary.jsonl` holds the stale event before `pair/sent`.
- *A task that never finishes times out:* with `timeout=1`, emit
  `task_started` and `result` only. `send` returns `ok=False` with an error
  naming the task id, and the process has been stopped.

`seat.stop()` in `tearDown` closes stdin; the stand-in exits on EOF.

### Risks

- The event names and fields (`system`/`task_started`/`task_notification`,
  `task_id`) are what this version of Claude Code emits, read from
  `.pair/primary.jsonl` on 2026-10-01, not a documented contract. If a later
  version renames them, the set never fills and the old behaviour returns
  silently. The stand-in pins the shape we rely on, so a change shows up
  only in a real run; the module docstring says where the names came from.
- Some tasks never report back. In the developer's `.pair/primary.jsonl`
  and `secondary.jsonl` on 2026-10-01, six of 365 `task_started` events
  have no `task_notification`. Each is a foreground command, such as
  `git --no-pager show --stat HEAD | cat`, that hit the Bash tool's
  120-second timeout. Claude Code then moved it to the background
  (`task_updated` with `is_backgrounded: true`), where it was still
  running when the session's later turns ended. Under this plan, each of those would have
  held its turn open until the 45-minute timeout and a restart. The
  reminder in step 3 is the mitigation: the seat can stop such a task
  itself. If the seat ignores it, the timeout and restart still bound the
  cost, and the restart kills the hung task with the process. The error
  names the task, so the developer can tell this case from a slow turn.
- The stand-in is a real subprocess with a sleep, so the three tests add
  about two seconds to the pair tests.

## Notes from the implementation

- The plan held. `send` now clears out waiting output first, then reads
  until a `result` leaves `ClaudeSeat.tasks` empty, and sends `SETTLE`
  (in `seats.py`) once if the first such `result` does not. A failed write
  of `SETTLE` is ignored: the process is gone, so the next read is the end
  of output and the turn returns "seat exited mid-turn".
- `ClaudeSeat.stop` now also waits for a killed process, joins the stdout
  reader, and closes stdout and stderr, which the new tests showed were left
  open (`ResourceWarning`). If a child the seat left running still holds
  stdout open after five seconds, stdout is left to the reader instead of
  being closed under it.
- The tests are `ClaudeSeatTest` in `pair/test_pair.py`. The stand-in
  `claude` is the `STAND_IN` script there. It reads its steps from the file
  named by `STAND_IN_SCRIPT`, which the seat inherits because it passes its
  environment through. The four tests take about two seconds; the fourth
  shows that a task started in output cleared out before the message still
  holds the turn open.
- `<role>.log`, the log a person tails, now shows each task's start and end,
  and a `result` reads `<<< result`, not `<<< turn ended`, since a `result`
  with tasks running no longer ends the turn.
