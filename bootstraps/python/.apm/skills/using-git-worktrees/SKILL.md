---
name: using-git-worktrees
description: >-
  Use when starting work that should be isolated from the main checkout - creates a worktree
  on its own branch, installs dependencies with uv, and establishes a test baseline that is
  honest about what it did NOT run. Derived from obra/superpowers (MIT), heavily adapted.
---

# Using git worktrees

## 1. Detect existing isolation first

If you are already in a worktree, stop — nesting them is confusing and rarely wanted.

```bash
test "$(git rev-parse --git-dir)" != "$(git rev-parse --git-common-dir)" && echo "already isolated"
```

Note this is also true inside a **submodule**, which is not a worktree. Check for
`.gitmodules` before concluding.

## 2. Prefer the harness's own worktree tool

If the environment provides one, use it. Creating a worktree by hand when the harness has its
own mechanism produces state the harness cannot see, track or clean up.

Only fall back to `git worktree add` when there is no native tool:

```bash
git check-ignore -q .worktrees || echo ".worktrees/" >> .gitignore   # or a commit will swallow the tree
git worktree add .worktrees/<branch> -b <branch>
```

## 3. Set up — `uv`, not pip or poetry

```bash
cd .worktrees/<branch>
uv sync --all-groups
git config --local include.path ../.gitconfig    # committed hooks; see the repo's .gitconfig
```

## 4. Establish a baseline — and be honest about it

**This is the step that matters, and the step most often done wrong.**

```bash
make check
```

**A green baseline in a worktree is a NARROWER claim than the same green on main.** A
worktree lacks every gitignored artifact, and the three failure modes are different:

| Missing | Symptom |
|---|---|
| `.env` — gitignored, so it does not follow a worktree | credential-dependent tests **skip** |
| `.venv` | `make` may silently fall back to system python |
| a gitignored symlink (`logs/`, `models/`, data dirs) | one *raises*; another silently **skips** |

So **compare the skip count against the main checkout**, not just pass/fail:

```bash
uv run pytest -q 2>&1 | tail -1     # here
# and the same on main -- the numbers should match
```

A real measurement of this gap: **237 passed / 12 skipped in a worktree against 242 / 7 on
main.** Reporting the first as "ALL GREEN" is reporting green over a smaller suite.

Also: a script run from a worktree can import the **main checkout's** package, because a
shared venv's editable install beats cwd. If a live run disagrees with a test, check
`module.__file__` before believing either.

If the baseline is not green, **stop and report it**. A baseline you did not establish is not
a baseline, and every later failure becomes ambiguous.

## 5. Two rules while you work

- **Never `git stash`.** `refs/stash` is a single stack shared by *every* worktree of the
  repository. Two sessions stashing concurrently swap each other's work. Use a patch file
  outside the repo, or a throwaway branch.
- **An uncommitted worktree is not a place work can live.** A routine cleanup of worktrees
  has destroyed hours of unstaged work, with nothing for git to recover — nothing had ever
  been staged. **Commit the first file that lands**, however rough.

## 6. Finishing

Use `finishing-a-development-branch`. Do not delete a worktree with uncommitted changes in it.
