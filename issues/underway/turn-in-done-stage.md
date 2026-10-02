---
difficulty: medium
---

# A rebase conflict after landing is overtaken leaves a turn in `done`

`Loop.merge` moves an Issue to `done/` (via `retirement`) before `land`. If
`land` answers `moved` because the other process landed first, `merge` goes
round again. If that rebase then conflicts, `rebase` pauses with `retry=None`
while `st.stage == "done"`. The next `just pair` calls `work`, which starts a
turn, and `Loop.message` reads `pair/prompts/stage-done.md`, which does not
exist, so the loop crashes with `FileNotFoundError`.

Found while planning `unused-desk-check-prompt`, which handles the
`desk-check` stage of the same sequence with `Loop.leave_desk_check`.

## How to reproduce it

As `test_a_flight_overtaken_and_conflicting_goes_back_to_its_check` in
`pair/test_pair.py` does for a Flight, but with an ordinary Issue in
`in-progress` whose branch changes a file `a.txt`:

1. Put `[quiet, main_edits_a]` in `b.before_land`, where `main_edits_a`
   writes different content to `a.txt` in `b.repo` and commits it. The first
   entry is for the landing `start` makes.
2. Let the pair settle `in-progress`. `run(once=True)` answers `paused`, and
   the state has `stage == "done"` and `retry is None`.
3. Script one more turn and run again: `message` raises `FileNotFoundError`.

## Wanted

No turn runs in `done`. In `Loop.work`, where it already sends an Issue left
in `desk-check` back with `leave_desk_check`, an Issue left in `done` goes
back to `in-progress` in the same way: its file moves from `issues/done/` to
`issues/in-progress/` on the branch, and the next turn's note says it came
back without landing, followed by the pause reason ("conflicts with main;
resolve it …") and, if the developer changed things in the worktree, that
they did. An Issue reaches `done` only from `in-progress`, or from
`desk-check` for a `developer` Issue that `accept` merges; both go back to
`in-progress`, and a `developer` Issue then goes to its desk check again once
the pair agrees `in-progress`, since the code under check has changed.

## Out of scope

- The way `rebase` and `land` pause.
- The pause `merge` makes when the gate fails with the Issue in `done`, which
  is retried as `merge` and runs no turn.

## Done when

- A test in `pair/test_pair.py` follows the steps above and, with
  `stop_when_empty` and one scripted quiet turn, asserts that `run` answers
  `stopped`, the state's stage is `in-progress`, the Issue is at
  `issues/in-progress/` in the worktree and nowhere else, and the turn's
  message holds "Implement issues/in-progress/" and "conflicts with main".
  The test fails without the change.
- The existing desk-check tests (`test_an_accept_that_conflicts_goes_back_to_in_progress`,
  `test_a_flight_overtaken_and_conflicting_goes_back_to_its_check`) still pass.
