---
difficulty: easy
---
# Hand a failed gate back to the primary seat

Once both seats leave a stage as it stands, `Loop.decide` in `pair/loop.py`
checks the stage's requirement, and in the in-progress stage that runs the
full `just gate`. When the gate fails, the failure goes to `other(role)`: the
seat after the one whose quiet turn settled the stage. That is the secondary
seat whenever the primary seat was the last to go quiet, so the seat whose
part is to review is the one told to repair the build.

## Wanted

A requirement that fails because `just gate` fails sends the next turn, with
the gate's output, to the primary seat, whichever seat went quiet last. That holds wherever
`Loop.requirement` runs the gate: the in-progress stage, the grooming
pass, and the Flight check (`Loop.flight_checked`). Other unmet
requirements, including "nothing outside issues/ has changed", keep going
to `other(role)`, and a requirement that pauses the loop still pauses it.

## Out of scope

When the gate runs, and what the seats run during their turns. A gate that
fails on `just pair-accept` already restarts `in-progress/` with the primary
seat, so it needs no change. A gate that fails while landing, after `main`
moved, gives the pair a turn through `Loop.merge`, not through
`Loop.requirement`; routing that turn is `landing-gate-failure-goes-to-primary`.

## Done when

A test in `pair/test_pair.py` settles an in-progress stage with the primary
seat's quiet turn, makes the gate fail, and finds that the next turn goes to
the primary seat with the gate's output; a second does the same for a
grooming pass; a third finds that an unmet requirement other than the gate
still goes to `other(role)`; and the
paragraph under the requirement table in `pair/README.md` says where a
failed gate goes.

## The plan

1. **Mark a gate failure in `pair/loop.py`.** Add `class GateFailure(str)`
   beside `GATE_TAIL`, and a helper `gate_fails(out: str) -> GateFailure`
   that builds the existing message (`` `just gate` fails:`` and the fenced
   tail). Use it at the four requirement sites: grooming (line 945),
   in-progress (978) and both returns in `flight_checked` (1007, 1017). The
   landing site (1204) may use the helper for the text, but its behaviour
   is out of scope. Because `GateFailure` is still a `str`, the signatures,
   the `"paused"` sentinel and the note text stay as they are.
2. **Route it in `Loop.decide`.** In the unmet branch, after `st.note` is
   set, add `if isinstance(missing, GateFailure): st.next_role = "primary"`.
   Everything else keeps `other(role)`, which `decide` already set.
3. **Tests in `pair/test_pair.py`**, beside
   `test_gate_failure_goes_back_to_the_pair_with_its_output`:
   A stage settles on the primary's quiet turn only when the secondary
   changed something on the turn before: the first turn is always the
   primary's, so `(primary, quiet), (secondary, quiet)` settles on the
   secondary. Each test below uses `(primary, change), (secondary, change),
   (primary, quiet)`.
   - In-progress: easy Issue, `b.gates = [False, True]`. Backlog and todo
     as in the existing test, then `("primary", write("a.txt", "1"))`,
     `("secondary", write("a.txt", "2"))`, `("primary", quiet)` (gate
     fails), `("primary", write("a.txt", "3"))`, `("secondary", quiet)`.
     Assert `run(once=True) == "landed"`, that `b.sent[7][0] == "primary"`
     and that `b.sent[7][1]` holds `FAILED: test_widget`.
   - Grooming pass, driven through `b.groomer.groom()` as in
     `test_a_pass_takes_up_only_the_issues_not_groomed`: `b.gates =
     [False]`, `("primary", both(front(...), order(...)))`, `("secondary",`
     an edit to the order or the Issue`)`, `("primary", quiet)`, then
     `("primary", quiet)`, `("secondary", quiet)`. Assert that the
     fourth turn is the primary's and holds `FAILED: test_widget`.
   - Non-gate requirement: an Issue with no `difficulty`,
     `b.stop_when_empty = True`, `("primary", append("x", "…"))`,
     `("secondary", append("x", "…"))`, `("primary", quiet)`. Assert that
     `b.state().next_role == "secondary"` and the note says
     ``set `difficulty:` ``. The existing test at line 328 does not cover
     this: it settles on the secondary's quiet turn.
4. **`pair/README.md`:** reword the sentence under the requirement table
   ("If the requirement does not hold…") to say that a failed gate's turn
   goes to the primary seat, and any other unmet requirement's turn goes to
   the seat that did not go quiet last. The rule applies to three stages,
   so that sentence is a better home for it than a table cell.

Risk: the turn in the existing gate-failure test already lands on the
primary, so it cannot tell the old routing from the new; the new test has to
make the primary the last to go quiet. Check how many gate results each
scripted path consumes from `b.gates`, so the failure lands on the
settlement under test and not on landing.

## Notes

- `GateFailure` is a `str` subclass that `gate_fails(out)` returns, so
  `Loop.requirement` and `flight_checked` keep returning `str | None` and
  `decide` tells a failed gate apart with `isinstance`. The message text is
  the same as before. `Loop.merge` uses the helper for its note as well, but
  it does not route through `decide`.
- The README rule went into the paragraph under the requirement table, not
  into a cell, because it covers three stages.
- `FlightCheckTest.test_a_failed_gate_in_a_flight_check_goes_to_the_primary`
  covers the Flight check's gate failure as well, since `flight_checked`
  builds its own `GateFailure` and a plain string there would slip past
  the routing unnoticed.
