---
parent: grooming-alongside-the-loop
waits_on: [underway-on-main]
difficulty: medium
---

# Run `just groom` alongside `just pair`

`just groom` and `just pair` share the worktree `worktrees/pair`, the run lock
`.pair/run.lock`, and the supervisor state `.pair/state.json`. `Loop.run`
refuses while that state holds a grooming pass, and `Loop.groom` refuses while
it holds an Issue, so either waits for the other.

## What is wanted

- **Grooming has its own worktree, lock and state:** `worktrees/groom`,
  `.pair/groom.lock`, and its own state, seat session, pid and log files, so a
  grooming pass and an Issue can run at once. The two refusals above go. Two
  grooming passes still cannot run at once, nor two Issues.
- **Grooming lands on `main` like an Issue:** on its short-lived branch,
  rebased onto `main` and fast-forwarded. It touches only `backlog/` and
  `ORDER`, and the Issue underway is in `underway/`.
- **`ORDER` never stops a pass from landing.** A landing drops its slug from
  `ORDER`, and a Flight's send-back puts its slug first, so a pass's edits to
  `ORDER` can conflict with `main` textually. When the rebase conflicts only in
  `ORDER`, the loop rebuilds it from `main`'s `ORDER` with the pass's
  placements inserted where the pass put them, minus any slug no longer in
  `backlog/`, and carries on. A pass places only Flights and standalone Issues
  (`rank-flights-not-parts`), and a part's landing drops no line.
- **A pass and the loop do not work the same Issue.** While a pass is
  underway, `next_ripe` skips the Issues the pass targets (its `skip`
  argument). A pass started while an Issue is underway does not target it,
  since it is not in `backlog/`.
- **A refused fast-forward is retried.** When the other process lands first,
  `git merge --ff-only` in the developer's checkout is refused, or fails on
  the other's index lock. Each process then rebases onto the new `main` and
  tries again, a few times, before pausing for the developer. `land` tells
  this apart from local edits in the developer's checkout, which still pause
  at once. This applies to an Issue's landing and a send-back as much as to a
  pass's.
- **The board shows both.** `just pair-status` reads the pass's state as well
  as the Issue's, and shows each one that is underway, paused or not, with the
  sessions to take over in its own worktree. A pause message from a pass names
  `worktrees/groom`, not `worktrees/pair`.
- **The words follow:** `pair/README.md` says that the two may run at once,
  and what each holds.

## Out of scope

- More than one Issue at a time.
- The event log and `just pair-watch` (`flight-instruments`).

## Done when

- A grooming pass started while an Issue is underway lands, and the Issue
  lands after it, and the reverse, with neither pausing.
- A pass whose `ORDER` edits conflict with a landing that dropped a slug lands,
  with its placements kept and the dropped slug gone.
- The loop does not start an Issue that a pass underway targets.
- With both underway, `just pair-status` shows the pass and the Issue.
- The pair tests cover each of the above, with fake seats, and a refused
  fast-forward that succeeds on retry; `just gate` passes.

## The plan

### Seams

- **One `Loop` per process kind.** `Loop.__init__` takes `kind: str = "pair"`.
  `self.wt` becomes `worktrees/<kind>`. `self.dir` stays `.pair` for `pair` and
  becomes `.pair/groom` for `groom`. That one directory then holds the kind's own
  `state.json`, `<role>.session`, `<role>.pid`, `<role>.jsonl` and `.log`, and
  `turns.jsonl`. `reap`, `saved_session` and `record` already key off
  `self.dir`, so they do not change. `save` and `record` call `mkdir` without
  `parents=True`, and `.pair/groom` needs it on a fresh clone. Every message
  that names `worktrees/pair` (`start`, `decide`, `advance`, `rebase`) uses
  `self.wt.relative_to(self.repo)` instead.
