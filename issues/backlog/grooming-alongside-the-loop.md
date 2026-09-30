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
