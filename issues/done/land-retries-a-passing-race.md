---
difficulty: medium
---

# Retry a fast-forward that a passing commit on `main` refused

`Loop.land` in `pair/loop.py` fast-forwards `main` in the developer's checkout
with `git merge --ff-only`. When that fails, it answers `moved` if `main` is no
longer an ancestor of the landing commit, waits and retries if it sees
`index.lock`, and otherwise pauses with "local edits in the way?". A commit
the developer makes on `main` at the same moment can fall through to that
pause, though nothing is in the way once it has finished.

## What happened

On 2026-10-01 at 13:52:32, `seat-git-signature-check-hangs` had passed its
gate and the loop tried to land it. In the same second a commit was made on
`main` in the developer's checkout (`182dc9c`). The loop paused with "could
not fast-forward main in your checkout to 9027372d (local edits in the
way?)". The checkout had no local changes afterwards, and `just pair` landed
the Issue on the next try as `d45b1919`. That landing also reverted an earlier
commit on `main`, which is a separate bug: `squash-reverts-commits-on-main`.

Which race it was is not known, because git's error is in neither the pause
reason nor `.pair/events.jsonl`. Likely: the commit held the index lock or the
lock on `refs/heads/main` when the merge ran, had not yet moved `main` when
`land` checked for `moved`, and had released `index.lock` by the time `land`
looked for it. A ref lock's error does not name `index.lock` at all.

## Wanted

- Every refusal that is not `moved` goes round the existing `LAND_TRIES` loop,
  calling `wait_for_lock` between tries, and checks for `moved` each time.
  Only after the last try does `land` pause.
- The exception: when the checkout has local changes (staged, unstaged or
  untracked) to a path that differs between `main` and `sha`, `land` pauses
  at once with the existing "local edits in the way" reason, naming those
  paths.
- A lock is either `index.lock` or the lock on `main`'s ref (both found with
  `git rev-parse --git-path`); the pause after the last try names whichever
  is still there.
- Every pause reason from `land` ends with the last few lines of git's stderr
  from the final try, trimmed to a few hundred characters.

## Out of scope

- How a pause on real local edits is answered: it stays as it is.
- `squash-reverts-commits-on-main`, and the other `LAND_TRIES` loops in
  `pair/loop.py`.

## Done when

Tests in `pair/test_pair.py`, using the bench's `before_land` hook, show:

- a fast-forward refused by `.git/refs/heads/main.lock`, which is gone by the
  next try, lands without a pause (the bench's `wait_for_lock` removes
  `main.lock` as well as `index.lock`, which is all it removes today);
- a fast-forward refused once with no lock and no local edits (`loop.git_run`,
  the name `land` calls, stubbed to fail its first `merge`) lands without a
  pause, after one `wait_for_lock`;
- local edits to a path the landing changes pause at once, with
  `lock_waits` still 0, and the reason names the path and carries git's error;
- a lock that stays pauses after `LAND_TRIES` tries, and the reason names the
  lock and carries git's error;
- local edits to a path the landing does not change do not pause the landing;
- the existing tests for a lock that stays, a refused fast-forward tried
  again, and local edits pausing still pass.

## The plan

Files: `pair/loop.py` (`Loop.land` and one new helper), `pair/test_pair.py`
(the bench and `AlongsideTest`), and the landing paragraph of `pair/README.md`.

1. **Edits in the way.** Add `Loop.edits_in_the_way(sha) -> list[str]`: the
   paths in `git diff --name-only -z <main> <sha>` that also appear in
   `git status --porcelain=v1 -z --untracked-files=all` in `self.repo`.
   Parse with `-z` so quoted and renamed paths come out plain; for a rename
   entry take both paths. An untracked file at a path `sha` adds counts, as
   git refuses to overwrite it.
2. **The loop in `land`.** Resolve both lock paths once: `index.lock` as now,
   and `git rev-parse --git-path refs/heads/<main>` plus `.lock`. Each try:
   merge; on success answer `landed`; if `main` is not an ancestor of `sha`
   answer `moved`; if `edits_in_the_way(sha)` is non-empty, break and pause at
   once; otherwise `wait_for_lock()` and go round. The wait is skipped after
   the last try. Keep `done.stderr` from the last merge.
