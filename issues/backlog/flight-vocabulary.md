---
difficulty: medium
parent: flights
waits_on:
  - underway-not-in-flight
  - flight-desk-check
---

# Name the Flight in the vocabulary and the docs

One part of `flights`.

## Wanted

- **Flight** becomes a concept in `.meta/assertions/imported/vocabulary.yaml`:
  an Issue with children, holding one unit of value and how the developer will
  know it has been delivered; its parts are *in flight*. The scope note says
  what it is not: not a time-box (a Sprint) and not a tracker's Milestone.
- "Parent issue" in the Issue concept and in the `Issue` class description is
  replaced by Flight. The Desk check concept says a Flight's desk check comes
  after its parts have landed on `main`.
- A wiki page `wiki/stereorepo/flight.md`, scaffolded and checked with
  `/wikisplain` (A17, DR-190).
- `pair/README.md`'s stage table, `issues/README.md` and
  `template/issues/README.md` describe the Flight's path: waiting in
  `backlog/`, the Flight check, `desk-check/`, `done/`.
- A Decision Record for the choice of Flights over a desk check per part.
- Re-render.

## Out of scope

Changing Flight behaviour; the other parts of `flights` do that.

## Done when

The concept, the wiki page and the Decision Record exist, the READMEs describe
the Flight's path, and `just gate` passes.
