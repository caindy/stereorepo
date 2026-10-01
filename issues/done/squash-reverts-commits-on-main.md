---
difficulty: easy
---

# Keep a landing from reverting commits made on `main` while it gates

`Loop.squash` in `pair/loop.py` commits the Issue's branch onto `main` as one
commit by running `git reset --soft <main>` and committing the index. It
resets to wherever `main` is at that moment, but the index holds the tree the
branch was rebased onto, which can be older. Any commit made on `main` between
the rebase and the squash is then reverted by the squashed commit, with no
conflict and no warning. That window holds the full `just gate` before
landing, about 2 minutes an Issue.

## What happened

On 2026-10-01, from the reflog of `worktrees/pair`:

1. 13:50:27: the loop rebased `pair/seat-git-signature-check-hangs` onto
   `main` at `9dbfe9b` and went on to gate it.
2. 13:51:50: the developer's checkout committed `0e454a1` on `main`, which
   moved `issues/roadmap/gate-only-touched-projects.md` to `issues/backlog/`
   and added it to `ORDER`.
3. 13:52:31: `squash` reset softly to `main`, now `0e454a1`, and committed
   the index built on `9dbfe9b` as `9027372`. That commit reverted `0e454a1`.
4. The fast-forward was refused (see `land-retries-a-passing-race`). The next
   `just pair` rebased `9027372` onto `182dc9c`, revert included, and landed
   it as `d45b1919`. The move was restored by hand afterwards.

## Wanted

The squashed commit contains exactly the branch's changes on top of the
commit it was rebased onto. If `main` has moved since that rebase, the loop
treats it as `moved`: it rebases onto the new `main` and gates again, as
`land` already does when the fast-forward finds `main` moved.

The likely fix is small: `squash` resets softly to the commit the branch was
rebased onto (`git merge-base <main> HEAD`, which `rebase` leaves at the
`main` it rebased onto) rather than to `<main>` itself. The squashed commit
is then not built on a moved `main`, the ancestor check after `squash` in
`Loop.merge` fails, and the loop goes round again: `rebase` then the gate.
This holds for a grooming pass too, which gates nothing.

## Out of scope

- Refused fast-forwards that are not `moved`: `land-retries-a-passing-race`.
- `kick_back`, which builds its commit on `main` as it is when it commits.

## Done when

A test in `pair/test_pair.py` commits to `main` in the developer's checkout
from inside the fake gate while `Loop.merge` is gating, so between `merge`'s
rebase and the squash, and checks the result once the Issue lands. Each
commit goes to a path the branch does not touch, so every rebase is clean,
and the Issue's branch changes code, since `merge` gates only when
`touches_code()` holds. The checks:

- the change is still on `main`;
- the landed commit's parent is that commit, and its diff from it holds only
  the Issue's changes;
- `merge` gated again, on the branch rebased past that commit.

## The plan

**Where the window is.** In an easy Issue's run the gate is called first by
`requirement` for `in-progress` (`pair/loop.py`, after its own `rebase`).
`merge` then rebases again, and gates only if that rebase moved the branch
(or `force_gate`). A commit made during the `requirement` gate is caught by
`merge`'s rebase, so it does not reproduce the bug. The commit has to land
during `merge`'s own gate (the `self.gate` call inside its retry loop), which runs only when `main`
has already moved once since the `requirement` gate.

1. **Test first** (`pair/test_pair.py`). Add `Bench.during_gate:
   list[Action]`, popped and run on `bench.repo` at the start of each fake
   `gate` call, as `before_land` is for `land`. In a new `LoopTest` test,
   take an easy Issue through the script of
   `test_easy_issue_lands_as_one_squash_commit` with
   `write("a.txt", ...)`, and queue three gate actions:
   1. the `requirement` gate commits `b.txt` on `main` (so `merge`'s rebase
      moves and `merge` gates);
   2. `merge`'s gate commits `c.txt` on `main` (the window);
   3. the re-gate after going round does nothing.

   Assert `landed`, that `c.txt` and `b.txt` are on `main`, that `main~1`
   is the `c.txt` commit, that `git diff --name-only main~1 main` lists only
   `a.txt` and the Issue's files under `issues/`, and that `gate_runs == 3`.
   Run it and see it fail on `c.txt` before the fix.
2. **Fix** `Loop.squash`: reset softly to
   `git merge-base <main> HEAD` instead of `<main>`. `rebase` has just left
   the branch on top of the `main` it saw, so that commit is the merge base.
   If `main` has not moved, it is `main` itself and nothing changes. If it
   has, the ancestor check after `squash` in `merge` fails, the loop goes
   round, `rebase` replays the one squashed commit onto the new `main`, and
   `merge` gates again. Update the docstring to say what it resets to.
3. Run the new test and the rest of `pair/test_pair.py`.

**Risks.**
- The going-round now rebases the squashed commit, which already drops the
  slug from `ORDER`. A commit on `main` that also edits `ORDER` conflicts
  there; `rebase` resolves an `ORDER`-only conflict with `merge_order`, which
  should keep the drop. If a test shows otherwise, reset `ORDER` from `main`
  before squashing again rather than widening this Issue.
- `retirement` runs again on the second time round, but `move` has
  already set `st.stage` to `done`, so it answers `None` and no second move
  is made. A gate that fails on that round pauses with "main moved and the
  gate now fails on the squashed issue", as it does today.
- `LAND_TRIES` bounds the going-round, so a `main` that moves during every
  gate still ends in the "main kept moving" pause, as before.

## Notes

The plan held. `test_a_commit_on_main_while_merge_gates_is_not_reverted`
failed on `c.txt` before the fix, and passes after it with three gate runs.
`Bench.during_gate` is new: a queue of actions, one run on the developer's
checkout per fake gate call, for any test that needs `main` to move while a
gate runs. The `ORDER` risk did not arise, since the test's commits leave
`ORDER` alone, and no test covers a commit on `main` that edits `ORDER`
during the gate.

The test asserts the landed diff exactly: `a.txt` and
`issues/done/fix-typo.md`. The `Start` commit has already taken the Issue
out of `backlog/` and `ORDER` on `main`, so the landing touches neither.
`pair/README.md`'s Landing step now says that a commit on `main` during the
gate is rebased onto rather than reverted.