3. **The pause reason.** Edits: "(local edits in the way: a, b); clear them".
   A lock still there after the last try: "(<lock> stayed in place); if no
   git process holds it, delete it", naming whichever lock exists. Neither:
   "(git refused it <LAND_TRIES> times)". All three then add ", then run
   again" and git's error: the last three non-empty lines of `stderr`, joined
   with " / " and cut to the last 300 characters, in the form
   `(git: …)`. Put that tail in a small module-level function so the tests do
   not depend on the exact cut. The branch-check pause at the top of `land`
   has no git error and stays as it is.
4. **Docstring and README.** Rewrite `land`'s docstring to say that any
   refusal is tried again unless local edits overlap the landing. The
   docstrings of `wait_for_lock` and `LOCK_WAIT` say they wait for the index
   lock; reword them to "the other process's git command (a lock, or a commit
   in flight)", since every retry now goes through them.
   In `pair/README.md` (the paragraph ending "local edits in the developer's
   checkout still pause it at once"), say that a lock on `main`'s ref or any
   passing refusal is also tried again, and that only edits to the paths the
   landing changes pause at once.
5. **Tests**, next to `test_a_refused_fast_forward_is_tried_again`:
   - Bench: `wait_for_lock` also unlinks `.git/refs/heads/main.lock`.
   - `test_a_lock_on_mains_ref_is_waited_out`: `before_land` writes
     `main.lock`; the landing answers `landed`, `lock_waits == 1`.
   - `test_a_refusal_with_nothing_in_the_way_is_tried_again`: wrap
     `loop.git_run` with `mock.patch("loop.git_run", ...)` so its first
     `merge` returns a `CompletedProcess` with return code 1 and a stderr,
     and every other call goes to the real one; `landed`, `lock_waits == 1`.
   - Extend `test_local_edits_still_pause_a_landing`: `lock_waits == 0`, and
     the reason contains `x.txt` and `git:`.
   - Extend `test_a_lock_that_stays_pauses_and_says_so`: the reason contains
     `git:` and the `index.lock` error text.
   - `test_edits_the_landing_does_not_touch_do_not_stop_it`: `before_land`
     writes an untracked `notes.txt` and appends a line to the tracked
     `.gitignore` the bench commits, which no landing touches; `landed`, and both edits survive.

Risky:

- `git status` while `index.lock` is held: it should still print, as it only
  writes the index opportunistically. If it fails, treat its failure as no
  edits and keep going round, so a lock is never read as edits.
- The `moved` check must still come before the edits check, or a moved
  `main` whose new files collide with the checkout would pause instead of
  rebuilding.
- A real refusal with nothing visible in the way now costs
  `LAND_TRIES × LOCK_WAIT` (2.5 s) before it pauses. That is acceptable.

## Notes from the work

- **A ref lock leaves the landing half done.** When `merge --ff-only` cannot
  lock `refs/heads/main`, it has already written `sha`'s tree into the index
  and working tree, so every path the landing changes shows as a local
  change. Step 1 as planned read that as edits in the way and paused at once.
  (On 2026-10-01 the old `land` paused because the ref lock's error does not
  name `index.lock`; the half-written checkout is also why the next
  `just pair` could land it.) `edits_in_the_way`
  therefore counts a tracked path only when its content differs from `sha`
  (`git diff --name-only <sha>`); untracked paths still always count. The
  next try then finishes the fast-forward.
- **Git's error tail keeps the `fatal:` and `error:` lines.** After an
  `index.lock` error git prints four lines of advice, which pushed the line
  naming the lock out of a plain last-three-lines tail. `git_error` keeps the
  last three `fatal:`/`error:` lines, or the last three lines when there are
  none. `GIT_ERROR_TAIL` (300) is the cut.
- **The half-done landing outlives a `moved`.** If the other process moves
  `main` after a ref-lock refusal, `land` answers `moved` and leaves the
  refused tree staged in the checkout, where it reverts the other process's
  commit. That was so before this change too, and is written up as
  `land-leaves-a-half-landed-checkout`.
