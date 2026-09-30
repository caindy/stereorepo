---
difficulty: medium
parent: flights
waits_on:
  - flight-desk-check
---

# Run one Flight with `just pair --flight <slug>`

One part of `flights`.

## Wanted

`just pair --flight <slug>` works only the Flight's children (and any children
the Flight check or a resume adds), in running order, then the Flight's own
check. It stops when the Flight reaches `desk-check/`, when the developer is
needed (a pause, or a child's own desk check), or when no child is ripe. It
does not run the grooming pass. A slug that is not a Flight in `backlog/` is
refused with a message saying so.

## Out of scope

Running several Flights, and ranking Flights against each other.

## Done when

The pair tests show that, with another ripe Issue ranked first,
`--flight <slug>` lands exactly that Flight's children, runs its check, and
stops at its desk check; and that an unknown slug is refused. `just gate`
passes.
