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
  and `issues/backlog/README.md` say that a ripe Flight goes first.

## Done when

- A test in `pair/test_pair.py` sets up a ripe Flight ranked below a ripe
  Issue without children in `ORDER`, and `next_ripe` returns the Flight.
- A test shows that a Flight with a child outside `done/`, with a `Needs
  elaboration` section, or with a `waits_on` not yet done, is not taken ahead
  of a ripe Issue.
- `just gate` passes.

## The plan

1. **`pair/board.py`, `next_ripe`.** Keep the single walk in running order
   and the ripeness test as it is. Pull the test into a local `ripe(slug)`,
   and record the first ripe slug found. Return straight away a ripe slug
   that is a key of `kin` (`families`), which means it is a Flight. After the
   first ripe Issue without children has been found, go on walking and test
   only slugs that are keys of `kin`, so the files of the other slugs are not
   read. At the end, return the first ripe slug found, or None. `skip` and
   `within` filter every slug first, as they do now, so `--flight` and the
   loop's `skip` callers keep their behaviour. Rewrite the docstring: a ripe
   Flight is taken before any other ripe Issue, and among ripe Flights the
   running order decides.
2. **Docs.** In `pair/README.md`, add a sentence where the Flight check is
   described (after "Once the last one lands, the loop takes the Flight
   through the Flight check") saying that a ripe Flight is taken ahead of
   the running order, and qualify "`just pair` takes the Issues in the
   running order as it stands" under "Grooming the backlog" to match. In
   `issues/backlog/README.md`, change
   "takes the first ripe Issue in running order" so that it says a ripe
   Flight goes first.
3. **Tests, `pair/test_pair.py`, `BoardTest`.** Add
   `test_a_ripe_flight_goes_first`. Backlog holds `a` (no children) and `big`,
   with `ORDER` set to `a\nbig\n`, and `done/part` names `parent: big`; assert
   `next_ripe` returns `big`. Then check each case that keeps `big` from being
   ripe, where `next_ripe` must return `a`:
   - `part` moved back to `backlog/`;
   - `big` given a `# Needs elaboration` section;
   - `big` given `waits_on: [z]` with `z` not done.
   Also assert that with two ripe Flights the one `ORDER` names first wins,
   and that `skip=frozenset({"big"})` returns `a`.
4. Run `just gate pair` while working, then `just gate`.

**Risk.** This changes which Issue the loop takes, so any test that expected
a leaf ahead of a ripe Flight would now fail. I read the existing
`next_ripe` assertions (in `LoopTest`, `FlightCheckTest` and `BoardTest`)
and none of them sets that up, so none should change. The loop needs no
change, because it already starts a Flight check for a ripe slug with
children (`pair/loop.py`, after its `next_ripe` call), and `--once` already
stops after that unit of work.

## Notes

- `next_ripe` still goes through the running order once. It remembers the
  first ripe Issue without children. After that it tests only slugs that
  `families` lists as parents, so reading the rest of the backlog costs no
  more file reads than it did before.
- The plan held. The test is `BoardTest.test_a_ripe_flight_goes_first`. No
  existing test changed. `pair/loop.py` needed nothing, because it already
  starts a Flight check for a ripe slug that has children.
- `issues/backlog/README.md` now also says when a Flight is ripe, since its
  ripeness sentence covered only `waits_on` and `Needs elaboration`.
- `pair/loop.py`'s module docstring and the `--flight` paragraph of
  `pair/README.md` also described the old order, so both now say a ripe
  Flight goes first. Under `--flight`, a ripe Flight below the one being run
  is likewise taken before its sibling Issues.
