---
slug: seat
context: stereorepo
minted: 2026-10-02
---

# Seat

**Seat** is one of the two long-lived harness sessions that take an [[issue|Issue]] from the backlog to `main` in turns, in one shared worktree.

## What a seat is

A seat is a vendor's own harness CLI, run headless, keeping one session for
the whole Issue (stereorepo's DR-309). Claude Code is the first harness. A
seat runs in the pair's worktree on the Issue's branch, and loads the
repository's own settings, instructions and skills and nothing from the
developer's machine. A session kept across turns keeps the prompt cache warm,
where a fresh process for every turn would start cold each time. A stage that
names a different model starts the seat afresh on it.

## Taking turns

Within a [[stage]], the primary seat takes the first turn and the secondary the
next, and they alternate. Each turn a seat is told three things: which Issue
file it is on, what the stage is for, and what changed since its last turn. It
is told nothing about the protocol that moves the Issue; the
[[supervisor]] reads that from the tree (stereorepo's DR-306).

Both seats write code. A seat that finds something wrong in the other's work
fixes it rather than describing it. A seat that accepts what it finds says so
by changing nothing, a [[quiet-turn|quiet turn]], and a seat that judges the
Issue cannot be done as written says so with a `Needs elaboration` section
(stereorepo's DR-307). A seat that finds work outside its Issue writes it as a
new Issue in the backlog instead of doing it.

## What a seat is not

- **Not a driver or navigator.** Pair programming divides the typing; here both
  seats type, which is why the word is coined.
- **Not a coder and a reviewer.** Neither seat rules on the other's work.
- **Not just an agent.** Every harness session is an agent; *seat* names the
  place one holds in the loop, which a session outside the loop does not.
- **Not the developer.** A seat is never the [[developer]], however it acts.
- **Not the supervisor.** A seat does the work; the supervisor only observes it
  and moves the Issue.

## Open questions

These were put to the first run of the loop in another repository, and their
answers are not yet recorded here:

- Does a headless seat behave as an interactive session does, with the same
  skills, hooks, instructions and subscription login?
- How many tokens does each turn read from the prompt cache, and does that
  number rise across a seat's turns?
- How well does it work for the developer to take over a seat and hand it
  back?
- Which set of tool permissions works for a seat?

---

**See also:** [[supervisor]], [[quiet-turn]], [[developer]], [[ubiquitous-language]]
