---
difficulty: medium
parent: flights
waits_on:
  - flight-check
---

# Desk-check a Flight on `main`, without holding the loop

One part of `flights`. An Issue's desk check today holds the worktree: the
loop pauses with `retry: desk-check` in `.pair/state.json` until
`just pair-accept` merges it or `just pair-resume` sends it back. A Flight's
parts are already on `main`, so its desk check gates nothing but the Flight
being called delivered, and should not stop the loop.

## Wanted

- A Flight that passes its check lands on `main` in `desk-check/`, whatever its
  difficulty, with its brief. The loop does not pause; it goes on to the next
  ripe Issue.
- `just pair-accept <slug>` moves a Flight in `desk-check/` to `done/` on
  `main`. `just pair-resume <slug>` turns the developer's desk-check notes in
  the Flight file into new child Issues, one per note, each with `parent:`
  naming the Flight, and returns the Flight to `backlog/` to wait on them.
  After they land it is checked again and returns to `desk-check/`.
- The Flight file keeps each round's brief and notes; a new round appends, it
  does not overwrite.
- Without a slug, `pair-accept` and `pair-resume` keep today's meaning (the
  Issue desk check holding the worktree). With a slug that names neither, they
  say so and change nothing. The recipes take the slug as an atomic
  identifier (DR-259, DR-272).

## Out of scope

`just deliver` (`flight-deliver`), `just pair --flight`, and showing Flights in
`pair-status` (`status-lists-what-waits-on-the-developer`).

## Done when

The pair tests show: a checked Flight lands in `desk-check/` and the loop
carries on; `pair-accept <slug>` moves it to `done/`; `pair-resume <slug>` with
two notes makes two children and returns the Flight to `backlog/`, and after
they land it returns to `desk-check/` with both rounds in its file. `just gate`
passes.
