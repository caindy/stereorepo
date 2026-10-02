---
difficulty: easy
parent: onboard-fitch-mvp
---

# Plan adoption from the files the target repository tracks

`just adapt plan` walks the target's working tree (`_scan_target_files` in
`.meta/lib/adapt/plan.py`) and skips only `DEFAULT_IGNORES` and a product
configuration's `ignore` list. Whatever else is on disk becomes part of the
plan, whether or not the repository tracks it.

## How to reproduce it

Run `just adapt plan /Users/christopher/fitch-mvp`. The repository tracks 65
files. The plan lists 3,094 `RETAIN` entries: 2,723 under `.jj/repo`, 278 under
a leftover `.claude/worktrees/` checkout, and others under `.pytest_cache/`
and `schema/generated/`. The one conflict and two integrations are lost among
them.

## Wanted

- The plan considers the target's tracked files when the target is a git
  repository (`git ls-files`), and falls back to the walk otherwise.
- A scaffold item is still `CREATE` when its path is untracked in the target,
  and becomes `CONFLICT` if an untracked file occupies the path, since applying
  the plan would overwrite it.
- A test in `.meta/checks/probes/tools/test_brownfield.py` over a temporary
  git repository holding untracked and ignored files.

## Out of scope

- Applying the plan.
- How `.gitignore` is integrated.
