---
difficulty: medium
parent: backlog-grooming-and-ranking
---

# Take the backlog in a ranked order, and keep send-backs in it

`next_ripe` in `pair/board.py` takes the first ripe Issue in filename order,
and a send-back moves an Issue to `roadmap/`, which is the developer's alone.
This part gives the backlog a running order and keeps send-backs in it. It
does not write the order; `backlog-grooming-pass` does.

## Wanted

- **The order file.** `issues/backlog/ORDER` is plain text, one slug per line.
  Blank lines are ignored. The line `# groomed below` is the marker: lines
  above it are the developer's placements, lines below it are grooming's
  ranking. A file with no marker is all the developer's. Any other line
  starting `#` is a comment.
- **`next_ripe` follows it.** It reads `ORDER` at the ref it is given, and
  names in it that are not in `backlog/` are passed over. It takes the first ripe Issue in the order the
  file gives (above the marker, then below), then any backlog Issue the file
  does not name, in filename order. A missing file means filename order alone,
  as today.
- **Sent-back Issues sit out.** `next_ripe` skips a backlog Issue whose body
  has a `Needs elaboration` section.
- **Send-backs stay in the backlog.** `kick_back` in `pair/loop.py` writes the
  Issue, with its `Needs elaboration` section, to `issues/backlog/` on `main`
  instead of `issues/roadmap/`. Its messages and the module docstring say so.
  The file it writes always has a `Needs elaboration` section: when the
  Issue's file is gone from the branch (`kick_back(st, None)` with nothing to
  read), it adds one saying so, so the Issue sits out rather than being taken
  straight back up.
- **The order stays true.** When `merge` in `pair/loop.py` squashes an Issue
  onto `main`, after its rebase, the squash commit also removes the Issue's
  slug from `ORDER`, if the file names it. The removal is not made in the
  earlier `backlog -> todo` move on `pair/<slug>`. That commit would conflict
  at rebase with any reordering the developer does on `main` while the Issue
  runs.
- **A gate step.** Beside `board front matter` in
  `.meta/checks/files/board.py`, a step fails when `ORDER` names a slug that
  has no file in `backlog/`, `todo/`, `in-progress/` or `desk-check/`, and
  reports the line. An Issue in flight still has its slug in `ORDER` on its
  branch, so its own gate must pass. A board with no `ORDER` passes.

## Out of scope

- Writing or ranking the order (`backlog-grooming-pass`).
- The READMEs and vocabulary (`backlog-and-roadmap-words`).

## Done when

- Pair tests show: the loop takes a ripe Issue named in `ORDER` ahead of one
  earlier in filename order; an unnamed Issue follows every named one; an
  Issue with `Needs elaboration` is skipped; a `Needs elaboration` section,
  a round-cap overrun and a vanished Issue file each leave the Issue in
  `backlog/` on `main` with that section; a
  landed Issue's slug is gone from `ORDER` on `main`; and a developer's edit to
  `ORDER` on `main` while an Issue is in flight still lands without a
  conflict. The existing roadmap send-back tests are changed to match.
- Probes show that the gate step fails on a slug in `done/` or in no stage,
  passes on a slug in `in-progress/`, and passes on a board without `ORDER`.
- `just gate` passes.

## The plan

### Steps

1. **`pair/board.py`: read the order.** Add `ORDER = "ORDER"` and a
   module-level `order(repo, ref) -> list[str]`, which reads
   `git show <ref>:issues/backlog/ORDER` and returns the slugs, above the marker
   first and then below it. Blank lines and `#` lines are dropped, and a
   missing file gives `[]`. The marker needs no special handling when reading,
   because the file lists placements before the ranking. It matters only to
   the grooming pass. Add `without(text, slug) -> str`, which returns the file
   with every line equal to `slug` removed and leaves comments, the marker and
   the other lines as they were.
2. **`next_ripe`** walks `order(...)` filtered to `listed(..., "backlog")`,
   then the remaining backlog slugs in filename order. It skips `skip`, any
   Issue that is not ripe, and any Issue for which `needs_elaboration(issue.body)`
   is true. Its docstring says so.
3. **`kick_back`** in `pair/loop.py` writes to `backlog/`. When `issue` is
   `None`, the text becomes `# <slug>` plus a `# Needs elaboration` section
   saying the Issue's file was gone from its branch. Update the method
   docstring, the `notify`/`say` wording, the module docstring (lines 11–12),
   and the one sentence in `pair/README.md:42` that names the send-back
   destination, because this change makes it false. This overlaps
   `backlog-and-roadmap-words` on purpose. That Issue still owns the rest of
   `pair/README.md` and every other README.
