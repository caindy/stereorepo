---
difficulty: medium
---

# Put the checkout back when a fast-forward is refused at `main`'s ref

`git merge --ff-only` writes the landing's tree into the index and working
tree, releases `index.lock`, and only then locks `refs/heads/main` to move
it. `land-retries-a-passing-race` found this out: a fast-forward refused by
`main.lock` leaves every path the landing changes as a staged change in the
developer's checkout. Its next try finishes the fast-forward, so nothing is
lost when `main` has not moved.

When `main` has moved, though, it is lost. Two processes landing in the same
checkout (a grooming pass and the loop working an Issue) can meet in that
gap. A's merge releases the index and is about to move `main`. B's merge
writes B's tree, is refused at the ref, and A then moves `main`. `Loop.land`
in B answers `moved` and leaves the checkout's index and working tree holding
B's tree: A's changes now show as staged changes that revert them. B rebuilds
on A and fast-forwards again, and git keeps those staged changes because the
target matches `HEAD` for A's paths. The developer's next commit, or anything
that commits the index, reverts A.

## How to reproduce it

In a `Bench` (`pair/test_pair.py`), with an Issue the pair settles
(`land_the_issue`):

1. Put `[lambda _repo: None, hold_main]` in `b.before_land`, where `hold_main`
   writes `.git/refs/heads/main.lock` in the developer's checkout. The first
   entry is for the landing `start` makes.
2. Replace `b.loop.wait_for_lock` with a function that deletes the lock and
   then moves `main` the way the other process would, without touching the
   checkout's index: build a commit on `main` that changes a file the landing
   does not touch (`git hash-object -w`, `git mktree` or a temporary index
   with `GIT_INDEX_FILE`, then `git commit-tree`), and point `main` at it with
   `git update-ref`.
3. `b.loop.run(once=True)` answers `landed`, but `git status --porcelain` in
   the developer's checkout shows the moved file as a staged change back to
   its old content.

## Wanted

- When `land` answers `moved` after a try that git refused at `main`'s ref,
  every path that try wrote is put back to `main` (`HEAD`), in both the index
  and the working tree, before `land` returns. The paths are the ones the
  landing changes (`git diff --name-only <main before> <sha>`). The try wrote
  them only where no local edit stood in the way, since a fast-forward that
  meets a local edit writes nothing, so putting them back loses nothing of
  the developer's. A path that is not in the landing is never touched.
- When `land` pauses because `main`'s ref lock stays in place, the pause
  reason also says that the checkout holds the half-done landing as staged
  changes, and how to clear them (`git restore --staged --worktree` for the
  landing's paths, or let the next run finish the landing).

## Out of scope

- The retry rules in `land` itself (`land-retries-a-passing-race`).
- A refusal at `index.lock`, which writes nothing to the checkout.

## Done when

- A test in `pair/test_pair.py` follows the steps above and asserts that,
  after the Issue lands, `git status --porcelain` in the developer's checkout
  is empty, the moved file holds the moved `main`'s content in the checkout
  and on `main`, and the Issue is in `issues/done/` on `main`. The test fails
  without the change.
- A test has the developer's checkout hold a local edit to a file the landing
  does not touch during the same sequence, and asserts the edit is still
  there afterwards.
- A new test, like `test_a_lock_that_stays_pauses_and_says_so` but with
  `.git/refs/heads/main.lock` written in `before_land` and left in place
  (`wait_for_lock` does nothing), asserts that the loop pauses, that the
  reason names `main.lock` as staying in place, and that it holds the new
  sentence about the staged changes. No such test exists today: the existing
  one leaves `index.lock`, which writes nothing to the checkout.
