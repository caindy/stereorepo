---
difficulty: medium
---

# `pair-status` lists what waits on the developer

The loop and the grooming pass can say that something needs the developer, but
nothing tells the developer. An Issue with a `# Needs elaboration` section sits
out of the running order silently, and the developer finds it only by reading
files. `just pair-status` shows the board's counts and the Issue being worked,
cutting the backlog list short, and says nothing about what is waiting for
the developer.

The developer's interface is the files, presented by a cockpit, and worked
with a transient interactive session. This is the first slice of that
presentation for one repository: one screen that answers "what needs me, and
what happens next".

## What is wanted

`just pair-status` shows, from the board on `main` and `.pair/`:

- **What waits on the developer**, first, one line each with the reason:
  - every Issue in `backlog/` with a `Needs elaboration` section, with the
    section's first line;
  - every Flight in `desk-check/` on `main`, with the first line of its
    latest `## Desk-check brief` and the recipes that answer it
    (`just pair-accept <slug>`, `just pair-resume <slug>`);
  - the Issue underway, when `.pair/state.json` has `retry: desk-check`
    (a `developer` Issue, whose file is in `desk-check/` on the pair branch
    and in `underway/` on `main`), with the recipes that answer it
    (`just pair-accept`, `just pair-resume`, no slug);
  - the loop or the grooming pass, if paused, with the reason its
    `state.json` records (a seat that failed twice, a grooming pass or stage
    past its round cap, a refused fast-forward, and the rest). A desk check
    is recorded as a pause too; it is listed once, as the desk check above.
- **What happens next:** the Issue being worked, its stage and turn; then the
  running order, in full, marking which Issues are ripe and, for each that is
  not, what it waits on. A Flight is one entry in that order, with its parts
  beneath it in the order they will run, each marked done, ripe or waiting,
  and last the Flight's own check. Ripeness is the predicate `next_ripe` in
  `pair/board.py` already applies, factored out so status and the loop share
  it; an Issue a grooming pass has taken up is marked as such. Backlog
  Issues without a `difficulty` are listed after the order as waiting for
  `just groom`.
- The board's counts per stage, as now, with `desk-check/` added (it is
  missing today).
- The take-over lines and last turns, as now, after the sections above.

Nothing new is stored: every line is derived from the board and `ORDER` on
`main`, `.pair/state.json` and `.pair/groom/state.json`.

## Out of scope

- Notifications, and anything across repositories (`cockpit-status-convention`).
- Machine-readable output (`pair-status-json`, which waits on this Issue);
  keep the derivation separate from the rendering so that Issue can reuse it.
- Changing how the loop decides ripeness or pauses.

## Done when

- Each kind of waiting item above appears under what waits on the developer,
  with its reason, and nothing appears there when nothing waits.
- The running order is shown in full, with ripe and waiting Issues told apart,
  and each Flight shown with its parts beneath it.
- `next_ripe` and status use the one ripeness predicate.
- The `just pair-status` line in `pair/README.md` and its `justfile` comment
  say what the screen now shows.
- The pair tests cover each case, and `just gate` passes.

## The plan

### Seams

- **`pair/board.py`: one ripeness test.** Lift `ripe` out of `next_ripe`
  into a module function `holds(repo, ref, slug, done, kin) -> list[str]`,
  which returns what holds a backlog item back: `needs elaboration`, each
  `waits_on` not in `done/`, and each child not in `done/` (as
  `part <slug>`). An empty list means ripe. `next_ripe` calls
  `not holds(...)`, and its behaviour does not change.
- **`pair/board.py`: the running order as a tree.** `running_order`
  already builds each Flight's expansion in `expand`. Split that into
  `running_tree(repo, ref)`, which returns the top-level entries, each a
  `(slug, parts)` node whose parts are nodes in run order. `running_order`
  becomes the flattening of that tree, parts before their Flight, so the
  order is defined once and status shows the order the loop actually runs.
- **`pair/loop.py`: derive, then render.** Split `status` into
  `status_view(repo, main) -> dict`, plain data that `pair-status-json`
  can dump later, and `status(repo, main) -> str`, which renders that data.
  `status_view` reads only `main`, `ORDER` (through the `board` helpers),
  `.pair/state.json` and `.pair/groom/state.json`.

### The screen, top to bottom

1. **waits on you.** One line per item, and the section is left out when
   nothing waits:
   - a backlog Issue for which `board.needs_elaboration` is true, with the
     first non-blank line of `board.section(body, "Needs elaboration")`;
   - each slug in `board.listed(main, "desk-check")` that has children,
     with the first non-blank line of
     `board.last_section(body, BRIEF)`, then
     `just pair-accept <slug>` / `just pair-resume <slug>`;
   - the pair state when `retry == "desk-check"`: its slug, then
     `just pair-accept` / `just pair-resume`;
   - for each of `pair` and `groom`, `paused` when `retry != "desk-check"`.
     The pause that a desk check records is not listed a second time.
2. **underway.** The `underway:` line `status` prints today: what is
   underway, its turn, its next seat and its approvals, or
   `nothing underway`. The `paused:` line moves out of this block into
   `waits on you`, and the session lines move down to step 5, so neither
   is printed here.
