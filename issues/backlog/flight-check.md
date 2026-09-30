---
difficulty: medium
parent: flights
---

# Keep a split Issue as a Flight, and check it when its last part lands

One part of `flights`. Today `retire_hard` in `pair/loop.py` moves a `hard`
Issue to `done/` as soon as its children are written, and the backlog stage
requires a `hard` Issue to have children in `backlog/`. So nothing checks that
the unit of value the parent described was delivered.

## Wanted

- **The parent stays.** A split `hard` Issue stays in `backlog/` (and in
  `ORDER`) as a Flight; `retire_hard` goes. `board.next_ripe` treats an Issue
  as not ripe while any Issue naming it in `parent:` is outside `done/`, as if
  it waited on each of them.
- **Children roll forward** as now: each lands on `main` when done, with no
  desk check unless it is itself `developer`.
- **The Flight check.** When a Flight is ripe (every child done), the loop takes
  it through a Flight check instead of todo and in-progress. The seats check
  its "Done when" end to end on `main` and either:
  - write each gap as a new child Issue with `parent:` naming the Flight; the
    children land on `main` and the Flight, back to waiting, stays in
    `backlog/`; or
  - write a `## Desk-check brief` section into the Flight file: what was
    delivered, where to see it, and what is worth trying.
  The check needs no change outside `issues/`, and the supervisor holds the
  seats to one of those two outcomes.
- A Flight that passes its check goes to `done/` in this part;
  `flight-desk-check` sends it to `desk-check/` instead.
- **`flights` becomes the first Flight.** The grooming pass that split
  `flights` ran `retire_hard`, so `flights` is in `issues/done/` and out of
  `ORDER` when this part starts. Move it back to `issues/backlog/`, so it waits
  on its remaining parts and gets its own Flight check once they land. Put it
  back at the top of `ORDER`, above `# groomed below`, where the developer
  placed it. The board checks allow this: a backlog Issue that
  `ORDER` names.
- The backlog-stage requirement that a `hard` Issue have children counts
  children in any stage, so a Flight with landed children is not asked to split
  again.

## Out of scope

The desk check of a Flight, `just deliver`, `just pair --flight`, and the
vocabulary; each is its own part of `flights`.

## Done when

The pair tests show: a split `hard` Issue stays in `backlog/` and is not ripe
while a child is outside `done/`; once all its children land the loop runs the
Flight check; a gap written in the check produces a child and the Flight waits
again; a clean check writes the brief and retires the Flight. `flights` is
back in `issues/backlog/` and first in `ORDER`, and `just gate` passes.
