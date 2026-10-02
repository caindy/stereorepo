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
- A second test does the same for a `developer` Issue whose `accept` is
  overtaken and then conflicts: `accept` answers `paused` with the stage
  `done`; the next run puts it in `issues/in-progress/`, and once the pair
  settles `in-progress` again it pauses at `desk-check` with
  `retry == "desk-check"` rather than landing.
- The existing desk-check tests (`test_an_accept_that_conflicts_goes_back_to_in_progress`,
  `test_a_flight_overtaken_and_conflicting_goes_back_to_its_check`) still pass.

## The plan

**Why the file is in `done/` on the branch.** `merge` commits the move to
`done/` (`move`), then `squash` folds the branch into one commit on its fork
point, which also drops the slug from `ORDER`. `land` answers `moved`, and the
next `rebase` conflicts and aborts, so the branch is left at that squash
commit: the Issue file sits in `issues/done/` and `ORDER` on the branch no
longer lists it.

**`pair/loop.py`.**

1. Rename `leave_desk_check` to `send_back` (callers: `accept`, `work`) and
   let it take any stage that left without landing. The target stays
   `FLIGHT_CHECK` for a Flight with children and is `in-progress` otherwise,
   which is right for `done` too, since only an ordinary Issue or a
   `developer` Issue reaches `done/`. The first line of the note names where
   the Issue was: "This came back from its desk check to …" for `desk-check`,
   and "This came back from done/ to in-progress/ without landing." for
   `done`. The rest (`why`, then the developer's edits) is unchanged. Update
   its docstring.
2. In `work`, widen `if st.stage == "desk-check"` to
   `if st.stage in ("desk-check", "done")`. The `retry == "merge"` branch
   above it runs first, so the gate-failure pause in `done` (out of scope)
   still retries `merge` and never reaches this line unless that merge pauses
   again on a conflict, which is exactly the case to send back.

**`pair/README.md`.** In the stage table, the `in-progress/` row's "otherwise
landing" gains: a landing whose rebase conflicts after `main` moved sends the
Issue back to `in-progress/` from `done/`, and no turn runs in `done/`.

**`pair/test_pair.py`**, next to `accept_that_conflicts`:

- `test_a_landing_overtaken_and_conflicting_goes_back_to_in_progress`: an
  ordinary Issue `h` (no difficulty set in the script, as other tests do);
  `before_land = [quiet, main_edits_a]`, where `main_edits_a` writes
  `"main's"` to `a.txt` in the repo and commits; script the pair through
  backlog, todo and in-progress, the in-progress primary writing `a.txt`.
  `run(once=True)` answers `paused` with `(stage, retry) == ("done", None)`.
  Then `stop_when_empty`, one quiet primary turn, and the assertions the issue
  lists, plus that the message lacks "The developer changed things": `squash`
  records the squashed `HEAD` in `st.head`, so the aborted rebase must not
  read as the developer's edit. Before the change this raises
  `FileNotFoundError` on `prompts/stage-done.md`.
- `test_an_accept_overtaken_and_conflicting_goes_back_to_its_desk_check`: a
  `developer` Issue brought to its desk check as in `accept_that_conflicts`,
  but with no edit on `main` before `accept`; instead `before_land =
  [quiet, main_edits_a]`. `accept()` answers `paused` with stage `done`.
  A turn that writes `a.txt` cannot make the later rebase clean: `rebase`
  replays the branch commit by commit, and the squash commit at its base
  still changes `a.txt` against `main`'s. So the developer resolves the
  conflict the way the pause asks, before the next run: in `b.loop.wt`,
  `git rebase -X theirs main` (keeps the branch's `a.txt`; `ORDER` replays
  cleanly, since `main_edits_a` does not touch it). `absorb_developer` then
  sees the new `HEAD`. Script a quiet primary and a quiet secondary; the
  branch still differs from `main` in `a.txt`, so `touches_code` holds and
  `requirement`'s rebase answers False. `run()` then answers `desk-check`
  (the `kind` `pause` returns), with the state at `desk-check`,
  `retry == "desk-check"`, the file at `issues/desk-check/` only, and the
  first turn's message holding "The developer changed things".

Run them with `uv run --quiet --script pair/test_pair.py -k overtaken -k
conflict`, then the whole of `test_pair.py`.

**Risks.**

- `ORDER` on the branch has already lost the slug when the Issue comes back,
  so the branch's history now holds a commit that touches `ORDER`, which
  `squash`'s docstring says never happens before landing. That is harmless:
  a later rebase that meets a reordering on `main` conflicts in `ORDER` only,
  which `rebase` resolves through `board.merge_order`, and `squash` drops
  the slug only if it finds it. `main`'s `ORDER` is untouched until the
  landing, so there is nothing to assert there mid-turn; the second test,
  which rebases that commit again, is what exercises it.
- `send_back` calls `absorb_developer` before `move`, as `leave_desk_check`
  does; keep that order, or a conflict the developer resolved reads as the
  pair's.

## Notes

- `leave_desk_check` is now `send_back`. Its note names `done/` as where the
  Issue came back from, and keeps "its desk check" for `desk-check`, so the
  existing desk-check messages read as before.
- Both new tests fail with `FileNotFoundError` on `prompts/stage-done.md`
  against the previous `loop.py`, and pass with the change. The developer's
  `git rebase -X theirs main` in the second test resolves the conflict as
  the plan expected.