4. **`squash`** removes the slug from `ORDER` after the `reset --soft` to
   `main` and before the commit. It reads `issues/backlog/ORDER` in the
   worktree (the rebased tree, so it already holds any edits the developer made
   on `main`), writes `without(...)` if the slug appears in it, and runs
   `git add` on the file. `move` and `start_issue` stay unchanged, so no branch
   commit touches `ORDER`. `squash` runs again on each pass of `merge`'s retry
   loop and on a resumed `retry="merge"`, so the removal must be a no-op when
   the slug is already gone.
5. **Gate step** `board order` in `.meta/checks/files/board.py`, registered
   after `board_front_matter`. It reads `BOARD/backlog/ORDER` and, if the file
   exists, reports `issues/backlog/ORDER:<n>: <slug> names no Issue in
   backlog, todo, in-progress or desk-check` for each slug line that fails.
   It takes a seam for probes, `board_order(views, root: pathlib.Path | None = None)`,
   where `root` stands in for `BOARD`. Add a history entry to
   `.meta/checks/files.history.md` in the form of its `board_front_matter`
   entry.
6. **Probes** in `.meta/checks/probes/files/board.py`: a new `@check("board
   order probes")` builds a temporary board. It checks that a slug in `done/`
   and a slug in no stage are each reported once with their line number, that
   a slug in `in-progress/` is not reported, and that a comment, a blank line
   and the marker are not reported. It also checks that a board with no `ORDER`
   passes.

### Tests (`pair/test_pair.py`)

- `BoardTest`: `ORDER` putting `b` ahead of `a` makes `next_ripe` return `b`.
  A named slug that is not ripe (`waits_on`) is passed over for the next named
  one. An unnamed slug comes after every named one. Placements above the
  marker come before those below it. A comment line and a name missing from
  `backlog/` are ignored. An Issue with `# Needs elaboration` is skipped. With
  no `ORDER`, the order is filename order.
- Rename the three roadmap send-back tests to assert `issues/backlog/<slug>.md`
  on `main` with the section, and not `roadmap/`. Add a test for a vanished
  Issue file, where a seat deletes it: the Issue lands in `backlog/` with a
  `Needs elaboration` section, and `next_ripe` then returns `None`.
- Landing: with `ORDER` naming `a` and `b`, landing `a` leaves `main`'s `ORDER`
  naming only `b`, in one squash commit. In the same shape as
  `test_backlog_added_on_main_mid_issue_lands_alongside`, the developer
  commits a reordering of `ORDER` on `main` mid-Issue, and the Issue still
  lands with `"landed"`, the reordering kept, and its own slug gone.

### Risks

- **A retried landing can conflict on `ORDER`.** If `main` moves between the
  squash and the fast-forward, `merge` rebases the squash commit, which now
  touches `ORDER`. A developer's edit to `ORDER` on the lines next to the slug
  in that window conflicts, and the loop pauses through the existing rebase
  pause. The window is seconds long and the pause is safe, so the plan accepts
  it and does not add machinery.
- **The gate on an Issue's own branch.** The gate runs on the branch while
  the Issue sits in `in-progress/` or `desk-check/`, so its slug still
  resolves. The `done/` move and the slug's removal both happen after the
  gate, inside `merge`, so the check never sees the slug in `done/`.
- **Old send-backs in `roadmap/`** are untouched. The loop never reads
  `roadmap/`.

## Notes for the next reader

- **Where the plan moved.** The ordering tests are one `BoardTest` case,
  `test_order_runs_the_backlog`, plus `test_without_drops_only_the_slug`. The
  landing test puts `a`, `b` and `c` in `ORDER` and reorders `b` and `c` on
  `main` mid-Issue, so it covers the removal and the reordering together.
- **More sentences made false.** `issues/backlog/README.md` said the loop
  runs in filename order, and `issues/roadmap/README.md` said send-backs land
  there. The stage tables in `issues/README.md` and `template/issues/README.md`
  said both. Each was corrected in place, like `pair/README.md:42`. The rest of the
  wording is still `backlog-and-roadmap-words`'s.
- **A step with no sources.** `board_order` takes only its `root` seam, so the
  gate passes it nothing. It reads `issues/backlog/ORDER` from disk rather than
  from `sources.tree()`, which is enough for one known path.
- **The probe bites.** Letting `done` count as a stage the step accepts makes
  `board order probes` fail on the `landed` line.
- **Old send-backs.** An Issue already sitting in `roadmap/` with a `Needs
  elaboration` section stays there. The developer moves it to `backlog/` after
  answering it, as before.
