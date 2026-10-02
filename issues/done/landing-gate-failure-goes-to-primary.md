---
difficulty: easy
---

# Hand a gate that fails while landing back to the primary seat

When `main` has moved since the stage settled, `Loop.merge` rebases and runs
the gate again. If the gate fails and the Issue is still in its stage, `merge`
clears acceptance, sets the gate's output as the note, and returns `None`, so
the pair takes another turn. That turn goes to `st.next_role`, which
`Loop.decide` set to `other(role)` before it advanced: it goes to the
secondary seat whenever the primary seat settled the stage.
`gate-failure-goes-to-primary` sends a failed requirement gate to the primary
seat (`decide` sets `st.next_role = "primary"` for a `GateFailure`); this path
still does not.

Found while implementing `gate-failure-goes-to-primary`, whose "Out of scope"
first said, wrongly, that this path gives no seat a turn.

## How to reproduce it

In a `Bench` in `pair/test_pair.py`, with an Issue in `in-progress` whose
branch changes a file outside `issues/`, so that `touches_code` is true:

1. Script turns so that the primary seat's quiet turn is the one that settles
   the stage: the primary seat writes the file, the secondary seat writes it
   again, then the primary seat is quiet. (A turn that changes something
   resets acceptance to that seat alone, so "primary writes, secondary quiet"
   would settle on the secondary seat's turn, leave `st.next_role` already
   `primary`, and the test would pass without the change.)
2. Set `b.gates = [True, False]`, and put one action in `b.during_gate` that
   commits an unrelated file to `main` in `b.repo`. The first gate run is the
   requirement in `decide`; while it runs `main` moves, so `merge`'s rebase
   moves the branch and runs the gate a second time, which fails.
3. The next turn goes to the secondary seat.

## Wanted

In that branch of `merge`, set `st.next_role = "primary"` along with clearing
`st.approvals` and setting `st.note`, so the seat that repairs a failed gate
is the primary one, as for a failed requirement gate.

## Out of scope

- The pause `merge` makes when the gate fails with the Issue already in
  `done` or no longer in its stage.
- Which seat takes the turn after any other note.

## Done when

A test in `pair/test_pair.py` follows the steps above and asserts that the
turn after the failed landing gate goes to the primary seat and that its
message holds the gate's output (`FAILED: test_widget`). The test fails
without the change.

## The plan

1. Test first, in `pair/test_pair.py` next to
   `test_a_failed_gate_goes_to_the_primary_even_when_it_went_quiet_last`:
   `test_a_gate_that_fails_while_landing_goes_to_the_primary`. Issue `x`,
   `difficulty="easy"`, in `backlog`; `b.gates = [True, False]`;
   `b.during_gate = [commits]`, where `commits` writes, adds and commits
   `b.txt` in `b.repo` (as in
   `test_the_gate_at_landing_after_main_moves_selects_the_same_projects`).
   Script: primary quiet, secondary quiet, primary `append("x", PLAN)`,
   secondary quiet, primary `write("a.txt", "1")`, secondary
   `write("a.txt", "2")`, primary quiet (settles `in-progress`; the
   requirement gate passes while `main` gains `b.txt`; `merge` rebases, gates
   again, fails), then primary `write("a.txt", "3")`, secondary quiet. Assert
   `run(once=True) == "landed"`, `b.sent[7][0] == "primary"`,
   `"FAILED: test_widget" in b.sent[7][1]`, and `b.gate_runs == 3`. Run it
   and see it fail before the change.
2. In `Loop.merge` (`pair/loop.py`, the branch that sets
   `st.approvals, st.note = [], failure`), also set
   `st.next_role = "primary"` before `self.save(st)`.
3. Run the new test and the rest of `pair/test_pair.py`.

Risk is small: the line sits after the `done`/moved-out pause, so only the
path that hands the turn back changes. `FakeSeat` checks each scripted role
against the seat that opens (`pair/test_pair.py:185-187`), so without the
change the test fails on "expected a primary turn, got secondary" before it
reaches the `b.sent[7]` assertions; those assertions guard the message once
the change is in.

## Notes

Done as planned. The new test failed first with "expected a primary turn,
got secondary", and the whole of `pair/test_pair.py` passes with the change.
`pair/README.md` (Landing) now says a gate that fails while landing hands the
turn to the primary seat; the requirement table already covered it.
