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
   the stage: the primary seat writes the file, the secondary seat is quiet,
   then the primary seat is quiet.
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
