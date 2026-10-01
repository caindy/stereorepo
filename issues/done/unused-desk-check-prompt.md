---
difficulty: medium
---

# No turn runs in the desk-check stage

`Loop.message` loads `pair/prompts/stage-{stage}.md` for the stage a turn runs
in. The usual ways out of a desk check never run a turn in `desk-check`:
`Loop.resume`, and `Loop.accept` when its gate fails, move the Issue to
`in-progress/` first; `Loop.resume_flight` sends a Flight back to `backlog/`.
So `pair/prompts/stage-desk-check.md` reads as if it governs the resumed turn,
and its text ("address the developer's notes") is wrong for every turn that
does load it. Two paths do load it:

1. **A `developer` Issue whose accept conflicts.** `accept` calls `merge`, and
   `rebase` conflicts with `main` before `retirement` moves the Issue to
   `done/`. `rebase` pauses with `retry=None` while `st.stage` is still
   `desk-check`. The next `just pair` passes the `st.retry == "desk-check"`
   check in `run`, calls `work`, and `work` starts turns in `desk-check`.
2. **A Flight overtaken while it lands.** `merge` moves a Flight from its
   Flight check to `desk-check/`, and `land` answers `moved` because the other
   process landed first. `merge` goes round again, and that rebase conflicts
   with the new `main`. It pauses with `retry=None` and `st.stage ==
   "desk-check"`, and the next `just pair` starts turns there. (A Flight's
   merge never runs the gate: a Flight check that changes anything outside
   `issues/` is refused before it merges, so `touches_code` is false.)

(If `land` pauses after an accept, the Issue is already in `done/`, so that
path never runs a turn. The same conflict-after-`moved` sequence does leave
an Issue in `done` with `retry=None`, and the next run then asks for
`stage-done.md`, which does not exist. That is filed as
`issues/backlog/turn-in-done-stage.md`, not fixed here.)

## What is wanted

- In `Loop.work`, just before the turn loop, if `st.stage == "desk-check"`,
  move the Issue back to the stage it was checked from, keeping `st.note`
  (`Loop.move` overwrites it, so save and restore it as `accept` does):
  `in-progress` for an Issue, or the Flight check (`FLIGHT_CHECK`) for a
  Flight, which is an Issue with children (`board.children`). `Loop.move`
  names the target directory `to` rather than `home(to)`, so moving a Flight
  back has to put its file in `underway/`. `accept` can
  then rely on this instead of making its own move to `in-progress`.
  A `developer` Issue moved back this way goes to the desk check again once
  the pair agrees `in-progress`. That is intended, because the code under
  check has changed.
- Tests in `pair/test_pair.py`, one for each path above, that check the next
  turn's stage and the message it receives.
- Delete `pair/prompts/stage-desk-check.md`.

## Out of scope

- The note `Loop.resume` sends, and the other stage prompts.
- The way `rebase` and `land` pause.

## Done when

- Both tests pass, and each fails without the change to `work`.
- `pair/prompts/stage-desk-check.md` is gone, and no file names it apart from
  this Issue.
- `just gate pair` passes.

## The plan

All code changes are in `pair/loop.py`, all tests in `pair/test_pair.py`.

1. **Let `Loop.move` take a directory.** Add `into: str | None = None` to
   `move` (line 1008); the destination becomes `into or to`. Every existing
   caller keeps its behaviour. `move` cannot use `home(to)` for all callers
   because `retirement` moves a Flight to `backlog` meaning `backlog/`, not
   `underway/`.
2. **Add `Loop.leave_desk_check(st, why: str)`** beside `accept`/`resume`.
   It picks `FLIGHT_CHECK` when `board.children(self.wt, "HEAD", st.slug)` is
   non-empty, otherwise `in-progress`. It calls
   `self.move(st, to, into=home(to))` and then sets `st.note` to "This came
   back from its desk check to `{home(to)}/` without landing." followed by
   `why` when `why` is non-empty, and saves.
3. **`accept`** (lines 441–445): replace the save, move and restore of the
   note with `self.leave_desk_check(st, st.note)`, then `return self.work(st)`.
   The gate output still reaches the next turn, so
   `test_gate_failure_goes_back...`-style assertions keep holding.
