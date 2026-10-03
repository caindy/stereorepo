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

## What the spike answered

These questions were put to the first run of the loop, a spike in the
booktutor repository that took 12 Issues through 81 turns. The answers below
are its evidence, from `docs/PAIR_LOOP_SPIKE.md` in caindy/booktutor at
commit `cdfa78d`, and the runs it names are that document's hypothesis runs.

**Does a headless seat behave as an interactive session does, with the same
skills, hooks, instructions and subscription login?** Yes. Skills,
`CLAUDE.md`, git hooks and the subscription login all behaved as usual.

**How many tokens does each turn read from the prompt cache, and does that
number rise across a seat's turns?** Within an Issue, the hit ratio was 0.95
to 0.98. A fresh session is the expensive part: with the default flags, each
seat's first turn in run H7 wrote 86,000 to 87,000 tokens to the cache, and
in the follow-up probes a fresh session settled at about 79,000. Turning off
setting sources, skills and MCP, and appending `CLAUDE.md` to the system
prompt, let a fresh session read about 102,000 tokens and write about 2,400.
Those flags also take away the skills and project settings, which is why the
first answer holds only for the default flags. Whether reads rise across a
seat's turns was measured only in the pre-flight check, where they went from
22,196 to 30,588 tokens over two turns; no longer run was measured.

**How well does it work for the developer to take over a seat and hand it
back?** It works (run H6). The developer stops the loop between turns,
resumes the seat's session, and makes an edit; on the next run the loop
commits the edit as the developer's turn and resumes the same session, whose
next turn acts on the edit. The seat did not recall the exchange in words.

**Which set of tool permissions works for a seat?** Not an allow-list of
command prefixes (run H9). It caused 75 denials in 81 turns, none of them of
anything dangerous: 62 were compound shell commands built from allowed parts.
The spike recommends a sandbox confined to the worktree, with a short deny
list for the git verbs that belong to the loop, but it did not test one.

---

**See also:** [[supervisor]], [[quiet-turn]], [[developer]], [[ubiquitous-language]]
