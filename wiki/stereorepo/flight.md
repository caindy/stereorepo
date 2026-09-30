---
slug: flight
context: stereorepo
synonyms:
  - parent Issue
minted: 2026-09-30
---

# Flight

**Flight** is an [[issue|Issue]] with children, holding one unit of value and how the [[developer]] will know it has been delivered (stereorepo's DR-298).

## What makes an Issue a Flight

No field marks a Flight. An Issue becomes one when another Issue names it in
its `parent:` front matter, whether grooming split it because it was `hard` or
the developer wrote its children by hand. Its children are its parts, and
while they are being worked the Flight is *in flight*. A child can itself be a
Flight, with parts of its own.

A Flight's file says what value it delivers and, under "Done when", how the
developer will know that value has been delivered. Its parts say how the value
is built. The parts are small enough for the pair to land one at a time; the
Flight is the unit the developer cares about.

## Its path through the board

A Flight waits in `backlog/` while its parts land on `main`, each as its own
Issue. Once the last part is in `done/`, the pair takes the Flight through the
Flight check: the seats check its "Done when" end to end on `main`, and either
write each gap as a new part or write a desk-check brief. With a brief, the
Flight moves to `desk-check/`, and the developer [[desk-check|desk-checks]] the
delivered value once, instead of desk-checking each part.

Because its parts are already on `main`, a Flight's desk check does not hold
the loop. Accepting it moves it to `done/`; notes and a resume return it to
`backlog/`, where the next Flight check writes each note as a new part. The
mechanics are the pair loop's: the developer answers with
`just pair-accept <slug>`, or writes `## Desk-check notes` in the Flight's file
and runs `just pair-resume <slug>`.

## What a Flight is not

- **Not a Sprint.** A Sprint is a time-box: it ends on a date, and whatever is
  unfinished rolls over. A Flight has no date; it ends when its value is
  delivered and the developer has checked it.
- **Not a Milestone.** A tracker's Milestone is a label that groups tickets and
  holds nothing of its own. A Flight is itself an Issue on the board, with its
  own file and its own statement of how its delivery will be known.
- **Not an epic.** An epic is a large story broken into smaller ones for
  planning. A Flight exists so that the developer checks delivered value once,
  on `main`, rather than each part before it lands.

---

**See also:** [[desk-check]], [[ubiquitous-language]]
