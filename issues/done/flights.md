---
difficulty: hard
waits_on: [flight-desk-check, flight-deliver, pair-flight-option, flight-vocabulary]
---

# Land a parent Issue as a Flight, and desk-check the Flight

Serial work is organised in windows of Issues that together deliver one unit
of value, such as a feature. When people worked in parallel, a window like that
needed up-front coordination so its parts could run concurrently. Here the
parts run one after another, so the coordination shrinks to saying what the
unit of value is and how anyone will know it has been delivered.

The board already groups Issues this way: a `hard` Issue is split into child
Issues that name it in `parent:`. But the parent moves to `done/` as soon as its
children are written, before any of them is built. Nothing records that the
unit of value was delivered, there is no point at which the developer reviews
it, and nothing can run "until this lands".

## What is wanted

- **A Flight is an Issue with children.** It holds the unit of value: what it
  is for, and how the developer will know it has been delivered. Its children
  name it in `parent:`, and `waits_on` orders them within it. No new front
  matter: `hard` means "split this into a Flight", and the developer can also
  write a Flight directly, by writing its children with `parent:`.
- **Its parts roll forward.** Each child lands on `main` as it is done, as
  Issues do now. A child gets no desk check of its own unless the developer
  marks it `developer`: the developer reviews the Flight, not its parts.
- **A Flight is checked by the pair when its last child lands.** The parent
  stays in `backlog/` and is not ripe while any child is not in `done/`. Once
  every child has landed, the loop takes the Flight: the seats check its "done
  when" end to end on `main`, write any gap as a new child Issue (which puts
  the Flight back to waiting), and write a desk-check brief into the Flight
  file: what was delivered, where to see it, and what is worth trying. The
  Flight needs no code change of its own.
- **Delivery is the repository's.** When the Flight check passes, the loop runs
  `just deliver` if the repository defines that recipe, for example a
  redeployment to a UAT environment, and it moves the Flight to
  `desk-check/`. The loop never knows how a product deploys, as it never knows
  how a worktree is provisioned (`just setup`).
- **The desk check is the Flight's backlog of the developer's review.** Every
  Flight ends in `desk-check/`, whatever its difficulty; `main` already holds
  its parts, so the desk check gates nothing but the Flight being called
  delivered.
  - `just pair-accept` moves the Flight to `done/`.
  - `just pair-resume` turns the developer's desk-check notes in the Flight
    file into new child Issues of the Flight, each naming it in `parent:`, and
    returns the Flight to `backlog/` to wait on them. They land, the Flight is
    checked and delivered again, and it returns to `desk-check/`. The Flight's
    file keeps the history: each round's brief and notes stay in it.
- **Run a Flight.** `just pair --flight <slug>` works only that Flight's
  children, in running order, and stops when the Flight reaches
  `desk-check/` or the developer is needed.
- **"In flight" is retired.** Today "the Issue in flight" means the one Issue
  the loop is working. That use goes, so that "in flight" can only mean a part
  of a Flight: the Issue being worked is *underway*. The phrase appears in
  `pair/loop.py` (`status`), `pair/pair.py`, `pair/README.md`,
  `issues/README.md`, `template/issues/README.md`, `AGENTS.md`, the `justfile`
  render in `.meta/lib/render/writers.py`, `.gitignore` and
  `issues/backlog/cockpit-status-convention.md`.
- **The words follow.** Flight becomes a concept in
  `.meta/assertions/imported/vocabulary.yaml`, with a scope note saying what
  it is not: not a time-box (a Sprint) and not a tracker's Milestone. "Parent
  issue" in the Issue concept and the `Issue` class description is replaced by
  it, and the Desk check concept says a Flight's desk check comes after its
  parts have landed. `pair/README.md`'s stage table describes the Flight's
  path.

## Parts

Split by grooming, in landing order: `underway-not-in-flight`,
`flight-check`, `flight-desk-check`, then `flight-deliver`,
`pair-flight-option` and `flight-vocabulary`. `flight-check` and
`flight-desk-check` carry the core; the other parts wait on
`flight-desk-check`, except `underway-not-in-flight`, which waits on nothing.

## Out of scope

- Grouping Flights, or ranking them against each other beyond the running
  order `issues/backlog/ORDER` already gives.
- A release gate after a Flight is accepted, such as production deployment.
- Flights that span repositories.

## Done when

- A `hard` Issue's parent stays in `backlog/` until its last child lands, then
  passes the pair's Flight check, runs `just deliver` where the repository
  defines it, and waits in `desk-check/`.
- `just pair-resume` on a Flight creates one child Issue per note, and the
  Flight returns to `desk-check/` once they have landed.