- **What does not key off the loop yet.** `pair.py:main` hardcodes the
  `ClaudeSeat` log directory as `repo / ".pair"`, so the seat factory takes the
  directory from the kind (`.pair/groom` for `groom`). `provision` and
  `deliver` print `worktrees/pair`, so they print the tree they were given.
  A pass runs `just gate` (`requirement`), so `worktrees/groom` is
  provisioned by `just setup` like `worktrees/pair`.
- **Locks.** `hold_lock(repo, name)`: `pair run`, `accept` and `resume` take
  `run.lock`, and `pair groom` takes `groom.lock`. In `pair.py:main`, `groom`
  builds its `Loop` with `kind="groom"`. `status` builds neither.
- **The refusals go.** Drop the `GROOMING` check in `Loop.run` and the "is
  underway" check in `Loop.groom`, and update both docstrings. Neither kind
  can load the other's state any more, so no guard is needed in their place,
  except for one left over from before this change. A `.pair/state.json` whose
  stage is `GROOMING` is a pass that was paused in `worktrees/pair`. `run`
  discards it: it says so, detaches `worktrees/pair` at `main`, deletes
  `pair/grooming` so that `worktrees/groom` can check that branch out, and
  clears the state. A pass is cheap to run again, and nothing it did had
  landed. `groom` does the same before it starts a pass. Otherwise its
  `checkout -B pair/grooming` fails, because git refuses to check out a
  branch that another worktree has checked out. Both call one helper,
  `discard_old_pass(repo)`, which does nothing when `.pair/state.json` is
  missing or holds an Issue.
- **Skip what a pass targets.** A module-level helper, `groom_targets(repo)`,
  reads `.pair/groom/state.json` and returns its `targets` as a frozenset,
  empty when the file is missing. `run` passes it as `skip=` to
  `board.next_ripe` on each pick. A paused pass keeps its state file, and so
  still counts as underway.
- **Rebuild `ORDER` from `main` (a new pure function in `board.py`).**
  `merge_order(ours, base, theirs, top) -> str`. `ours` is `main`'s
  `ORDER`, `base` is `ORDER` at `st.base`, and `theirs` is the pass's `ORDER`.
  `top` is the set of top-level backlog slugs in the conflicted worktree, which
  is `main` plus the pass. It is the backlog less its `parts`, read from the
  tree as `grooming_faults` does. This way a slug the pass made a part, and a
  part of a Flight that `resume_flight` sent back meanwhile, both lose their
  lines.
  - Above the marker, the lines are `ours`' (they belong to the developer or
    to `resume_flight`, which puts a sent-back Flight first there).
  - Below the marker, without rerank, start from `ours`' lines. Insert each
    slug the pass placed (below the marker in `theirs` but not in `base`) after
    the nearest earlier slug in `theirs` that is already in the result, or
    straight after the marker if there is none.
  - Below the marker, with rerank, keep `theirs`' order, then append any slug
    from `ours` that is not in it.
  - Finally, drop any slug not in `top`, and any slug named twice. The first
    naming is kept, so a line above the marker wins.
- **A pass's rebase.** `Loop.rebase`, for `GROOMING` only, first squashes the
  branch onto `st.base` (`reset --soft` plus one commit), so that at most one
  commit is replayed. If `git rebase` then conflicts, and `git diff
  --name-only --diff-filter=U` is exactly `ORDER`, the loop writes
  `merge_order(...)`, runs `git add`, and continues with
  `GIT_EDITOR=true git rebase --continue`. Any other conflict aborts and
  pauses, as it does today. After a successful rebase, the loop checks out
  from `main` every path outside `issues/backlog/` that the pass changed. This
  drops an edit that git's rename detection carried onto an Issue that moved
  to `underway/` meanwhile (see Risks).
- **A retry when `land` is refused.** `land` returns
  `"landed" | "moved" | "paused"` instead of a bool. After `merge --ff-only`
  fails, the loop checks two things. If `main` is no longer an ancestor of
  `sha`, the result is `"moved"`. If `.git/index.lock` exists, or stderr names
  `index.lock`, it sleeps briefly and retries the fast-forward, up to 5 times.
  Only failures other than these pause, as today, for local edits. That needs
  a `git_run` in `board.py` that returns the exit code and stderr. The callers
  handle `"moved"` as follows:
  - `merge` already loops: it raises its round count from 3 to 5 and treats
    `"moved"` like the existing `is-ancestor` miss.
  - `move_underway` rebuilds its commit from the new `main` and tries again,
    up to 5 times.
  - `kick_back` does the same: it checks out the new `main` and writes the
    same `kick_text` again.
