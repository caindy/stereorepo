# Keep a seat's background work from outliving its turn

The loop takes a seat's turn as over when the turn's result comes back, and
it judges the turn quiet or not from the tree at that moment. A seat can start
a command in the background, end its turn, and be woken later by that
command's completion. Its session then goes on editing the worktree after the
loop has judged the turn, committed, or landed.

## What happened

On 2026-10-01, in the in-progress stage of `fresh-seat-after-refusal`, the
primary seat started `just gate pair` and `just gate meta` in the background
during its first turn and ended the turn. The loop committed the work, and
the secondary seat took turn 2. The loop recorded the primary seat's turn 3
at 11:27:20 as quiet, in 0.0 seconds, yet the primary session ran for about
170 more seconds, woken by its background gates. In that time it wrapped two
long lines it had added, in `pair/loop.py` and `pair/README.md` (11:27:27),
and reran the loop tests against them.

Since turn 3 counted as quiet, the loop moved the Issue to `done/` and landed
it as `30f3ab19` at 11:29:43 without the wrapping. It then paused before
`pair-watch-exit-codes` with "worktrees/pair has uncommitted changes from
before this issue". The developer committed the wrapping to `main` by hand.
The primary seat's session log is `.pair/primary.jsonl`, session
`fa68d3d4-86b7-408a-b0e5-65c1b60fc88d`, in the developer's checkout.

## What done looks like

No edit a seat makes reaches the worktree after the loop has judged that
seat's turn. Either a seat cannot leave work running in the background when
its turn ends, or the loop waits until the seat's session is idle, with no
background task outstanding, before it reads the tree. A test in
`pair/test_pair.py` covers a seat whose session edits the tree after its
turn's result.
