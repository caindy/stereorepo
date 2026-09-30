---
difficulty: easy
parent: flights
---

# Check a Flight as soon as its last part lands

A Flight whose parts have all landed is taken next, ahead of the running
order, so a plain `just pair` checks it and moves it to the desk check as soon
as its last part lands, whatever else is ripe. A delivered unit of value
waiting only for its check gains nothing by waiting behind unrelated Issues.
`just pair --once` still ends after one unit of work.

This comes from the developer's desk check of `flights`.

## Where it stands

`board.next_ripe` (`pair/board.py`) walks the backlog in running order: the
slugs `issues/backlog/ORDER` names, then every other backlog slug in filename
order. A Flight is ripe once every child is in `done/`, but it is taken only
when its turn in that order comes. A Flight ranked below other ripe Issues,
or not named in `ORDER`, therefore waits behind them after its last part has
landed. The loop (`pair/loop.py`, where it calls `next_ripe`) starts a Flight
check for a ripe slug that has children.

## What is wanted

- `next_ripe` returns a ripe Flight, one with children, all of them in
  `done/`, before any ripe Issue without children. Among ripe Flights, the
  running order still decides.
- The other ripeness rules are unchanged: a Flight with a `Needs elaboration`
  section, or with a `waits_on` not yet done, is not ripe and is not taken
  early. `skip` and `within` apply as before, so `just pair --flight <slug>`
  still works only that Flight and the Issues below it.
- `just pair --once` still ends after one unit of work: a Flight taken first
  is that unit.
- The `next_ripe` docstring and the running-order text in `pair/README.md`
  say that a ripe Flight goes first.

## Done when

- A test in `pair/test_pair.py` sets up a ripe Flight ranked below a ripe
  Issue without children in `ORDER`, and `next_ripe` returns the Flight.
- A test shows that a Flight with a child outside `done/`, or with a `Needs
  elaboration` section, is not taken ahead of a ripe Issue.
- `just gate` passes.
