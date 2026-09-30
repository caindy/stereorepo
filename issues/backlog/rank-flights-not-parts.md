# Rank Flights, not their parts

`issues/backlog/ORDER` gives every Issue a line of its own, a Flight's parts
included. So ranking a Flight means placing each of its parts, in their
`waits_on` order, and the Flight after them; a part left out of `ORDER` counts
as unlisted and is reached only after everything listed. The developer decides
which unit of value comes next. The order of a Flight's parts is a detail its
`waits_on` already settles.

## What is wanted

- **`ORDER` names only Flights and standalone Issues.** A part, an Issue that
  names a Flight in `parent:`, has no line of its own: it runs where its
  Flight's line is. A part that is itself a Flight runs where its parent
  Flight's line is, and its own parts with it.
- **The loop expands a Flight where it stands.** When `next_ripe` reaches a
  Flight's line, it takes the Flight's first ripe part, in the order the parts'
  `waits_on` gives and then by filename, and once every part has landed, the
  Flight's check, as now. A Flight whose parts are all waiting on something
  outside it is passed over, as a waiting Issue is. A ripe Flight still goes
  before any ripe Issue without children.
- **Grooming places Flights, not parts.** A grooming pass places each new
  Flight and standalone Issue in `ORDER`; splitting a `hard` Issue keeps that
  Issue's line, which now stands for the Flight it became, and writes no
  lines for the parts. `pair/prompts/grooming-place.md`,
  `pair/prompts/grooming-rerank.md` and `pair/prompts/stage-grooming.md` say
  so.
- **The board holds `ORDER` to it.** The `board order` step and the grooming
  faults refuse a line naming a part, and a pass that leaves a Flight or
  standalone Issue unplaced.
- **`ORDER` on `main` is migrated in the same change:** the lines for
  `underway-on-main` and `groom-alongside-pair` go, leaving
  `grooming-alongside-the-loop` where it is, and any other part's line with
  them.
- **The words follow:** `issues/backlog/README.md`, `issues/README.md`,
  `template/issues/README.md` and `pair/README.md` describe ranking by Flight.

## Out of scope

- How `just pair-status` shows the running order
  (`status-lists-what-waits-on-the-developer`).
- Running grooming alongside the loop (`groom-alongside-pair`).

## Done when

- With `ORDER` naming a Flight above a standalone Issue, the loop takes every
  part of the Flight, in `waits_on` order, and the Flight's check, before the
  standalone Issue.
- A grooming pass that splits a `hard` Issue keeps its line and adds none for
  the parts, and `board order` fails on a line that names a part.
- `ORDER` on `main` names no part.
- The pair tests cover each of these, and `just gate` passes.
