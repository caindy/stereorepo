---
name: executing-plans
description: >-
  Use when working through an agreed plan - executes tasks in batches with checkpoints,
  keeping the tree green between tasks and reporting honestly when reality diverges from the
  plan. Derived from obra/superpowers (MIT), adapted.
---

# Executing plans

## The cycle, per task

1. Re-read the task. If it is no longer right, say so **before** doing it.
2. Make the change.
3. Run the task's own verification step.
4. Run `make check`. Green before moving on.
5. Commit. Small commits are what make a bisect useful later.

## Checkpoints

Batch a few related tasks, then stop and report: what landed, what the gate said, and what
changed about the plan. **Report the gate's actual output**, not a summary of it — see
`verification-before-completion`.

## When reality diverges

It will. The failure mode is not divergence; it is **silent** divergence.

- A task turns out to be wrong → stop, say why, propose the correction.
- A task turns out to be three tasks → say so; do not quietly widen one.
- The gate goes red for an unrelated reason → **diagnose it, do not route around it**. A gate
  that is red for reasons unrelated to your change trains re-running until green, which is
  exactly how a real failure gets waved through. `docs/TRAPS.md` covers the common causes.

## What not to do

- Do not batch so far ahead that a wrong assumption costs the whole batch.
- Do not leave the tree red between tasks.
- Do not mark a task done because the code is written. It is done when its verification step
  passed and you read the output.