- **Status.** `status()` loops over `(".pair", "worktrees/pair")` and
  `(".pair/groom", "worktrees/groom")`, printing an `underway:` block for each
  state file it finds. Each block shows the paused reason and a take-over line
  for its own worktree. The text for a single state stays as it is today. The
  "last turns" tail reads each directory's `turns.jsonl`.
- **README.** Rewrite the paragraph under "Grooming the backlog" in `pair/README.md` that opens "A pass and an Issue share", which says the two
  wait for each other. Also update the runtime-state table (`.pair/` versus
  `.pair/groom/`, and the two locks) and the watch, steer and take-over rows,
  so that each names both worktrees.

### Order

1. `kind`, `self.dir` and `self.wt`, the path-free messages, `hold_lock(name)`,
   and `main`, with the seat log directory and the `provision` and `deliver`
   messages. Drop the two refusals, and discard a leftover pass state. The existing tests must still pass
   unchanged.
2. `groom_targets` and `skip=` in `run`.
3. The tri-state `land` and its three callers.
4. `merge_order` and the pass's rebase path.
5. `status()`, then the README.

### Tests (`pair/test_pair.py`)

- The `Bench` gains a second loop, `bench.groomer`, with `kind="groom"` and the
  same fake seats and gate. Its scripted turns live on their own deque, so the
  two loops can be interleaved within one test. `FakeSeat` today writes its
  session into `bench.loop.dir` and sets `bench.loop.stop_requested`, so it
  takes the loop it serves, and its deque, from the factory instead.
- **An Issue started, then a pass run to landing, then the Issue run to
  landing.** Neither pauses. `main` holds both, and `ORDER` has lost the
  Issue's slug and kept the pass's placements. A second test does it the other
  way round: a pass started, an Issue landed, then the pass landed.
- **A pass whose `ORDER` conflicts textually** with an Issue landing that
  dropped the line next to its placement. It lands, the dropped slug is gone,
  and the placement is kept. `merge_order` also gets direct unit tests in
  `BoardTest`: an insertion by anchor, a slug dropped from `backlog`, a slug the
  pass made a part, a
  send-back line added above the marker on `main`, and rerank.
- **A saved pass state whose `targets` include the only ripe Issue.**
  `run` returns `"empty"`, and with another ripe Issue it takes that one.
- **A pass that loses a target.** A pass targets X and edits it; X is then
  started by `run` (it moves to `underway/` on `main`) before the pass lands.
  The pass lands, and `underway/X.md` on `main` is unchanged by it. `run`
  skips a target, so the test starts X before it saves the pass's state, which
  reproduces the race described under Risks.
- **A retry after a refused fast-forward.** A `TestLoop.land` hook advances
  `main` in the developer's checkout (a commit by a "developer") just before
  the first `merge --ff-only`. The Issue still lands. The same test is run
  for `move_underway` and `kick_back`. A second hook leaves an
  `index.lock` in the developer's `.git` for the first attempt only, and the
  fast-forward then succeeds without a pause. The existing local-edits test
  still pauses.
- **A leftover pass state.** A `.pair/state.json` with stage `GROOMING` and a
  `pair/grooming` branch in `worktrees/pair` is discarded by `run`, which then
  works the backlog, and a `groom` after it can check out `pair/grooming`.
  With the same leftover, `groom` run first discards it and then starts its
  pass in `worktrees/groom`.
- **Status with both states present.** The output shows both, each with its
  own worktree in the take-over line.
- **The two locks.** `hold_lock(repo, "groom.lock")` succeeds while
  `run.lock` is held.
- `just gate` passes.

