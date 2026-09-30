---
difficulty: hard
---

# Groom the backlog while the loop works an Issue

A well-kept backlog has groomed work ready to pick up as the loop comes free.
Today grooming and implementation cannot run at once: `just groom` and
`just pair` share one worktree and one run lock, so a grooming pass waits for
the Issue underway, and the Issue waits for the pass. And while an Issue is
worked, its file on `main` stays in `backlog/`, so a pass that ran alongside
could edit the very Issue being implemented.

Grooming changes no code, only backlog Issue files and `ORDER`, so it needs no
coordination with implementation beyond keeping its hands off the Issue
underway and landing cleanly on a `main` that moves.

## What is wanted

- The Issue being worked is out of `backlog/` on `main` from the moment the
  loop starts it (`underway-on-main`).
- `just groom` runs alongside `just pair`, each in its own worktree, and each
  lands on `main` whatever the other has landed meanwhile
  (`groom-alongside-pair`).

## Done when

- With an Issue underway, `just groom` grooms and ranks the backlog and lands
  on `main`, and the Issue underway then lands too, with neither pausing for
  the developer.
- The board on `main` shows which Issue is underway.
- `just gate` passes.

## Desk-check brief

**What was delivered.** Grooming and implementation now run at once, and the
board on `main` shows what is being worked.

- `underway-on-main` (5ae2c37): when the loop starts an Issue or a Flight
  check, it first lands a commit on `main` that moves the file from
  `issues/backlog/` to `issues/underway/`. If that fast-forward is refused,
  nothing starts and the file stays in `backlog/`. `just pair-status` lists
  `underway` as a stage beside `backlog` and `done`.
- `groom-alongside-pair` (5f6942b, DR-300): `just groom` runs in its own
  worktree (`worktrees/groom`), under its own lock (`.pair/groom.lock`), and
  keeps its own state in `.pair/groom/`. The loop's refusals to run while the
  other is underway are gone. Each process lands on whatever `main` the other
  left:
  - A refused fast-forward, or one blocked by the other's `index.lock`, is
    rebased and retried up to five times before it pauses.
  - An `ORDER` conflict is resolved by `merge_order`, which rebuilds `ORDER`
    from `main`, keeping the pass's placements and dropping slugs that no
    longer have a file.
  - The loop does not start an Issue that a pass underway targets.
  - `just pair-status` shows both the pass and the Issue, each with a
    take-over line for its own worktree.

**Checked on this branch.** `just gate` passes, including 101 pair tests.
`AlongsideTest` in `pair/test_pair.py` runs a pass and an Issue in both orders
with neither pausing. It also covers:

- an `ORDER` conflict;
- a pass that loses a target to `underway/`;
- the loop skipping a pass's targets;
- a retried fast-forward;
- a lock that never clears;
- a leftover pass in `worktrees/pair`;
- status with both underway.

**Something to notice.** This Flight check was started with its file still in
`issues/backlog/`, and `issues/underway/` on `main` is empty, although the
check is underway. The supervisor that runs this check probably started
before 5ae2c37 landed, and so runs the older code. The next `just pair`
should move the Issue it starts into `underway/`.

**Worth trying.**

1. Start `just pair` on a ripe Issue. Check that `issues/underway/` on `main`
   holds it and that `just pair-status` names it.
2. While it runs, run `just groom` in a second terminal (or
   `just groom --rerank`). The pass should land on `main` without waiting, and
   the Issue should land after it with no pause. `ORDER` should keep the pass's
   placements and lose the landed Issue's line.
3. Run `just pair-status` while both are working. It should show two
   `underway:` blocks, one naming `worktrees/pair` and one naming
   `worktrees/groom`.
4. The first `just groom` provisions `worktrees/groom` with `just setup`, so
   expect that one-time delay.
