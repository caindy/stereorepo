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

## Done when

A test in `pair/test_pair.py` commits to `main` between the rebase and the
squash, and finds that commit's change still on `main` after the Issue lands.
