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
- The pair tests cover a refused fast-forward that succeeds on retry, and
  `just gate` passes.
