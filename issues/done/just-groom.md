---
difficulty: medium
---

# Groom with `just groom`, apart from implementation

The grooming pass runs inside `just pair`: before taking each Issue, the loop
compares every backlog file on `main` with `.pair/groomed.json` and runs a pass
whenever one is new or changed. The pass grooms the backlog and re-ranks all of
it below the `# groomed below` marker in `issues/backlog/ORDER`. So every
backlog commit, including the Issues the pair files itself, delays the next
Issue by a whole-backlog pass, and the running order can change under the
developer between two Issues.

Grooming and implementation are different activities. Implementation should
start from the running order as it stands.

## What is wanted

- **`just groom`** runs a grooming pass on its own, and `just pair` no longer
  runs one. The pass keeps the agreement rule, its own branch, the checks the
  supervisor holds it to, and landing as one commit on `main`.
- **Groomed is read from the Issue.** An Issue is groomed when its front
  matter sets a valid `difficulty` and it has no `Needs elaboration` section.
  The pass grooms only the Issues that are not, leaving out any that carry a
  `Needs elaboration` section: those wait on the developer, who answers by
  editing the Issue and removing the section, as they do now.
  `.pair/groomed.json`, `board.stale`, `board.backlog_blobs` where nothing else
  uses it, and the record update in `kick_back` go. An Issue the developer writes with a
  `difficulty` is taken as groomed, and deleting an Issue's `difficulty` asks
  for it to be groomed again. `just groom` with nothing to groom says so and
  exits.
- **Faults cover what the pass grooms.** `board.grooming_faults` asks for a
  `difficulty` (and children for `hard`) only on the Issues the pass took up
  and the children it wrote. It asks nothing of an Issue the pass parks with a
  `Needs elaboration` section, or of Issues it did not take up.
- **Ranking is incremental.** The pass places each Issue it groomed, and each
  child it writes, into the order below the marker, and leaves every line
  already there where it is. `just groom --rerank` judges the whole order below
  the marker again, as the pass does now. Lines above the marker stay the
  developer's in both. The supervisor holds the pass to this:
  `board.grooming_faults` reports a fault when, without `--rerank`, the
  slugs that were below the marker at the start of the pass, and are still in
  the backlog, are no longer in the same relative order.
- **The prompt follows.** `pair/prompts/stage-grooming.md` names the Issues
  to groom instead of the whole backlog, and asks for them to be placed without
  moving the rest. Under `--rerank`, it asks for the whole order below the
  marker to be ranked again.
- **One thing at a time in the worktree.** A grooming pass and an Issue share
  `worktrees/pair` and the loop's state. `just groom` refuses while an Issue is
  in flight, and says so. `just pair` refuses while a grooming pass is in
  flight, and says to finish it with `just groom`, which resumes an
  interrupted pass.
- **The loop takes the order as it stands.** `just pair` takes the first ripe
  Issue in running order. An ungroomed Issue is still groomed by its own
  backlog stage when the loop takes it, as before the pass existed.
- **The words follow:** `pair/README.md`, `issues/README.md`,
  `template/issues/README.md`, `issues/backlog/README.md`, `AGENTS.md` and the
  recipe comments in `.meta/lib/render/writers.py` (with `groom` added to the
  justfile contract in `.meta/checks/files/justfile.py` and to its
  scaffold-only recipes).

## Out of scope

- Running `just groom` on a schedule or automatically.
- Flights (`flights`). The developer placed this Issue above the marker, so it
  lands before any part of `flights`, which rank below the marker. Keep
  `retire_hard` as it is: the pass still retires a `hard` Issue it splits.
  `flight-check` removes that later. After that change, a split `hard` Issue
  stays in `backlog/`, and it counts as groomed because it has a `difficulty`.

## Done when

- `just pair` never runs a grooming pass, and `just groom` grooms only the
  Issues that are not groomed and carry no `Needs elaboration` section, and
  exits when there are none.
- An Issue parked with a `Needs elaboration` section is neither groomed again
  nor held to a `difficulty` by the pass.
- A groomed Issue keeps its place in `ORDER` across a `just groom`, a pass
  that reorders it is held back by a grooming fault, and `--rerank` re-ranks
  the whole order below the marker.
- Neither `just groom` nor `just pair` starts while the other's work is in
  flight.
- `.pair/groomed.json` is no longer written or read.
- The pair tests cover each of these, and `just gate` passes.

