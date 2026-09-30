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

- "That Flight's children" means its descendants: a child that is itself a
  Flight is worked, with its own children, inside the run. The ripe candidate
  is chosen as `board.next_ripe` chooses it, restricted to the Flight and its
  descendants, so `ORDER` and `waits_on` still decide the order. The
  descendants are read from `main` before each pick, so children written
  during the run (a `hard` child split, a gap from a Flight check) are in it.
- A descendant Flight that passes its check goes to `desk-check/` and does
  not stop the run, but its parent is not ripe until the developer accepts
  it (`board.waiting`). So when no descendant is ripe, the run stops and
  names each descendant Flight in `desk-check/` as what it waits on.
- `--once` still stops after one Issue; `--push` and `--model` apply as
  they do without `--flight`.
- If an Issue outside the Flight is already underway (a saved loop state),
  `--flight` refuses and names it; finishing or abandoning it is the
  developer's call. An underway Issue inside the Flight is resumed.
- A Flight already in `desk-check/` is refused, with the message pointing to
  `just pair-accept <slug>` or `just pair-resume <slug>`.
- `--flight` passes through `just pair *args`, so no recipe changes. It is
  documented in `pair/pair.py`'s usage and in `pair/README.md`.

## Out of scope

Running several Flights, and ranking Flights against each other. Placing a
Flight's children in `ORDER`: that stays with `just groom`, and an unplaced
child runs in filename order after the placed ones, as it does now.

## Done when

The pair tests show that, with another ripe Issue ranked first,
`--flight <slug>` lands exactly that Flight's children, runs its check, and
stops at its desk check; that an unknown slug, a slug with no children, and
a slug with a different Issue underway are each refused; that a
grandchild is worked within the run; and that a descendant Flight left in
`desk-check/` stops the run with its slug named. `just gate` passes.

## The plan

**`pair/board.py`.** Add `descendants(repo, ref, slug) -> set[str]`: a
breadth-first walk over `families(repo, ref)` from `slug`, excluding `slug`.
Give `next_ripe` a keyword `within: frozenset[str] | None = None`; when set,
any backlog slug outside it is skipped, as `skip` does now. The ripeness rules
do not change.

**`pair/loop.py`, `Loop.run(once, flight=None)`.** With `flight` set:

1. Before anything else, and after `reap`, refuse (say why, return
   `"refused"`, touch nothing):
   - `flight` in `desk-check/` on `main`: point to
     `just pair-accept <flight>` / `just pair-resume <flight>`;
   - `flight` not in `backlog/` on `main`, or with no children
     (`board.children`): "not a Flight in backlog/";
   - a saved state whose slug is neither `flight` nor one of its descendants
     (grooming is already refused above): name that slug.
2. In the pick, recompute `scope = {flight} | descendants(...)` from `main`
   each time, and call `next_ripe(..., within=scope)`, so children written by
   a split, a gap or a resume join the run.
3. After a landing, if `flight` is in `desk-check/` on `main`, say so and
   return `"desk-check"`. This is the normal end.
4. When the pick finds nothing, return `"empty"`, naming each descendant that
   is in `desk-check/` on `main` and has children, as what the run waits on.

`--once` keeps its meaning. Without `flight`, `run` behaves exactly as now.

**`pair/pair.py`.** `run.add_argument("--flight", metavar="SLUG")`, passed to
`loop.run`. Add the flag to the module usage line. `just pair *args` passes it
through unchanged.

**`pair/README.md`.** A short paragraph in the Flight section, and a row in
the operator table: `just pair --flight <slug>`, what it runs and when it
stops.

**Tests (`pair/test_pair.py`), a new `FlightRunTest`:**
- `big` (a Flight, with backlog children `big-a` and `big-b`, where
  `big-b` waits on `big-a`), and an unrelated easy `other` ranked first in
  `ORDER`. Run with `flight="big"`: `big-a` and `big-b` land, `big` gets its
  check and lands in `desk-check/`, the outcome is `"desk-check"`, and `other`
  is still in `backlog/` with no turn sent for it.
- Refusals, each returning `"refused"` with no turn sent and `main`
  unchanged: an unknown slug; a backlog Issue with no children; `big` in
  `desk-check/`; a saved state for `other`.
- A saved state for `big-a` (inside the Flight) is resumed, not refused: the
  run finishes `big-a` and goes on to `big-b`.
- A grandchild: `big-a` is itself a Flight with a backlog child `big-a-1`.
  The run lands `big-a-1`, checks `big-a` (which goes to `desk-check/`), and
  then stops with `"empty"` and `big-a` named, because `big` cannot be
  ripe until `big-a` is accepted.
- `BoardTest`: `descendants` walks two levels, and `next_ripe(within=...)`
  skips a ripe slug outside the set.

`main()` in `pair/pair.py` already binds a local `flight` to
`args.slug` and, when it is set, answers `accept`/`resume` and returns before
the lock is taken. Read `run`'s option as `args.flight` only in the `run`
branch, and rename that local (to `desk`, say), so `--flight` can never be
mistaken for a desk-check slug and a run always holds the lock.

**Order.** Board helpers and their tests, then `run`, then the CLI and README,
then `just gate pair`, and `just gate` at the end.

**Risks.**
- The refusal of a saved state must come before `run`'s existing
  `retry == "desk-check"` branch. Otherwise a developer-difficulty Issue
  outside the Flight waiting at its desk check would be reported as the run's
  stop, not as a refusal.
- Every check in `run` reads `main` in the developer's checkout
  (`board.listed(self.repo, self.main, ...)`), as the pick does, not the
  worktree, which may still sit on an Issue branch.

## Notes from the work

- The plan held. `run` returns `"refused"` for each refusal, and says why
  through `say`; the refusal checks live in `Loop.flight_refusal`, and the
  message when nothing is ripe in `Loop.nothing_ripe`.
- An Issue outside the Flight waiting at its own desk check is refused like
  any other outside Issue underway, because the refusal runs before `run`'s
  `retry == "desk-check"` branch (tested).
- A Flight check that writes a brief settles in two turns (the brief, then a
  quiet turn); the tests' `flight_check_turns` scripts exactly that.
- The pick restricts `next_ripe` with `within`, so a descendant Flight is
  ripe by the usual rule. A Flight whose child is in `done/` is ripe even if
  a grandchild is not, because ripeness looks only one level down; that is
  unchanged here and does not arise when children land before their parent.
- The recipe is unchanged, but its comment in `just --list`, rendered from
  `.meta/lib/render/writers.py`, now names `--flight SLUG`; it lost "from
  issues/backlog/" to stay under the line limit. `AGENTS.md`'s Delivery list
  names `just pair --flight <slug>` beside `just pair`.
