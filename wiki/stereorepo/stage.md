---
slug: stage
context: stereorepo
minted: 2026-09-30
---

# Stage

**Stage** is where an [[issue|Issue]] is on its way to `main`, held as the directory of the [[board]] that its file sits in.

## The stages in order

An Issue moves through `backlog`, `underway`, `todo`, `in-progress`,
`desk-check` and `done`, in that order, and each is a directory under
`issues/`. `roadmap` stands beside them: it holds what the [[developer]]
intends and may never do, and no agent moves an Issue into or out of it.

- `backlog` is the queue, run in the order `issues/backlog/ORDER` gives.
- `underway` holds the one Issue the pair loop is working, from the moment the
  supervisor starts it until the commit that lands it.
- `todo` holds an Issue that has been groomed and waits for a plan.
  `in-progress` holds one that has a plan and is being implemented.
- `desk-check` holds a `developer` Issue, or a [[flight|Flight]], that waits
  for the developer to check it by hand.
- `done` holds an Issue that has landed on `main`.

## Two boards, one Issue underway

The board on `main` is the authoritative one, but an Issue being worked has a
second position on its own branch, which is named for its slug. On `main` its file sits in
`underway/` for as long as it is worked, so the board shows what is being
worked, and nothing that edits the backlog can edit it. On the branch, the file
sits in `underway/` for the backlog stage and the Flight check, and then moves
through `todo/`, `in-progress/` and `desk-check/`. The commit that lands the
Issue moves the file out of `underway/` on `main`: to `done/`, to
`desk-check/` for a Flight that passes its check, or back to `backlog/` for a
Flight left waiting on its children. A send-back moves it from `underway/` back
to `backlog/` in a commit of its own, without the branch's work.

## Who moves an Issue

A stage is a directory, never a field. Only the developer adds Issues to
`roadmap`. The developer or a seat adds new Issues to `backlog`. Every other
move is the supervisor's: a `git mv`, or, for a send-back, the file rewritten
into `backlog` on `main` with a `Needs elaboration` section. Seats never move
Issue files. Where a seat moves one, the supervisor puts it back.

## What a stage is not

- **Not a column.** A kanban column is a view that holds no state of its own.
  A stage is the directory the file sits in, and every view of the board is
  read from it.
- **Not a status field.** No front-matter key records an Issue's stage, so a
  field can never disagree with where the file actually sits (stereorepo's DR-308).

---

**See also:** [[flight]], [[ubiquitous-language]]