## The plan

### Seams

- **`pair/board.py`**
  - Add `to_groom(repo, ref)`: the backlog slugs at `ref` with no valid
    `difficulty` and no `Needs elaboration` section.
  - Add `unnamed(repo, ref)`: the backlog slugs `ORDER` does not name, which
    `Loop.groom` uses to decide whether there is anything to place.
  - Remove `stale` and `backlog_blobs`. Nothing but the grooming record uses
    them.
  - `grooming_faults(tree, repo, ref, targets, rerank)`:
    - It asks for a `difficulty`, and for children when `hard`, only on
      `targets` that are still in the backlog without a `Needs elaboration`
      section, and on backlog files that were not listed at `ref` (the
      children the pass wrote).
    - The ranking faults stay as they are. Every backlog Issue not placed above
      the marker is still named once below it, so an Issue the developer wrote
      with a `difficulty` but never placed is placed by the next pass.
    - New fault, only when `rerank` is false: the slugs below the marker at
      `ref` that are still in the backlog, and are not targets, must keep their
      relative order. A target is free to move, because an Issue whose
      `difficulty` the developer deleted is being placed afresh. The fault
      names the slugs out of order and shows their order at `ref`.
- **`pair/loop.py`**
  - `State` gains `targets: list[str]` and `rerank: bool`. Their defaults keep
    an old `state.json` loading.
  - `run` loses the grooming branch and the `groom` constructor argument. When
    the loaded state is a grooming pass, `run` says to finish it with
    `just groom` and returns `"grooming"`. The `once and outcome != "groomed"`
    special case goes.
  - New `Loop.groom(rerank)`. It takes the name the removed `groom`
    constructor argument had.
    1. It runs `ensure_worktree` and `reap`, then loads the state.
    2. With an Issue in flight, it says so and returns `"busy"`.
    3. With a pass in flight, it resumes it through `work`, and `retry=GROOMING`
       keeps working as now. The resumed pass keeps the `targets` and `rerank`
       in its state. A `--rerank` given on resume is ignored, and the command
       says so.
    4. Otherwise it computes `targets` from `board.to_groom` on `main`.
    5. With no targets, no Issue that `ORDER` leaves unnamed, and no
       `--rerank`, it says "nothing to groom" and returns `"nothing"`.
    6. Otherwise it starts `State(slug=GROOMING, stage=GROOMING, targets,
       rerank)`.
  - `requirement` passes `st.targets` and `st.rerank` to `grooming_faults`.
  - `groomed` loses `onto` and the record write. It only detaches, deletes the
    branch and clears the state.
  - `kick_back` loses the record update. `groomed_file`, `load_groomed` and
    `save_groomed` go, along with the `json` use for them.
  - `retire_hard` retires only `hard` backlog Issues that have children in the
    tree. As it stands, it would move a developer-written `hard` Issue to
    `done/` unsplit, because the pass no longer holds that Issue to having
    children. The behaviour for an Issue the pass splits is unchanged.
  - `message` passes `issues=` (the targets as a bullet list, or
    "(none: this pass only ranks)") and `ranking=` (the text of the placing or
    the re-ranking paragraph) into `template.format`. The unnamed Issues are
    not listed: the ranking paragraph asks for every backlog Issue the
    developer has not placed to be named below the marker, as the fault
    does. The other stage templates ignore these
    extra keys.
  - The module docstring's grooming paragraph is rewritten for `just groom`.
- **`pair/prompts/stage-grooming.md`**
  - It says "Groom these Issues in issues/backlog/: {issues}" instead of the
    whole backlog, and keeps the per-Issue grooming wording.
  - It drops "You may remove a `Needs elaboration` section you have answered",
    because the pass no longer takes up parked Issues.
  - Its ranking paragraph becomes `{ranking}`, filled from two short files:
    - `grooming-place.md`: place each named Issue and each child below the
      marker, leaving the other lines in their order.
    - `grooming-rerank.md`: today's paragraph, which ranks the whole order
      below the marker.
- **`pair/pair.py`**
  - A `groom` subcommand with `--rerank` and the seat flags calls
    `loop.groom(args.rerank)` under the same run lock.
  - The module docstring lists it.
