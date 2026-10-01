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
the Issue on the next try as `d45b1919`.

Which race it was is not known, because git's error is in neither the pause
reason nor `.pair/events.jsonl`. Likely: the commit held the index lock or the
lock on `refs/heads/main` when the merge ran, had not yet moved `main` when
`land` checked for `moved`, and had released `index.lock` by the time `land`
looked for it. A ref lock's error does not name `index.lock` at all.

## Wanted

- The pause reason carries the tail of git's error.
- A failed fast-forward is tried again a few times, looking each time for
  `moved` and for a lock, before the loop pauses. It pauses at once only when
  the checkout has local changes to a path the landing would change.

## Out of scope

Pausing on real local edits in the way, which stays as it is.

## Done when

Tests in `pair/test_pair.py` show that a fast-forward refused once with
nothing in the way, and refused by a lock on `main`'s ref, both land without
a pause, and that a pause reason carries git's error.
