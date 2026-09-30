---
difficulty: medium
---

# Rank Flights, not their parts

`issues/backlog/ORDER` gives every Issue a line of its own, a Flight's parts
included. So ranking a Flight means placing each of its parts, in their
`waits_on` order, and the Flight after them; a part left out of `ORDER` counts
as unlisted and is reached only after everything listed. The developer decides
which unit of value comes next. The order of a Flight's parts is a detail its
`waits_on` already settles.

## What is wanted

- **`ORDER` names only Flights and standalone Issues.** A part, an Issue that
  names in `parent:` a Flight still in `backlog/`, has no line of its own: it
  runs where its Flight's line is. A part that is itself a Flight runs where
  its parent Flight's line is, and its own parts with it. An Issue whose
  `parent:` names an Issue outside `backlog/` (the `why-fork-*` and
  `trim-decision-records-*` parts, whose Flights are in `done/`) is ranked as
  a standalone Issue and keeps its line. An unlisted Flight's parts run where
  the Flight falls among the unlisted slugs, by the Flight's filename.
- **The loop expands a Flight where it stands.** When `next_ripe` reaches a
  Flight's line, it takes the Flight's first ripe part, in the order the parts'
  `waits_on` gives and then by filename, and once every part has landed, the
  Flight's check, as now. A Flight whose parts are all waiting on something
  outside it is passed over, as a waiting Issue is. A ripe Flight still goes
  before any ripe Issue without children.
- **Grooming places Flights, not parts.** A grooming pass places each new
  Flight and standalone Issue in `ORDER`; splitting a `hard` Issue keeps that
  Issue's line, which now stands for the Flight it became, and writes no
  lines for the parts, on whichever side of `# groomed below` the line
  stood. `pair/prompts/grooming-place.md`,
  `pair/prompts/grooming-rerank.md` and `pair/prompts/stage-grooming.md` say
  so.
- **The board holds `ORDER` to it.** The `board order` step
  (`.meta/checks/files/board.py`) and `grooming_faults` (`pair/board.py`)
  refuse a line naming a part, and a pass that leaves a Flight or
  standalone Issue unplaced.
- **`ORDER` on `main` is migrated in the same change:** the lines for
  `underway-on-main` and `groom-alongside-pair` go, leaving
  `grooming-alongside-the-loop` where it is, and so do `pair-exit-codes`,
  `pair-event-log` and `pair-status-json`, leaving `flight-instruments`.
- **The words follow:** `issues/backlog/README.md`, `issues/README.md`,
  `template/issues/README.md` and `pair/README.md` describe ranking by Flight.

## Out of scope

- How `just pair-status` shows the running order
  (`status-lists-what-waits-on-the-developer`).
- Running grooming alongside the loop (`groom-alongside-pair`).

## Done when

- With `ORDER` naming a Flight above a standalone Issue, the loop takes every
  part of the Flight, in `waits_on` order, and the Flight's check, before the
  standalone Issue.
- A grooming pass that splits a `hard` Issue keeps its line and adds none for
  the parts, and `board order` fails on a line that names a part.
- A part whose Flight is in `done/` still runs from its own line.
- `ORDER` on `main` names no part of a Flight in `backlog/`.
- `just pair --flight <slug>` still keeps to that Flight's parts and check.
- The pair tests cover each of these, and `just gate` passes.

## The plan

One definition carries the whole change: a slug is **top-level** when it is in
`backlog/` and its `parent:` names nothing in `backlog/`. `ORDER` names only
top-level slugs; every other backlog slug is a part and runs inside its
top-level Flight. A part of a Flight at its desk check (a gap or a note that
came back as a child) is top-level by this rule until the Flight returns to
`backlog/`, so nothing is ever unreachable.

1. **`pair/board.py`: the running order.** Add `running_order(repo, ref)`,
   which takes the top-level slugs (those `ORDER` names, first to last, then
   the rest by filename, as `next_ripe` builds them now) and expands each
   Flight in place: its backlog children, sorted so that a child comes after
   any sibling its `waits_on` names (`w.split(":")[-1]`, as `ripe` reads it)
   and otherwise by filename, with each child that is itself a Flight expanded
   the same way, then the Flight itself. A `waits_on` cycle among siblings
   falls back to filename order, so the sort always ends. `next_ripe` iterates
   `running_order` in place of `named + rest`. Its scan stays as it is, so a
   ripe Flight still goes first, and `skip` and `within` still filter.
   `test_descendants_and_within_keep_to_one_flight` keeps `--flight` honest.
2. **`pair/board.py`: grooming.** `unnamed` returns only top-level slugs that
   `ORDER` misses. Without this, `just groom` would find the parts unplaced
   forever and never report "nothing to groom". In `grooming_faults`, `wanted`
   becomes the top-level slugs not placed above the marker, so a part named
   below it is reported as extra by the existing `extra` fault. Above the
   marker the lines are the developer's and the pass may not touch them, so a
   fault there could never be cleared. Instead, `above == kept` compares both
   with part lines removed, and the fault that names a part above the marker
   tells the seats to delete that line. That lets a pass repair a stale part
   line, and `board order` still refuses one on `main`. The `held` list for the no-rerank check
   keeps only top-level slugs. A split `hard` Issue is top-level, so its
   existing line satisfies `wanted` on either side of the marker. In
   `grooming_faults`, top-level is read from the files in `tree`'s
   `backlog/`, as `backlog` already is, not at `ref`: the parts a pass has
   just written exist only in the tree, so `listed`/`families` at `ref` would
   take them for top-level Issues and demand lines for them.
