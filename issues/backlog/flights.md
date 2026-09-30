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
