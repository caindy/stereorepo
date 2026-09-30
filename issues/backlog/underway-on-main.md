---
parent: grooming-alongside-the-loop
---

# Move the Issue being worked to `underway/` on `main`

While the loop works an Issue, its file on `main` stays in `backlog/`, and its
real stage exists only on its branch. So the board on `main` does not show what
is being worked, and anything that edits the backlog on `main` can edit the
Issue underway.

## What is wanted

- A new stage directory, `issues/underway/`, on `main` only. When the loop
  starts an Issue or a Flight check, it moves the file from `backlog/` to
  `underway/` on `main`, in a commit of its own, before the seats' first turn.
- The branch's own stages (`todo/`, `in-progress/`, `desk-check/`) are
  unchanged. The commit that lands the Issue moves it from `underway/` to
  `done/` (or to `desk-check/` for a Flight) on `main`. A send-back moves it
  from `underway/` back to `backlog/`.
- `next_ripe`, grooming and the board checks treat `underway/` as neither
  backlog nor done. `ORDER` may still name the Issue underway.
- A restarted supervisor finds the Issue underway where it left it.
- The stage tables in `issues/README.md`, `template/issues/README.md` and
  `pair/README.md`, a README in `issues/underway/`, the Stage concept in
  `.meta/assertions/imported/vocabulary.yaml`, and `just pair-status` show the
  new stage.

## Done when

- Starting an Issue moves its file to `underway/` on `main`, and landing it,
  sending it back and restarting the supervisor each leave it in the right
  place.
- The pair tests cover each of these, and `just gate` passes.
