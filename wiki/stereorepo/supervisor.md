---
slug: supervisor
context: stereorepo
minted: 2026-10-02
---

# Supervisor

**Supervisor** is the deterministic program that runs the [[seat|seats]] and moves an [[issue|Issue]] between [[stage|stages]] from what it can observe: where the Issue file is, the working tree, and the gate's exit code.

## Deciding from what it observes

The scaffold holds the supervisor, outside every portfolio's tree, and
`just pair` runs it there. It takes one Issue
at a time from the backlog, gives the seats their turns, and decides every
transition for itself (stereorepo's DR-306). It reads only what is visible in
the tree or in git: which directory the Issue file sits in, whether a turn
changed anything, whether the Issue has a `Needs elaboration` section, and the
gate's exit code before landing. It asks nothing of the seats, so a seat that
ignores an instruction cannot stall it.

When both seats have accepted the same state, by making it or by a
[[quiet-turn|quiet turn]], the supervisor advances the stage with `git mv` if
the stage's requirement holds (stereorepo's DR-307). A `Needs elaboration`
section, or a stage that runs past its round cap, sends the Issue back to the
backlog on `main` without its code. Every move of an Issue file is the
supervisor's, apart from the [[developer]] adding work; where a seat moves one,
the supervisor puts it back.

The cost is that the supervisor cannot act on what it cannot see, so every
requirement of a stage is stated as something visible in the tree or in git.

## What a supervisor is not

- **Not a model.** A model deciding transitions could ignore an instruction as
  a seat can, which moves the failure up a level instead of removing it.
- **Not an orchestrator, captain or lead.** No agent sits at the top. The
  supervisor holds nothing but a lock, its state file and its process handles.
- **Not something an agent invokes.** The seats are never told it exists.

## Open questions

These were put to the first run of the loop in another repository, and their
answers are not yet recorded here:

- How reliably can the end of a seat's turn be detected?
- Does agreement by quiet turns settle naturally, or does it rubber-stamp, or
  never settle at all?

---

**See also:** [[seat]], [[quiet-turn]], [[stage]], [[ubiquitous-language]]
