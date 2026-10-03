---
slug: externalized-memory
context: stereorepo
synonyms:
  - compiled memory
minted: 2026-09-17
---

# Externalized Memory

**Externalized Memory** is the practice of holding what a session would otherwise remember in artifacts the next participant reads, rather than in the agent that learned it (stereorepo's DR-343, stereorepo's Article 22).

## Not the absence of memory

The rule in `AGENTS.md` — that nothing about this repository is written to the harness's memory, because a memory file is a fact only one session can read — governs where memory is authored, not whether it exists. The harness's own memory surfaces are tracked: `.claude/settings.json` and the skills under `.claude/skills/`, with agent definitions, hooks and instructions under `.meta/.apm/`.

Those skills are not written by hand: each is a render target, so what it says is asserted once and the skill a harness loads is generated from it. Memory here is therefore compiled rather than forbidden: a change to an assertion regenerates the surface every agent reads, and no copy can drift from the source because no copy is authored.

What is given up is the private copy. State the next participant cannot observe is state the system does not have (stereorepo's Article 22).

## Why it is possible here

A fact worth remembering in this repository is a fact about something the repository owns — a program under `.meta/`, a [[knowledge-management|Discipline]], a rule, a term — and each has a file with a name. The routing tree therefore has a destination for every fact, which is what makes a store unnecessary.

A system whose facts concern things it does not own has no such destination. An agent supervising work across repositories it may only read accumulates knowledge about those repositories, about external quotas, and about a person, none of which is an artifact it can write to; a memory store is the only answer available to it. The rule here is not that memory is bad, but that there is somewhere better, and that the somewhere better exists because the subject and the artifact coincide.

## Read by necessity, not by retrieval

A fact in a program is read because someone is editing that program. A fact in a skill is read because the skill's trigger fired. A fact in `AGENTS.md` is read every session by construction. In each case consumption is forced by the work rather than chosen by a retrieval step that may not run.

Stereorepo's Article 8 asks the sharper question: an artifact prevents drift only if something consumes it, and consumption is not sufficient, so ask what it is checked against. A fact beside the code it describes is checked by the mismatch a change would create; a fact in an assertion is checked by `check.py`. The property that matters is not that knowledge survives, but that it is falsifiable where it sits.

## What it costs

Externalizing does not remove a cost. It converts recall into four problems, and much of the repository's apparatus exists to answer them: **routing**, under the [[knowledge-management|Knowledge Management]] discipline and the Diátaxis Compass; **disclosure**, under Progressive Disclosure and the load map that is deliberately insufficient on its own; **retrieval**, through `/search` (`.meta/search.py`); and **freshness**, through `check.py`, dereferenced citations under stereorepo's Article 12, and generation that leaves no second copy to go stale.

The compensation is that these are paid once and apply to everything, where curating a private store is paid per fact and forever.

## Relationship to the pair loop

The pair loop is the same commitment on the coordination side. Its supervisor holds nothing a seat or the developer cannot read for themselves: an Issue's stage is the directory its file sits in, a turn's work is the working tree, and the gate's verdict is its exit code. A seat therefore needs no memory of the protocol, and a protocol it forgets cannot stall. stereorepo's Article 22 is the rule that follows from both.

---

**See also:** [[knowledge-management]], [[ubiquitous-language]], stereorepo's DR-343, stereorepo's Article 8, stereorepo's Article 22.
