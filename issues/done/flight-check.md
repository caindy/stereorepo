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
  `ORDER`) as a Flight. Both paths that retire it go: `retire_hard` after a
  grooming pass, and the `advance` branch that moves a `hard` Issue from its
  own backlog stage to `done/`; that stage now merges its children with the
  parent still in `backlog/`. An Issue is a Flight when any Issue, in any
  stage, names it in `parent:`. `board.next_ripe` treats an Issue
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
  seats to one of those two outcomes: the stage is finished when the branch
  adds a backlog Issue naming the Flight in `parent:`, or adds one more
  `## Desk-check brief` section to the Flight file than it had at the base
  (earlier rounds' briefs stay, as history), and nothing outside `issues/`
  has changed. The check runs as its own stage of the loop, `flight-check`,
  with its prompt in `pair/prompts/stage-flight-check.md`, while the file
  stays in `backlog/`. The loop starts a ripe Flight in that stage rather than
  in the backlog stage. `flight-check` names no directory, so every place
  that takes `st.stage` as the Issue's directory reads a Flight from
  `backlog/` instead: `move`, `merge`, the guard that puts back a file a seat
  moved, and the prompt's issue path.
- **A gap lands without retiring the Flight.** `merge` moves every Issue to
  `done/` and `squash` drops its slug from `ORDER`; for a Flight check that
  wrote a gap, and for a `hard` Issue split in its own backlog stage, neither
  happens: the new children and the Flight file land on
  `main` with the Flight in `backlog/` and still in `ORDER`.
- A Flight that passes its check goes to `done/` in this part;
  `flight-desk-check` sends it to `desk-check/` instead.
- **`flights` becomes the first Flight.** The grooming pass that split
  `flights` ran `retire_hard`, so `flights` is in `issues/done/` and out of
  `ORDER` when this part starts. Move it back to `issues/backlog/`, so it waits
  on its remaining parts and gets its own Flight check once they land. Put it
  back at the top of `ORDER`, above `# groomed below`, where the developer
  placed it. The board checks allow this: a backlog Issue that
  `ORDER` names.
- The requirement that a `hard` Issue have children, in both the backlog
  stage and `board.grooming_faults`, counts children in any stage
  (`board.children` looks only in `backlog/` today), so a Flight with landed children is not asked to split
  again.

## Out of scope

The desk check of a Flight, `just deliver`, `just pair --flight`, and the
vocabulary; each is its own part of `flights`.

## Done when

The pair tests show: a split `hard` Issue stays in `backlog/` and is not ripe
while a child is outside `done/`; once all its children land the loop runs the
Flight check; a check that changes nothing, or changes code, is not accepted;
a gap written in the check lands a child on `main` while the Flight stays in
`backlog/` and in `ORDER` and waits again; a
clean check writes the brief and retires the Flight to `done/`; a `hard`
Issue split in its own backlog stage stays in `backlog/`. `flights` is
back in `issues/backlog/` and first in `ORDER`, and `just gate` passes.

## The plan

### `pair/board.py`

1. `children(repo, ref, parent) -> dict[str, str]`: every Issue at `ref`, in
   any of `STAGES` except `roadmap`, whose `parent:` names `parent`, mapped to
   its stage. It replaces the tree-reading `children(tree, parent)`; the
   callers that read the worktree pass `self.wt` and `"HEAD"`, which is sound
   because `settle` commits every turn before `requirement` or `merge` run.
   `grooming_faults` passes `tree, "HEAD"` likewise. Add
   `waiting(repo, ref, parent) -> bool`: some child is outside `done/`.
2. `next_ripe` skips a slug for which `waiting` holds, beside the existing
   `waits_on` test. To keep it from reading every Issue once per candidate,
   build the parent→children map once per call (one `git ls-tree` per stage,
   one `at_ref` per file, as `listed`/`at_ref` do now); the tree is tens of
   files.
3. `sections(body, name) -> int`: how many headings are named `name`, so the
   loop can tell a new `## Desk-check brief` from an earlier round's.
   `section` finds only the first.

### `pair/loop.py`

4. `FLIGHT_CHECK = "flight-check"`, and a `home(stage)` helper returning
   `"backlog"` for it and the stage otherwise. Use it where `st.stage` is read
   as a directory: `settle` (the put-back guard), `move` (the source path),
   `message` (the `path` field). `status` says "in its Flight check" rather
   than "in flight-check/".
5. `run`: when `next_ripe` returns a slug with any child at `main`, start it as
   `State(slug=slug, stage=FLIGHT_CHECK)`.
6. `requirement` for `FLIGHT_CHECK`, in order: `touches_code()` is a fault
   ("the Flight check changes nothing outside issues/"); then finished when
   a child sits in `backlog/` at `HEAD` that did not exist at `st.base` (a
   gap; a child moved there from another stage does not count), or
   `sections(body, "Desk-check brief")` exceeds the count in the Flight file at
   `st.base`; otherwise the fault names both outcomes. Then run the gate, as
   the grooming pass does, since the check writes new Issue files the board
   checks read.
7. Backlog stage requirement: `board.children(self.wt, "HEAD", slug)` (any
   stage).
8. `advance`: drop `retire_hard` and its call (grooming just merges) and the
   `backlog`+`hard` → `done` branch; a split `hard` Issue and every
   `FLIGHT_CHECK` go straight to `merge`.
9. `merge`/`squash`: the Issue retires (moves to `done/`, leaves `ORDER`)
   unless `board.waiting(self.wt, "HEAD", slug)`. The rule is derived from the
   tree rather than carried in `State`, so a `retry="merge"` after a pause
   decides the same way. `squash` drops the slug from `ORDER` only when the
   Issue sits in `done/`, which is what happens today for every other path.
10. Module docstring: a paragraph on Flights (a split Issue waits in backlog
    until its children land, then gets a Flight check).

### `pair/prompts/stage-flight-check.md`

11. Fields `{path}` and `{slug}`: every Issue naming `{slug}` in `parent:` has
    landed; check the Flight's "Done when" end to end on `main`; write each gap
    as a new `issues/backlog/` file with `parent: {slug}` and a `difficulty`,
    or else append a `## Desk-check brief` (what was delivered, where to see
    it, what is worth trying) to `{path}`; change nothing outside `issues/`.

### The board

12. `git mv issues/done/flights.md issues/backlog/flights.md`; put `flights` on
    the first line of `ORDER`, above `# groomed below`.

### Tests (`pair/test_pair.py`)

- `BoardTest`: a Flight is not ripe while a child is in `backlog/`, `todo/`
  or `desk-check/`, and is ripe once all are in `done/`; `sections` counts
  repeated headings; `grooming_faults` does not ask a `hard` Issue whose
  children are all in `done/` to split.
- `LoopTest.test_a_hard_issue_is_split_into_backlog_children` now asserts
  `big` stays in `issues/backlog/` and in `ORDER` on `main`, and
  `next_ripe` is `big-1-parse`.
- `GroomingTest.test_a_hard_issue_split_in_a_pass_goes_to_done_and_leaves_order`
  becomes `..._stays_in_backlog_and_order`.
- New `LoopTest`s, with a `hard` parent in `backlog/` and its child in
  `done/`: the run starts it in `flight-check` and the prompt names
  `issues/backlog/<slug>.md`; two quiet turns are not accepted and the note
  says what is missing; a turn that writes `a.txt` is not accepted; a gap
  child lands on `main` with the Flight in `backlog/` and `ORDER` and
  `next_ripe` returning the gap; a brief lands the Flight in `done/` and out
  of `ORDER`; a Flight file that already holds one brief needs a second; a
  seat that moves the Flight file is put back in `backlog/`.

Then `just gate pair` while working, and
`just gate` at the end.

### Risks

- **An old supervisor after this lands.** A `just pair` started before this
  lands keeps the old `next_ripe` in memory, sees `flights` first in `ORDER`
  with no `waits_on`, runs its backlog stage and moves it to `done/` again.
  To guard against that, `flights` also gets
  `waits_on: [flight-desk-check, flight-deliver, pair-flight-option,
  flight-vocabulary]`, which both old and new code honour and which says
  nothing the children do not. The developer should still restart `just pair`
  after this lands.
- **`children` at `HEAD`.** Reading the worktree at `HEAD` rather than its
  files is correct only after `settle` has committed; `grooming_faults` is
  also only called then. A call before `settle` would miss uncommitted files.
  `BoardTest.test_grooming_faults_name_each_rule` does call it on uncommitted
  files; it passes only because `big` has no children either way. A new test
  of the children rule in `grooming_faults` commits the child first.
- **Retiring by inference.** A Flight check that writes a brief *and* a gap
  keeps the Flight waiting, which is right: the gap must land first, and the
  next check writes a fresh brief.

## Implementation notes

- `board.families` finds the Issues that name a parent with `git grep -l
  '^parent:'` at the ref, then parses only those, so `next_ripe` reads the
  parent map once per call and does not grow with `done/`. `children` and
  `waiting` read through it.
- The two retirement paths are gone, and so is the `retire_hard` method.
  `Loop.retires` decides at landing whether the Issue moves to `done/`, and
  `squash` drops a slug from `ORDER` only when the Issue sits in `done/`.
- The Flight check is capped by the Flight's own difficulty, so a `hard`
  Flight gets the `hard` round cap (4 rounds).
- The Flight check tests are in `FlightCheckTest`. The split tests in
  `LoopTest` and `GroomingTest` now expect the parent to stay in `backlog/`
  and in `ORDER`.
- `flights` carries `waits_on:` naming its four remaining parts, as the plan's
  first risk says. **Restart any `just pair` that was running before this
  landed**: the old code in memory would otherwise take `flights` straight
  back to `done/` once those parts land.
- `pair/README.md` describes the Flight path in its stage table, under
  Landing, and under grooming. The vocabulary for Flights is left to
  `flight-vocabulary`.
