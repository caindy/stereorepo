---
parent: grooming-alongside-the-loop
waits_on: [underway-on-main]
---

# Run `just groom` alongside `just pair`

`just groom` and `just pair` share the worktree `worktrees/pair` and the run
lock `.pair/run.lock`, so either refuses while the other runs.

## What is wanted

- **Grooming has its own worktree, lock and seats:** `worktrees/groom`,
  `.pair/groom.lock`, and its own session and log files, so a grooming pass and
  an Issue can run at once. Two grooming passes still cannot.
- **Grooming lands on `main` like an Issue:** on a short-lived branch, rebased
  onto `main` and fast-forwarded. It touches only `backlog/` and `ORDER`, and
  the Issue underway is in `underway/`, so the rebase is clean.
- **A refused fast-forward is retried.** When the other process lands first,
  `--ff-only` is refused. Each process then rebases onto the new `main` and
  tries again, a few times, before pausing for the developer. This applies to
  an Issue's landing as much as to a pass's.
- `pair/README.md` says that the two may run at once, and what each holds.

## Done when

- A grooming pass started while an Issue is underway lands, and the Issue
  lands after it, and the reverse, with neither pausing.
- The pair tests cover a refused fast-forward that succeeds on retry, and
  `just gate` passes.