2a. **`pair/loop.py`: `resume_flight`.** It is the other writer of `ORDER`
   (line 401). It writes the Flight's slug first. Two things break that
   under the new rule. First, a nested Flight's parent is in `backlog/`, so
   its line would be a part line. Resume writes the line only when the
   Flight is top-level, and otherwise leaves `ORDER` alone. Second, the loop's
   own Desk-check children are written by the Flight check after resume,
   while the Flight is already in `backlog/`, so they are parts from the
   start. But a backlog Issue naming the Flight in `parent:` that the
   developer writes while the Flight sits in `desk-check/` is top-level
   then, and a grooming pass may place it. Once the Flight is back in
   `backlog/`, that line names a part. Resume removes, in the same commit,
   the lines that name the Flight's backlog descendants, using
   `board.without` for each, so a send-back never leaves `board order`
   failing on `main`.
3. **`.meta/checks/files/board.py`: `board order`.** Read each named slug's
   front matter wherever `ORDERABLE` finds it, and report the line as a part
   when its `parent:` names an Issue in `backlog/`. Add a `part` slug to
   `ORDER`, `ORDER_STAGES` and `ORDER_REPORTED` in
   `.meta/checks/probes/files/board.py`, with a backlog parent. Also add a
   slug whose parent is in `done/`, which must not be reported.
4. **Prompts.** `grooming-place.md` drops "each part you wrote" and says that
   parts get no line: a split Issue keeps its own line, which stands for the
   Flight. `grooming-rerank.md` says to rank Flights and standalone Issues only.
   `stage-grooming.md` holds no ranking words of its own (`{ranking}` is filled
   from the two above), so it needs no edit unless the prompts read wrongly
   together.
5. **`ORDER`**: drop `underway-on-main`, `groom-alongside-pair`,
   `pair-exit-codes`, `pair-event-log` and `pair-status-json`.
6. **Words**: `issues/backlog/README.md` (the running order paragraph),
   `pair/README.md` (the loop paragraphs near lines 58, 94 and 107, and
   grooming near lines 117 to 129), and the `backlog/` row and line 36 of
   `issues/README.md` and `template/issues/README.md`. Each says that `ORDER`
   ranks Flights and standalone Issues, and that a Flight's parts run at its
   line in `waits_on` order.

### Tests (`pair/test_pair.py`)

- New: `ORDER` is `big` then `a` (standalone), and `big` has parts `p2` (which
  waits on `p1`) and `p1`. `next_ripe` gives `p1`, then `p2` once `p1` is
  done, then `big` once both are done, and only then `a`.
- New: a Flight whose only part waits on an Issue outside it is passed over
  for the next line.
- New: a nested Flight's parts run at the outer Flight's line.
- New: a part whose parent is in `done/` runs from its own `ORDER` line.
- New: an unlisted Flight's parts run at the Flight's filename position.
- New: `unnamed` ignores parts, and `groom` with only parts unlisted reports
  "nothing to groom".
- New: `grooming_faults` reports a part named in `ORDER` below the marker, and
  one named above it.
- Change `test_a_hard_issue_split_in_a_pass_stays_in_backlog_and_order`: the
  seat writes `big\n# groomed below\na\n` and `main` ends with that. Add a case
  where `big` was placed below the marker.
- New: `grooming_faults` accepts a pass that splits an unplaced `hard` Issue,
  placing only the Issue itself, even though its parts are only in the tree.
- New: `pair-resume` on a Flight with a backlog child, written while the
  Flight sat in `desk-check/` and given an `ORDER` line, leaves `ORDER` naming the Flight and not the child. On a nested Flight, it
  writes no line.
- `test_a_hard_issue_is_split_into_backlog_children` and
  `test_a_ripe_flight_goes_first` should pass unchanged. Check them rather than
  assume it.

Then `just gate pair`, `just gate meta` for the probe, and `just gate`.

### Risks

- **The live board.** Once this lands, `ORDER` on `main` drives the real loop.
  Run `board order` over the migrated file before committing. A leftover part
  line fails the gate, which is the intended guard.
- **Parts that wait outside their Flight.** `pair-status-json` waits on
  `status-lists-what-waits-on-the-developer`, which stands lower in `ORDER`.
  `flight-instruments` is then passed over until that Issue lands, rather than
  pulling it forward. This is as specified, and should be named in the
  README's wording so that it surprises no one.
- **`apm_modules/_local/.meta/…`** holds a copy of the probe. Leave it to
  whatever regenerates it, and do not hand-edit it.

## Implementation notes

- The plan held. `running_order` in `pair/board.py` is now the one place that
  says what order the loop reaches the backlog in. `next_ripe` walks it, and
  anything that later shows the order to the developer
  (`status-lists-what-waits-on-the-developer`) should read it rather than
  `ORDER`.
- The "top-level" rule lives in `board.parts(parent_of, backlog)`. At a ref
  the parents come from `families` through `backlog_parents`, and in
  `grooming_faults` they come from the tree's files, because a pass may just
  have written the parts. `.meta/checks/files/board.py` has its own small
  `_parent` reader, because `.meta/` does not import `pair/`.
- `grooming_faults` lets a pass delete a part line above the marker, and the
  two grooming prompts say so. Every other line above the marker is still the
  developer's to keep.
- `resume_flight` reads the Flight's `parent:` at `main` while the Flight is
  still in `desk-check/`, and drops the line of every descendant, not only the
  parts in `backlog/`. No other descendant should have a line anyway.
- The tests' docstring now names `pair`, not `tools/pair`, as the directory to
  run them from.
- The decision is recorded as DR-299, and `wiki/stereorepo/flight.md` says
  that the running order ranks the Flight, not its parts.
- A `parent:` cycle between two backlog Issues makes both of them parts, so
  neither appears in `running_order`. Neither could ever be ripe anyway,
  since each waits on the other's children, so the loop loses nothing it
  could have taken.
