---
name: writing-plans
description: >-
  Use when a design is agreed and work needs breaking down - produces bite-sized tasks with
  exact file paths and a verification step each, so progress is checkable rather than
  asserted. Derived from obra/superpowers (MIT), adapted.
---

# Writing plans

## Shape of a task

Each task is **small** — minutes, not hours — and carries:

1. **Exact paths.** `src/pkg/thing.py`, not "the parsing module".
2. **What changes**, concretely enough to execute without re-deriving the design.
3. **A verification step**: the command that shows it worked, and what its output should say.

A task without a verification step is a task whose completion is a matter of opinion.

## Ordering

- Put the task that would **invalidate the plan** first. If an assumption is wrong, find out
  on task 1, not task 9.
- Each task should leave the tree **green**. `make check` passing between tasks is what makes
  a plan resumable — and what stops a half-finished refactor becoming the new baseline.
- Name what is **out of scope**, so scope creep is visible rather than gradual.

## Before starting

Write the plan down and get agreement. Then use `using-git-worktrees` to get an isolated
branch with an honest baseline, and `executing-plans` to work through it.

## While executing

Update the plan as reality diverges — a plan nobody updates stops being read, and its
staleness is invisible until someone trusts it. If a task turns out to be three tasks, say
so rather than quietly widening one.
