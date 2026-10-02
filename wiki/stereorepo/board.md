---
slug: board
context: stereorepo
minted: 2026-10-02
---

# Board

**Board** is a repository's set of [[issue|Issue]] files, kept in `issues/` at its root, in which the directory holding an Issue file is that Issue's [[stage]].

## One board, kept in git

A repository has one board, and the board on `main` is the authoritative one
(stereorepo's DR-308). Its directories are the stages: `roadmap`, `backlog`,
`underway`, `todo`, `in-progress`, `desk-check` and `done`. An Issue moves
between them by `git mv`, so the board and the history never disagree, and
reading the board needs nothing but the files.

The Issue being worked has a second position on its own branch, where it
passes through the stages that exist only there. On `main` it sits in
`underway/` until it lands, so `main` always shows what is being worked. The
[[stage]] page traces both positions.

Within one repository, Issues run one at a time; work happens in parallel
only across repositories, each with its own board (stereorepo's DR-311).

## Views of the board

`just pair-status` shows the board and the Issue underway, and
`issues/backlog/ORDER` gives the running order of the backlog. A view is
computed from the files each time it is shown. It holds no state of its own,
so there is nothing to keep in step with the files, and nothing that can
contradict them.

## What a board is not

- **Not GitHub Issues or Projects.** State that git does not carry takes a
  network round-trip to read and an agent to set.
- **Not a kanban view or a tracker.** A kanban column is a view; the board is
  the files a view is read from.
- **Not a status field.** No field records an Issue's stage, so none can
  disagree with where the file sits.

---

**See also:** [[issue]], [[stage]], [[supervisor]], [[ubiquitous-language]]
