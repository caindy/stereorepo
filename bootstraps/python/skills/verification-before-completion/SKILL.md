---
name: verification-before-completion
description: >-
  Use when about to claim work is complete, fixed, or passing, and before committing or
  opening a PR - requires running the verification command and reading its output before
  making any success claim. Evidence before assertions, always. Derived from
  obra/superpowers (MIT), adapted.
---

# Verification before completion

## The rule

**Evidence before claims, always.** No statement that something is complete, fixed, or
passing without *fresh* output from a command that would have shown otherwise.

## The gate

1. **Identify** the command that would prove the claim false if it were false.
2. **Run** it, completely and freshly. Not a previous run; not a subset.
3. **Read** all of it, including the exit code.
4. **Judge** whether the output actually supports the claim — not whether it looks fine.
5. **Report** what it showed.

In this repository that command is:

```bash
make check
```

## Red flags in your own drafts

- "should work", "probably", "seems to", "looks right"
- "Done!" or "Fixed!" written before the command was run
- Reporting a subagent's or tool's claim without confirming it yourself
- Citing a run from *before* the last edit

## Three specific traps

**A green gate is a claim with a scope.** Read what it says it checked. A checker over a
hand-written file list passes unconditionally over everything outside that list.

**A worktree's green is narrower than main's.** A worktree lacks gitignored artifacts, so
credential- and data-dependent tests skip rather than fail. Compare the **skip count**, not
just pass/fail. See `using-git-worktrees`.

**A test that has never failed is not evidence.** If you wrote or changed a test, break the
thing it guards and watch it go red, then restore. A guardrail never observed to fail is not
evidence of anything — see `docs/TESTING.md`.

## When it will not pass

Say so plainly, with the output. A failing gate reported honestly is worth more than a
passing claim that has to be retracted — and far more than a green run nobody looked at.
