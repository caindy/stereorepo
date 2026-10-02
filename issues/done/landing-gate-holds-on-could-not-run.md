---
difficulty: medium
parent: onboard-fitch-mvp
---

# Hold a landing whose gate has a step that could not run

A gate step that this environment cannot run reports `?` (Article 6,
`.meta/check.py`'s `closing_block`). `.meta/gate` prints each one as
`?  <project>/<step>: <why>` and does not count it as a failure. Where a person
runs the gate, a `?` passes, and it fails only where `CI` is set (stereorepo's
DR-261). The loop runs `just gate <targets>` through `pair/pair.py`'s `gate`.
It judges the result in `pair/loop.py`'s `Loop.run_gate` only by the exit code,
and it does not set `CI`. So an Issue lands even when a step never ran.

fitch-mvp depends on that distinction. Its tests that need Neo4j report `?`
where neither Neo4j nor a Docker daemon is reachable, as in a seat's sandbox,
so a seat's targeted gate passes without them. The developer decided that
those tests must run before an Issue lands. Today nothing enforces that.

## Wanted

- The loop finds a `?` step in the gate's output by the shape `.meta/gate`
  prints it in, `?  <step>: <why>` (its `COULD_NOT`), which includes a
  Project's `?  <project>: no gate asserted`. The `?  steps that could not
  run (n)` summary from `closing_block` has no colon after the step and is
  not a step of its own.
- When a gate the loop runs reports a `?` step, the loop treats it as neither
  a pass nor a failure. This covers the gate at the end of `in-progress`, the
  Flight check, the grooming pass, and the gate after a rebase in
  `Loop.merge`. The loop pauses (`Loop.pause`) with a reason that names each
  `?` step and its `why`. The Issue stays in its stage, nothing lands, and the
  note, approvals and next seat are left as they were. A `?` does not go back
  to the seats as a gate failure, because they cannot provide an environment.
- After the developer supplies what was missing (by starting Docker, say),
  `just pair` resumes the paused Issue and runs the gate again before any
  seat takes a turn. If it then reports no `?`, the Issue goes on as it
  would have; if it still does, the loop pauses again.
- A gate whose output holds an `x` step goes back to the seats as a failure,
  as it does today, whether or not it also holds a `?` step.
- The gate a seat runs while it works is unchanged: a `?` there still passes.

## Out of scope

- What `?` means where a person runs the gate, and what `.meta/gate` and
  `.meta/check.py` print or return. DR-261 stands.
- Setting `CI` for the loop's gate. The loop reads the output instead.

## How anyone will know it is done

- In `pair/test_pair.py`, a `Loop` whose fake gate passes with a
  `?  proj/neo4j tests: no Docker daemon` line in its output pauses. Its
  `State.paused` names `proj/neo4j tests` and `no Docker daemon`, which is what
  `just pair-status` shows. The Issue file has not moved, and `main` has not
  advanced.
- Running that loop again with a fake gate whose output holds only `ok` lines
  lands the Issue, and no seat takes a turn in between.
- A fake gate that fails with both an `x` line and a `?` line sends the
  failure back to the primary seat and does not pause.
- A fake gate with only `ok` lines lands as before, and one with an `x` line
  still sends the failure back to the primary seat as the note.
- No step of stereorepo's own Projects reports `?` in a seat's sandbox, or
  this change would hold every landing here. The seats find each source of a
  `?` (a `collect.CouldNotRun` a check can return, a Project with no `gate`)
  and record each one that a seat's sandbox can reach as a new Issue in
  `issues/backlog/` before this one lands.

## The plan

All of the change is in `pair/loop.py`, its tests in `pair/test_pair.py`, and a
line in `pair/README.md`.

1. **Read the `?` steps.** Add a module constant `COULD_NOT`, a copy of
   `.meta/gate`'s regex `^\?  (?P<step>\S[^:]*): (?P<why>.*)$`, since
   `.meta/gate` is a script and cannot be imported. Its docstring names the
   original. Add `class GateUnrunnable(str)` beside `GateFailure`, and
   `gate_unrunnable(out)`, which returns one, or None when no line of `out`
   matches. Its text is
   `the gate could not run N step(s); supply what they need, then run again:`
   with one `- <step>: <why>` line per match. The summary line from
   `closing_block` and its two-space detail lines do not match, so they are
   not counted twice.
2. **Classify in `Loop.run_gate`.** When the gate does not pass, return
   `gate_fails(out, targets)` as today, whatever `?` lines the output also
   holds. That covers `.meta/gate`'s own `x` line when a Project exits non-zero
   with only `ok` and `?` steps. When it passes, return
   `gate_unrunnable(out)`, which is None when no step was `?`. The return type
   becomes `GateFailure | GateUnrunnable | None`.
3. **Hold at the end of a stage.** In `Loop.decide`, after `requirement`,
   when `missing` is a `GateUnrunnable`, return
   `self.pause(st, missing, retry=GATE)`, where the new constant is
   `GATE = "gate"`. Both approvals, `note` and `next_role` are as `decide`
   left them. This one seam covers `in-progress`, the Flight check and the
   grooming pass, because each reaches `run_gate` through `requirement`.
   Move the block after `requirement` (advance, pause, or note to the seats)
   into a helper, `close_stage(st, issue)`, so that the resume can call it.
4. **Resume at the gate.** In `Loop.work`, `st.retry == GATE` clears
   `paused` and `retry`, re-reads the Issue (None for a grooming pass), and
   returns `self.close_stage(st, issue)` if that gives an outcome. Otherwise,
   when the gate now fails, the loop falls into the turn loop with the note
   for the primary seat. No seat runs before the gate.
5. **Hold while landing.** In `Loop.merge`, when `run_gate` returns a
   `GateUnrunnable`, return `self.pause(st, failure, retry="merge")` before
   the existing `done` and moved-stage check. Today `work` resumes
   `retry == "merge"` with `self.merge(st)`. The rebase there usually does not
   move, so the gate would be skipped and the Issue would land unchecked.
   Change it to `self.merge(st, force_gate=True)`. That also re-gates the two
   existing `merge` pauses, which is right for the first and costs one gate
   run for the second. The first is "the gate now fails on the squashed
   issue". It said "main moved…" until a resume could reach it with `main`
   where it was. The second is "main kept moving…".
   `pair-accept` reaches `merge` too, so an accepted `developer` Issue can
   pause here while still in `desk-check/`. On resume, if the gate then fails,
   `merge` returns None with the failure in `st.note`, and `work` goes on to
   `send_back(st, st.paused or "")`. That would replace the failure with the
   stale `?` reason, because `send_back` rewrites `st.note`. In the
   `retry == "merge"` branch, clear `st.paused` before calling `merge`, and
   send back with `st.note` as `Loop.accept` does.
6. **Document.** In `pair/README.md`, add a line where the gate and pauses
   are described: a gate step that could not run pauses the loop, it is not
   sent to the seats, and `just pair` re-runs the gate.

### Tests

- Let the fake gate in `test_pair.py`'s bench take either a bool or an
  `(ok, out)` pair from `b.gates`, so that existing tests are unchanged.
- In `in-progress`, the gate gives `(True, "ok a — 1\n?  proj/neo4j tests: no Docker daemon\n")`.
  `run(once=True)` returns `"paused"`, and `state().paused` holds both
  `proj/neo4j tests` and `no Docker daemon`. The Issue is still in
  `in-progress/` in the worktree, and `main` has not moved. Then the gate
  gives only `ok`, and `run` returns `"landed"` with no further seat turn, so
  the script is empty and `b.sent` has not grown.
- Resuming while the gate still gives `?` pauses again with no seat turn.
- A gate of `(False, "x  a (1)\n?  b: c\n")` sends `FAILED`-style output to
  the primary seat and does not pause.
- Landing: the first gate passes, `during_gate` moves `main`, and the second
  gate gives a `?`. The run pauses with `retry == "merge"` and nothing lands.
  Running again with an `ok` gate lands the Issue and runs the gate once
  more, so `gate_runs` goes up by one.
- A `developer` Issue at its desk check, with a commit on `main` so that
  `merge` gates (it gates only when the rebase moves or the developer edited
  the branch): `pair-accept` meets a `?` gate and
  pauses with nothing landed. Running again with a failing gate sends it back
  to `in-progress/` with the gate's output, not the `?` reason, in the note.
- A grooming pass whose gate gives a `?` pauses, and resumes to land.
- `gate_unrunnable` unit cases: the `closing_block` summary and its indented
  lines are not steps, `?  meta: no gate asserted` is a step, and output
  with no `?` gives None.

### Risky

- **Holding stereorepo's own landings.** The loop's gate runs in the
  supervisor's process in `worktrees/pair`, not in a seat's sandbox, but any
  step that reports `?` there now holds every landing here. Known sources are
  `.meta/checks/files/rendered.py` ("apm is not installed") and
  `python.py`'s ruff and mypy checks when neither tool nor `uvx` is present.
  Others are the `?  dereference:` lines from `.meta/lib/dereference`, if a
  gate step runs them, and each `CouldNotRun` in `.meta/checks/`. Before this
  Issue lands, the implementer reads the gate output of a run the loop has
  already recorded, if one is to hand, or runs the targeted gate of each
  Project once in the worktree, and greps for lines starting `?  `. Each one
  found becomes a new Issue in `issues/backlog/`, as the done criteria say.
  The implementer does not weaken the hold to get around it.
- **`retry == "merge"` now gates on resume.** An existing test that counts
  `gate_runs` across a `merge` pause may need its count raised. The change in
  behaviour is intended, and each such edit says so.
- **Moving the block out of `decide`.** `close_stage` must keep `decide`'s
  order exactly: a `"paused"` from `requirement`'s rebase, a `GateFailure`
  setting `next_role = "primary"`, and the round cap checked after it.

## What the next reader should know

- The work followed the plan. `Loop.close_stage` is the block taken out of
  `decide`, and both `decide` and the `GATE` resume in `work` call it.
  The round cap stays in `decide`, so a resume does not count as a turn.
- Re-gating on a `retry == "merge"` resume changed no existing test's
  `gate_runs`. The one existing `merge` pause after a failed gate
  (`test_a_failing_gate_after_a_split_goes_back_pauses_the_landing`) now
  lands only because its re-run gate passes. Before, it landed without a
  gate.
- `COULD_NOT` in `pair/loop.py` copies `.meta/gate`'s pattern, and excludes
  newlines from the step so that it can scan the whole output with
  `re.MULTILINE`. If `.meta/gate` changes the shape of a `?` line, change
  both.
- On 2026-10-02, the gates of `meta`, `pair`, `python-seed` and `rust-seed`,
  run once each in this worktree, reported no `?` step. So no source of a
  `?` was found to file in `issues/backlog/`, and this change does not hold
  stereorepo's own landings. If one appears later, for example `apm` missing
  on another machine, the loop pauses and names it, and the developer either
  supplies it or files the Issue.
- Because a `retry == "merge"` resume now always gates, it also re-gates
  resumes of `land`'s pauses (the developer's checkout refused the
  fast-forward) and of a failed Flight delivery. The latter changes nothing
  outside `issues/`, so `touches_code` skips its gate. The pause for a gate
  that fails once the Issue is in `done/` no longer says "main moved", since
  such a resume can reach it with `main` where it was.