### Risks

- **An Issue picked at the moment a pass starts.** The loop may pick an Issue
  in the window after it reads the pass's (not yet saved) targets and before
  `move_underway` lands, while the pass reads `backlog/` in the same window.
  The pass may then target, and edit, a file that is now in `underway/`. On
  rebase, git's rename detection carries that edit onto `underway/<slug>.md`.
  The checkout from `main` of paths outside `issues/backlog/` after the rebase
  throws that edit away. `grooming_faults` does not trip on it: it compares
  the unrebased branch with `st.base`, where the target is still in
  `backlog/`.
- **A shared `.git`.** Ref updates and each worktree's own index are safe
  under git's own locking. The only lock the two processes share is the
  developer's-checkout `index.lock`, which the retry handles. `accept` and
  `resume` with a Flight slug commit in the developer's checkout without the
  loop (`commit_move`). If they meet the other process's `index.lock`, they
  fail with git's own message, and the developer runs them again. That is
  left as it is.
- **Two gates at once.** A grooming pass runs `just gate` in
  `worktrees/groom`, and an Issue runs it in `worktrees/pair`. Each worktree
  has its own build outputs. If the gate turns out to share a build directory
  (outside the worktree), write that as a new backlog Issue rather than fix it
  here.
- **Squashing the pass branch before rebase** loses its turn-by-turn commits
  once a landing has started. They are squashed on `main` anyway. A pause
  after the squash resumes from the squashed branch, and `retry="merge"`
  handles that.

## Notes

What the work changed from the plan, for the next reader:

- **`ORDER` is rebuilt on any branch's rebase, not only a pass's.** When
  `land` answers `moved`, `merge` replays the Issue's squash commit, which
  drops the Issue's line from `ORDER`, onto the new `main`. That can conflict
  with a pass's placement next to it, exactly as a pass's can. So
  `Loop.rebase` resolves an `ORDER`-only conflict for either kind, passing
  `st.rerank` (always false for an Issue).
- **`merge_order` keeps the Issue underway's line.** `keep` is
  `board.order_keeps(tree)`: the top-level backlog slugs *and* the slugs in
  `underway/`. Dropping everything not in `backlog/`, as the Issue first said,
  would take the line of the Issue being worked out of `ORDER` whenever a pass
  landed with a conflict. That Issue's own landing drops the line anyway, and
  a send-back needs the line to keep its place.
- **The squash before a pass's rebase is onto the merge-base, not
  `st.base`.** After a `moved` retry, the pass branch already sits on a later
  `main` than `st.base`. Resetting to `st.base` would fold `main`'s own
  commits into the pass.
- **Waiting for the index lock is `Loop.wait_for_lock`, not a `land_wait`
  attribute.** The test loop overrides it to remove the lock, which stands for
  the other process finishing, so the test sleeps for nothing and is
  deterministic.
- **The test bench shares one deque of scripted turns between `b.loop` and
  `b.groomer`.** The tests call one loop at a time, so the two never draw
  turns at once. `FakeSeat` takes the loop it serves from the factory, and
  sets that loop's `stop_requested`. The grooming tests now call
  `b.groomer.groom()` and read `b.state(b.groomer)`. The two tests that
  asserted the old refusals (`busy` and `grooming`) were rewritten: a desk
  check no longer stops `groom`, and `AlongsideTest` covers both orders.
- **DR-300** records the decision that a pass runs alongside the loop.
- **A lock that never goes away pauses, and says so.** A crashed git process
  can leave `.git/index.lock` behind. `land` then used the "local edits"
  pause message after its retries. It now names the lock and says to delete it
  if no git process holds it
  (`test_a_lock_that_stays_pauses_and_says_so`).
- **A rebuilt `ORDER` can empty the commit it resolves.** If the branch's only
  `ORDER` change is a line that `keep` drops, `rebase --continue` drops the
  now-empty commit, and the rebase still succeeds, so no `--skip` is needed
  (`test_a_rebuilt_order_that_undoes_the_commit_skips_it`).
