---
slug: issue
context: stereorepo
minted: 2026-10-02
---

# Issue

**Issue** is one unit of work, as one Markdown file on the [[board]], whose filename slug is its identifier.

## What an Issue holds

An Issue's file says what is wanted, what is out of scope, and how anyone will
know it is done. The [[seat|seats]] add to it as they work: a plan before they
implement, and what the next reader should know once they have. The
[[developer]]'s [[desk-check]] notes are written into it too. Everything said
about the work is in the one file, and the file travels with the work's
history in git.

Its front matter holds only what cannot be observed or derived
(stereorepo's DR-308):

- `difficulty`: `easy`, `medium`, `hard` or `developer`, set when the Issue is
  groomed. A `hard` Issue is split into parts; a `developer` Issue waits for
  the developer's desk check before it lands.
- `waits_on`: the Issues that must land first.
- `parent`: the Issue this one is a part of. An Issue that others name as their
  parent is a [[flight|Flight]], and there is no other kind of Issue.

All three are optional. Where the Issue stands is its [[stage]], the directory
its file sits in, and no field repeats it.

## How an Issue reaches main

The developer, or a seat that finds work outside its own Issue, adds an Issue
by committing a file to `issues/backlog/` on `main`. The [[supervisor]] takes
it from there, one Issue at a time (stereorepo's DR-311), and the seats groom,
plan and implement it on a branch named for its slug. It lands as one
squash-merged commit on `main`, with no pull request (stereorepo's DR-310):
what the seats argued is in the Issue file, and the branch's own commits are
not kept.

## What an Issue is not

The word is the common one, narrowed, because a reader would guess it right
(stereorepo's DR-313). What it drops is what a tracker's issue carries:

- **No number.** Its slug is its id, so adding work needs nothing reserved
  first and two new Issues cannot collide on an id.
- **No status, labels or assignee.** Its stage is the directory it sits in, and
  the seats working it are whichever two the loop is running.
- **No comment thread.** The seats' notes and the developer's notes are
  sections of the file.
- **Not a ticket, story, task or epic.** An Issue has one type, and an Issue
  with children is a Flight.

---

**See also:** [[board]], [[stage]], [[flight]], [[ubiquitous-language]]
