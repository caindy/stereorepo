---
name: writing-skills
description: >-
  Use when creating or editing a skill in .claude/skills/ - covers the trigger-shaped
  description that determines whether a skill activates at all, and the rules for editing a
  vendored skill. Derived from obra/superpowers (MIT), adapted.
---

# Writing skills

## The description is the activation mechanism

A skill activates on its `description`, so write it as a **trigger**, not a summary:

> "Use when about to claim work is complete, fixed, or passing…"

not

> "A skill about verification."

Name the *situations*. If you cannot state when it should fire, it will not fire — or it will
fire constantly, which is worse, because a skill that always applies is one people learn to
ignore.

## Content

- **One job per skill.** Two jobs means neither trigger is clean.
- **Rules, not narrative.** State the rule, then the pointer. A skill that grows a story per
  recurrence becomes unreadable exactly as it becomes well-evidenced.
- **Say what the failure looked like** where it is short. A rule with a remembered failure
  attached survives; a bare imperative gets rationalised away.
- **Point at repo files** rather than restating them. `docs/TESTING.md` and `docs/TRAPS.md`
  are the long forms; duplicating them here creates a second source of truth that will drift.

## Editing a vendored skill

Some skills here are vendored from upstream projects — see `PROVENANCE.md`.

- **Record the modification in `PROVENANCE.md`.** A locally-edited skill is excluded from
  refresh; an unrecorded edit is silently reverted the next time upstream is pulled.
- **Keep the licence notices.** Both upstreams are MIT and require the notice to travel.
  These skills are seeded into every generated project, so an omission propagates.
- Prefer *extending* a vendored skill over rewriting it, so a refresh diff stays readable.

## Before adding a new skill

Ask what consumes it. A skill nobody invokes is an artifact with no consumer, and the charter
has an invariant about those.