- **Recipes**
  - `.meta/lib/render/writers.py` renders
    `groom *args: uv run --quiet --script pair/pair.py groom {{args}}`, with a
    comment.
  - `.meta/checks/files/justfile.py` adds `"groom": (("args", FLAGS),)` to
    `CONTRACT` and `"groom"` to `SCAFFOLD_RECIPES`.
  - `just render` regenerates the justfile.
- **Words**: `pair/README.md`, `issues/README.md`, `template/issues/README.md`,
  `issues/backlog/README.md` and `AGENTS.md`. Where each one says the loop
  grooms before each Issue, it says `just groom` instead, and it says what
  counts as groomed.

### Order

1. `board.py`: `to_groom`, and the new `grooming_faults` signature and faults,
   with their unit tests.
2. `loop.py`: state, `groom`, `run`, `groomed`, `kick_back`,
   `retire_hard`, `message`, and the prompts.
3. `pair.py`, the recipe and the contract, then `just render`.
4. The words.
5. `just gate`.

### Tests (`pair/test_pair.py`, `GroomingTest`)

Most existing grooming tests keep their scripts and call
`b.loop.groom()` where they called `run()`. The helpers that rely on
the record go: `mark_groomed`, `stale`, and the `groom=False` bench argument.
New or rewritten tests:

- `run` never grooms. With an ungroomed ripe Issue, it takes the Issue straight
  into its backlog stage.
- `groom` on a backlog where every Issue has a `difficulty`, or is
  parked, and `ORDER` names them all returns `"nothing"` and sends no turn.
- The first message names only the targets, and a parked Issue is not among
  them.
- A pass that grooms `c`, with `ORDER` below the marker as `a b`, and writes
  `b c a` is held back, with the fault in the note. Writing `a c b` lands.
- Under `rerank=True`, `b a` lands.
- With `ORDER` below the marker as `a b c` and `a` a target (its `difficulty`
  deleted), writing `b c a` lands.
- A parked Issue with no `difficulty` raises no `difficulty` fault.
- `groom` with an Issue in flight returns `"busy"`. `run` with a pass in
  flight returns `"grooming"`. A stopped pass resumes under `groom`.
- A `hard` Issue the developer wrote without children is not retired by a pass
  that grooms something else.
- `.pair/groomed.json` does not exist after a pass or a send-back.

### Risks

- **The relative-order fault.** It must compare only slugs present both at
  `ref` and in the tree. A retired `hard` Issue leaves `ORDER` after the check
  runs, in `retire_hard`, so it does not interfere. A target that was already
  named below the marker is free to move.
- **A pass that finds an unnamed Issue.** An Issue the developer wrote with a
  `difficulty` but never placed makes the pass place it. Only in that case does
  `just groom` run with no targets, which the "nothing to groom" condition
  above accounts for.
- **The contract check.** It fails unless the recipe, the contract and
  `SCAFFOLD_RECIPES` change together.

## Implementation notes

- **Names.** The entry point is `Loop.groom(rerank)`, not `groom_backlog` as
  first planned. The `groom` constructor argument it would have clashed with is
  gone. `Loop.groom` returns `"groomed"`, `"nothing"`, `"busy"`, `"paused"` or
  `"stopped"`, and `Loop.run` returns `"grooming"` while a pass is in flight.
- **Refusing while an Issue waits for a desk check.** `just groom` names
  `just pair-accept` or `just pair-resume`, not `just pair`, because
  `just pair` would only repeat that the desk check is waiting.
- **An old `.pair/groomed.json`** in a checkout is left on disk, but nothing
  reads it any more. It is gitignored runtime state, and deleting it is
  harmless.
- **An old `state.json` for a pass in flight** loads with `targets=[]` and
  `rerank=False`. Its faults then ask a `difficulty` only of files the pass
  wrote. Resuming it with `just groom` finishes it, and anything left ungroomed
  is taken up by the next pass.
- **The recipe comment** is shorter than the other pair recipes' comments,
  because `.meta/checks/lines` holds `writers.py` to its line-length baseline.
- **Tests.** `GroomingTest` in `pair/test_pair.py` was rewritten around
  `Loop.groom`. It covers each "Done when" line: `run` never grooms, only the
  Issues not groomed are taken up and parked Issues are skipped, "nothing" sends
  no turn, the relative-order fault and the free target, `--rerank`, the two
  refusals, an unsplit developer `hard` Issue staying in the backlog, and no
  record written. `BoardTest.test_grooming_faults_name_each_rule` passes
  targets, and checks that an Issue the pass did not take up raises no fault.