- `just pair --flight <slug>` lands exactly that Flight's children and stops at
  its desk check.
- No text outside `WHY_FORK.md` uses "in flight" for the Issue being worked.
- The pair tests cover each of these, and `just gate` passes.

## Desk-check brief

**Delivered.** A parent Issue is now a Flight, carried from split to desk
check by the pair loop. All six parts are in `issues/done/`:
`underway-not-in-flight`, `flight-check`, `flight-desk-check`,
`flight-deliver`, `pair-flight-option` and `flight-vocabulary`. Each item of
"Done when" was checked on `main` at `fae5ab6`:

- A `hard` Issue's parent stays in `backlog/` while any child is outside
  `done/` (`board.py`, the pending-child check near its end). Once the last
  child lands, the loop gives the parent the Flight check
  (`pair/prompts/stage-flight-check.md`), runs `just deliver` where the
  repository defines it (`deliver` in `pair/pair.py`), and moves the Flight to
  `desk-check/`. This Flight is the first real run: it stayed in `backlog/`
  while its parts landed, and this check is what the loop gave it after the
  last one.
- `just pair-accept <slug>` moves a Flight to `done/`. `just pair-resume
  <slug>` returns it to `backlog/`, and the next Flight check writes one child
  per note and lists them under `## Desk-check children`.
- `just pair --flight <slug>` works only that Flight and the Issues below it,
  and stops at its desk check.
- Outside `WHY_FORK.md` and `issues/done/`, "in flight" is used only for a
  Flight's parts being worked: in the Flight concept
  (`.meta/assertions/imported/vocabulary.yaml`, `wiki/stereorepo/flight.md`).
  The Issue being worked is *underway*.
- `just gate` passes, including 67 pair tests. The tests covering the Flight
  are in `FlightCheckTest` and the `--flight` run tests in
  `pair/test_pair.py`, together with
  `test_a_flight_waits_until_every_child_is_done`.

**Where to see it.** `pair/README.md` has the stage table and the Flight
sections. `just pair-status` shows the board. The Flight concept is at
`wiki/stereorepo/flight.md` and in `.meta/vocabulary.md`.

**Worth trying.**

- Run `just pair-accept flights` to close this Flight. Or write a
  `## Desk-check notes` section here and run `just pair-resume flights`; the
  round trip back to `desk-check/` then runs on a real Flight.
- This repository defines no `deliver` recipe, so no delivery ran and this
  brief has no `Delivered by` line. To see a delivery, add a trivial
  `deliver` recipe on a scratch clone and land a small Flight there.
- Write a two-child Flight by hand (children naming it in `parent:`, with no
  `hard`), and run `just pair --flight <slug>` to see it stop at the desk
  check while other backlog Issues are left alone.

## Desk-check notes

- A Flight whose parts have all landed is taken next, ahead of the running
  order, so a plain `just pair` checks it and moves it to the desk check as
  soon as its last part lands, whatever else is ripe. A delivered unit of value
  waiting only for its check gains nothing by waiting behind unrelated Issues.
  `just pair --once` still ends after one unit of work.

## Desk-check children

- `flight-check-first`

## Desk-check brief

**Delivered.** The desk-check note is done. Its one child,
`flight-check-first`, landed at `8c4cfa6`, and it is in `issues/done/` with
the six first-round parts. A ripe Flight is now taken before any ripe Issue
without children, so a plain `just pair` checks a Flight and moves it to the
desk check as soon as its last part lands. Among ripe Flights, the running
order still decides. A Flight that has a part outside `done/`, a
`Needs elaboration` section, or a `waits_on` that is not done is not ripe, so
it is not taken early. `skip` and `within` work as before, so
`just pair --flight <slug>` still keeps to one Flight. `just pair --once`
counts the Flight check as its one unit of work. "Done when" was checked again
on `main` at `8c4cfa6`, and every item still holds. `just gate` passes,
including 68 pair tests.

**Where to see it.** `next_ripe` in `pair/board.py` and its docstring. The
test is `test_a_ripe_flight_goes_first` in `pair/test_pair.py`. The running
order is described in `pair/README.md` (the Flight section),
`issues/backlog/README.md` and the `pair/loop.py` module docstring.

**Worth trying.**

- Run `just pair-accept flights` to close this Flight. The round trip ran on a
  real Flight: `pair-resume`, then a check that wrote the note's child, then
  the child landing, then this check.
- This round did not test the new ordering on a real Flight, because
  `just pair-resume` had already put `flights` first in `ORDER`. To see it,
  write a two-child Flight by hand. Rank it below a ripe Issue in `ORDER`, or
  leave it out of `ORDER`. Let its children land, then check that
  `just pair --once` takes the Flight check before the other Issue.
