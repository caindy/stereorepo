---
name: finishing-a-development-branch
description: >-
  Use when the tasks on a branch are complete - verifies the gate, closes out the
  documentation the change owed, then presents merge/PR/keep/discard options and cleans up
  the worktree. Derived from obra/superpowers (MIT), adapted.
---

# Finishing a development branch

## 1. Verify, for real

```bash
make check
```

Read the output. If this was done in a worktree, remember its green is a **narrower claim**
than main's — compare skip counts (see `using-git-worktrees`).

## 2. Close the documentation the change owed

Per the charter's routing table, in the **same** change wherever possible:

- A rule changed → `CLAUDE.md`. A rule change ships with its code: it is a claim about the
  code, verifiable now.
- A decision with rejected alternatives → an ADR, and cite it from the value it governs.
- What happened, including a diagnosis whose conclusion outlives its fix →
  `docs/JOURNAL.md`, using `docs/JOURNAL-TEMPLATE.md`.
- Something turned out never to have existed, or an investigation is exhausted →
  `docs/NOT-TRUE.md`. This is the one most often skipped and the one that saves the most
  time later.

**A verification record is the exception to "same commit"** — it postdates the code by
definition. Deferring it is fine; carrying the debt across a topic change is not.

## 3. Present the options — do not choose unilaterally

State what the branch contains and what the gate said, then offer: **merge**, **open a PR**,
**keep the branch**, or **discard**. Merging or pushing is the user's call unless they have
already said otherwise.

## 4. Clean up

Only after the branch is merged or explicitly abandoned:

```bash
git worktree remove .worktrees/<branch>
git worktree prune
```

**Never remove a worktree with uncommitted changes.** Git cannot recover work that was never
staged, and a routine cleanup has destroyed hours of it.
