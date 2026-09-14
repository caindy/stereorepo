---
name: brainstorming
description: >-
  Use before writing code for anything non-trivial - refines a rough idea into a design
  through questions, explores alternatives, and presents the design for validation before
  implementation starts. Derived from obra/superpowers (MIT), adapted.
---

# Brainstorming

Do not start writing code. Start by finding out what is actually wanted.

## 1. Ask until the ambiguity is gone

Ask about the problem, not the solution: who hits this, what happens today, what "done"
looks like, what must **not** change. Prefer questions whose different answers lead to
*different work* — anything else is conversation.

## 2. Explore at least two approaches

One option is not a decision. For each: what it costs, what it forecloses, and how it fails.

**State a recommendation.** A survey of options with no recommendation pushes the work back
onto the person who asked.

## 3. Present the design in sections, for validation

Small enough to disagree with. Get agreement on the shape before any code exists — the
cheapest moment to be wrong.

## 4. Record it, and route it correctly

Per the charter's routing table:

- **Forecloses alternatives *and* has a nameable revisit condition** → an ADR
  (`docs/adr/`). This is the common case for a design.
- **Still open, but you can name the probe that would settle it** → a bet (`docs/BETS.md`).
- **Deliberately not being done** → `docs/PARKED.md`, and note the rule there: nothing
  written for parked work may constrain a core design decision later.
- **Otherwise** → a journal entry, with the rejected alternative, which is the part the code
  cannot record.

**A design that lives only in a chat transcript has not been decided.**
