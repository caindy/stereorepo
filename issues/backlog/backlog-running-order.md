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
- **`next_ripe` follows it.** It takes the first ripe Issue in the order the
  file gives (above the marker, then below), then any backlog Issue the file
  does not name, in filename order. A missing file means filename order alone,
  as today.
- **Sent-back Issues sit out.** `next_ripe` skips a backlog Issue whose body
  has a `Needs elaboration` section.
- **Send-backs stay in the backlog.** `kick_back` in `pair/loop.py` writes the
  Issue, with its `Needs elaboration` section, to `issues/backlog/` on `main`
  instead of `issues/roadmap/`. Its messages and the module docstring say so.
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
  Issue with `Needs elaboration` is skipped; a `Needs elaboration` section
  and a round-cap overrun both leave the Issue in `backlog/` on `main`; a
  landed Issue's slug is gone from `ORDER` on `main`; and a developer's edit to
  `ORDER` on `main` while an Issue is in flight still lands without a
  conflict. The existing roadmap send-back tests are changed to match.
- Probes show that the gate step fails on a slug in `done/` or in no stage,
  passes on a slug in `in-progress/`, and passes on a board without `ORDER`.
- `just gate` passes.