4. **`work`** (line 619): after the `retry` branch and before
   `st.retry = st.paused = None`, add
   `if st.stage == "desk-check":`, which first calls
   `absorbed = self.absorb_developer(st)` and then
   `self.leave_desk_check(st, why)`. Here `why` is `st.paused or ""`,
   followed by "The developer changed things since the last turn; see the
   changes below." when `absorbed` is true. `st.paused` still holds the pause
   reason (for example "pair/h conflicts with main; resolve it …"), which is
   what the pair needs to know. Absorbing first matters because the pause asks
   the developer to resolve the conflict in the worktree. `move` resets
   `st.head`, so after it a committed resolution would no longer look like
   the developer's, and `leave_desk_check` would overwrite the note that says
   so. A Flight
   paused at `retry == "desk-check"` never gets here, because `run` returns
   before calling `work`.
5. **Delete `pair/prompts/stage-desk-check.md`.** With the guard, `message` is
   never called in `desk-check`; if it were, the missing file raises
   `FileNotFoundError`, which is a better failure than a misleading prompt.
6. `issues/backlog/turn-in-done-stage.md` already holds the `done`-stage
   case named above. Leave it alone.

### Tests

- `LoopTest.test_an_accept_that_conflicts_goes_back_to_in_progress`: set up
  as `test_a_human_issue_waits_for_the_desk_check` (the pair writes `a.txt`),
  then commit a different `a.txt` on `main` in `b.repo`. `accept()` answers
  `paused`, and the state is `("desk-check", None)` for `(stage, retry)`.
  With `stop_when_empty` and one scripted `("primary", quiet)`, `run()`
  answers `stopped`. Then: stage `in-progress`, the issue is at
  `issues/in-progress/h.md` in the worktree, and the last message contains
  "Implement issues/in-progress/h.md" and "conflicts with main". A variant
  uses `b.developer_between` to commit a file in the worktree before that
  turn, and checks that the message also says "The developer changed things".
- `FlightCheckTest.test_a_flight_overtaken_and_conflicting_goes_back_to_its_check`:
  script `("primary", append("big", BRIEF))` and `("secondary", quiet)`, and
  put one action in `b.before_land` that appends different text to
  `issues/underway/big.md` on `main` and commits it. `land` then sees `main`
  moved, and the second rebase conflicts on the Flight file (a rename on the
  branch, an edit on `main`). `run(once=True)` answers `paused` with
  `(stage, retry) == ("desk-check", None)`. With one scripted quiet primary
  turn and `stop_when_empty`, `run(once=True)` answers `stopped`, the stage
  is `flight-check`, the file is at `issues/underway/big.md` in the worktree,
  and the last message contains "Check the Flight issues/underway/big.md".
- Before the guard in step 4, run both tests to see them fail; the existing
  `accept` gate-failure path stays covered by the current desk-check tests.

### Risks

- If the rename-and-edit in the Flight test does not conflict (git can merge
  a rename with an edit), make `main`'s edit and the brief touch the same
  last lines, so the content conflicts.
- A Flight sent back to its Flight check needs a fresh brief this round
  (`test_an_earlier_rounds_brief_does_not_count`). That is right, since
  `main` has changed under it, but the pair will be asked for a new brief
  even though the old one is still in the file.

## Notes for the next reader

- Done as planned, except that the absorb in step 4 lives in
  `leave_desk_check` rather than in `work`. The gate refuses a comment inside
  a function body, so the reason belongs in the docstring, and for `accept`
  the second absorb is a no-op. `Loop.leave_desk_check` is the one way out of
  `desk-check` that does not land: `accept` calls it when the gate fails, and
  `work` calls it for any pause that left the Issue there.
- All three new tests failed before the change to `work`, each with the
  stage still `desk-check`.
- In the Flight test, `b.before_land` starts with a no-op, because `start`
  also goes through `land` when it commits "Start big" to `main`.
- On an accept whose gate fails, the note now begins "This came back from its
  desk check to in-progress/ without landing." and the gate output follows.
  Before this change no test drove that path. Now
  `test_an_accept_whose_gate_fails_goes_back_to_in_progress` does.
- The stage table in `pair/README.md` now says that an accept that fails or
  conflicts also goes back to `in-progress/`, and that no turn runs in
  `desk-check/`.