3. **next.** `running_tree`, rendered with an indent per level. Each
   backlog slug is marked `ripe`, `groomed by the pass` if it is in
   `groom_targets`, or `waits on ...` with its `holds`. Each Flight node
   lists its parts in this order: first the children already out of the
   backlog, each with its stage (`done`, `underway`, `desk-check`); then
   its backlog parts in run order; and last a line `<slug> check` with the
   Flight's own mark. After the tree comes a `to groom:` line, which lists
   `board.to_groom` and is left out when that list is empty.
4. **The counts per stage,** in today's format, over `roadmap`, `backlog`,
   `underway`, `desk-check` and `done`. `todo` and `in-progress` are only
   ever on the pair branch.
5. **The take-over lines and the last turns,** as today.

### Steps

1. In `board.py`, add `holds` and `running_tree`, and rewrite `next_ripe`
   and `running_order` on top of them. Run the existing `BoardTest` and
   `FlightRunTest` cases unchanged to show that nothing moved.
2. In `loop.py`, write `status_view` and the new `status` renderer.
3. Write the tests below.
4. Update the `status` help in `pair.py`, the `pair-status` comment in
   `justfile`, and the `watch` row in `pair/README.md` to say what the
   screen shows: what waits on the developer, what is underway, the
   running order, and the counts.
5. Run `just gate pair` while working, then `just gate`.

### Tests (`pair/test_pair.py`, a new `StatusTest` over `Bench`)

- An empty board shows no `waits on you` section.
- A backlog Issue with `# Needs elaboration` and the line `Which C?` is
  listed under `waits on you` with `Which C?`.
- A Flight in `desk-check/` with one child in `done/` and a
  `## Desk-check brief` is listed with the brief's first line and with
  `just pair-accept big`. A second, later brief replaces the first.
- A saved pair `State` with `retry="desk-check"` and a `paused` reason
  appears once, as a desk check, and the `paused:` line is absent.
- A saved pair `State`, and separately a groom `State`, each with a
  `paused` reason and `retry="merge"`, are listed under `waits on you`
  with that reason, and the reason appears nowhere else on the screen.
- A saved `State` with `sessions` prints its take-over lines after the
  counts, not inside the underway block.
- The order: `a` waits on `z` and shows `waits on z`; `b` is `ripe`; the
  Flight `big` has one part in `done/`, one ripe part and one part that
  waits on its sibling, all three shown beneath `big` in run order, and
  then `big check` waiting on the two unfinished parts. An Issue with no
  `difficulty` appears on the `to groom:` line, and a groom target is
  marked as such.
- The count line for `desk-check` appears. The existing assertions on
  `underway       1  x` and on the `underway:` lines still pass.

### Risks

- **Refactoring `running_order` and `next_ripe` is the only change to
  behaviour the loop relies on.** The existing ordering tests guard it, and
  step 1 lands before anything is added on top of it.
- **Cost.** `status_view` reads every backlog file once through `at_ref`
  and calls `families` once. Compute `done` and `kin` once and pass them to
  `holds`, and do not call `children` per slug, which would re-grep the
  board each time.
- **A malformed `state.json`,** such as one written by an older loop
  without `retry`, must not crash the screen. Read keys with `.get`, as
  `status` already does for `paused` and `sessions`.

## Notes for the next reader

- **Seams as built.**
  - `board.holds` is the one ripeness test. `next_ripe` asks `not holds(...)`.
    Its labels are what status prints after `waits on`: `elaboration`, a
    `waits_on` slug, or `part <slug>`.
  - `board.running_tree` returns `Node(slug, parts)`, and `running_order` is
    `Node.flat()` over it. Nothing else about the order changed, and every
    earlier test passed after this step, before any status code was written.
  - `loop.status_view` is the plain-data derivation that `pair-status-json`
    can dump as it is. Its docstring lists the keys. `loop.status` only
    renders it.
- **Where the plan moved.**
  - The answering recipes are printed on a second, indented line under each
    desk check, because on the real board the slug, the brief and both
    recipes ran past any terminal width.
  - The `justfile` is rendered. The `pair-status` comment is set in
    `.meta/lib/render/writers.py` and written by `just render`. It drops
    "the last turns" to stay inside the 100-character line limit there.
  - The mark column is `WIDTH = 34`, which fits the longest slug on the
    board today.
  - A Flight's own entry renders as `<slug> (Flight)`, with its check as
    the last line beneath it, carrying the Flight's mark.
- **Known gaps, left as they are.**
  - An ungroomed Issue appears both in the order (usually `ripe`, since the
    loop's backlog stage grooms it) and on the `to groom:` line. A groom
    target appears on both too, marked `being groomed` in the order.
- **Second seat's polish.** `first_line` drops `**`, so a brief opening with
  a bold lead reads cleanly, and the `underway:` line prints its approvals
  as `primary, secondary` rather than a Python list. A brief's first line
  is its first source line, so a hard-wrapped paragraph is cut where the
  file wraps it.
