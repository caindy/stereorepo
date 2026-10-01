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

## Wanted

When `land` answers `moved` after a refused try, the checkout's index and
working tree hold `main` again for every path the refused try wrote, and no
local edit the developer had before the landing is lost. A pause left by a
ref lock that stays says the checkout holds the half-done landing.

## Out of scope

The retry rules in `land` itself (`land-retries-a-passing-race`).

## Done when

A test in `pair/test_pair.py` uses `before_land` to hold `main.lock`, then
moves `main` to a commit changing a file the landing does not touch before
the next check, and asserts that after the Issue lands, `git status` in the
developer's checkout is clean and the file holds the moved `main`'s content.
