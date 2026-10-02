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

- When the target is the top level of a git work tree (`git -C <target>
  rev-parse --show-toplevel` names the target itself, both paths resolved,
  since a temporary directory on macOS sits behind the `/var` symlink), the target-side entries
  of the plan (the loop over `_scan_target_files` in `build_adoption_plan`)
  come from `git -C <target> ls-files -z`, not from the walk. A tracked path
  that is not a file or symlink on disk (deleted, or a submodule's directory)
  is left out. `DEFAULT_IGNORES` and the configuration's `ignore` list still
  apply to tracked paths.
- Planning stays read-only: only `rev-parse` and `ls-files` are run, nothing
  that writes the target's `.git` (no `git status`, which may refresh the
  index).
- When the target is not the top of a git work tree (including a directory
  nested inside some other repository), or `git` is missing or fails, the walk
  is used as it is today.
- The classification of scaffold (bundle) items is unchanged: it still looks
  at the disk. A scaffold path that nothing occupies is `CREATE`, tracked or
  not. A scaffold path occupied by an untracked file whose content differs is
  `CONFLICT`, because applying the plan would overwrite it.

## Out of scope

- Applying the plan.
- How `.gitignore` is integrated.
- Reading tracked files from a non-git version control system (a `.jj`
  repository without a colocated `.git` falls back to the walk).

## Done when

A new case in the brownfield probe (`test_brownfield_probes` in
`.meta/checks/probes/tools/test_brownfield.py`, alongside
`_check_conflicts` and the others, with the `Passed` count bumped) builds a
temporary git repository holding a tracked file, a tracked file then deleted
from disk, an untracked file, a file matched by its `.gitignore`, and an
untracked file at a scaffold path, then checks that the plan:

- lists the tracked file as `RETAIN`;
- does not list the deleted tracked file;
- lists neither the untracked nor the ignored file;
- marks the untracked file at the scaffold path `CONFLICT`;
- marks an unoccupied scaffold path `CREATE`.

The existing cases plan plain temporary directories with no `.git` and keep
passing unchanged, which covers the fallback.

## The plan

Two files change: `.meta/lib/adapt/plan.py` and
`.meta/checks/probes/tools/test_brownfield.py`. (As built, the git listing
went into a new `.meta/lib/adapt/tracked.py`, asserted as an Artifact in
`structure.yaml`, because `plan.py` would otherwise pass its 500-line
ceiling.)

1. **`plan.py`: list tracked files.** Add `_git_tracked_files(target_dir) ->
   list[str] | None`. Its steps:
   - Run `git -C <target> rev-parse --show-toplevel`. Return `None` unless the
     resolved output equals the resolved target.
   - Run `git -C <target> ls-files -z`, split on NUL, and return the paths.
   - Return `None` on `FileNotFoundError` (no `git`) or a non-zero exit.

   Both commands use `subprocess.run(..., capture_output=True, check=False)`.
   The environment they run in has every `GIT_*` variable removed (see Risks).
2. **`plan.py`: choose the source of target files.** In `_scan_target_files`,
   call `_git_tracked_files` first. If it returns a list, keep a path only
   when:
   - it is not ignored (`_is_ignored`), and
   - on disk it is a file or a symlink: `is_symlink()`, or `is_file()` when it
     is not a symlink.

   This drops deleted paths and submodule directories. Return the kept paths
   deduplicated and sorted (`sorted(set(...))`): during an unfinished merge
   `ls-files` prints an unmerged path once per stage, and a duplicate here
   would become a duplicate `PlannedAction`. If it returns `None`, walk the tree exactly as today.
   `build_adoption_plan` and `_classify_bundle_item` stay as they are, so
   scaffold items are still classified from what is on disk. Update the
   docstring.
3. **Probe: add the new case.** Add `_check_tracked_files(scaffold_dir, tmp)`.
   - Make `tmp / "git_target"` and run `git init -q` in it.
   - Write the tracked file `src/app.py`, the file `gone.py` and a
     `.gitignore` holding `build/`.
   - `git add` those three, then delete `gone.py`. Staging alone puts paths in
     the index, which is what `ls-files` reads, so the case makes no commit.
     That avoids needing a commit identity and the developer's GPG signing.
   - Write the untracked file `scratch.txt`, the ignored file `build/out.txt`,
     and an untracked `.meta/render.py` whose content differs from the
     scaffold's.

   The plan must then show:
   - `src/app.py` as `RETAIN`;
   - none of `gone.py`, `scratch.txt` or `build/out.txt`;
   - `.meta/render.py` as `CONFLICT`;
   - `GEMINI.md` as `CREATE`.

   Register the case in `test_brownfield_probes`, add an item to its
   docstring list, and change `Passed("7 adoption cases")` to 8. If `git` is
   missing, the case reports a problem; `git` is a prerequisite of the
   repository.

## Risks

- **Inherited git environment.** When the probe runs under a git hook or the
  pair loop, `GIT_DIR`, `GIT_INDEX_FILE` or `GIT_WORK_TREE` may be set. These
  override `-C` and would point the commands at the scaffold's own repository.
  Clear `GIT_*` from the environment in `_git_tracked_files` and in the
  probe's own `git` calls.
- **Path comparison on macOS.** `rev-parse` prints the real path
  (`/private/var/...`), while the temporary directory is given as `/var/...`.
  Compare both with `.resolve()`. `build_adoption_plan` already resolves the
  target.
- **Other repositories' configuration.** A target owned by another user makes
  `rev-parse` fail ("dubious ownership"). That falls back to the walk, which
  is acceptable.
- **Read-only invariant.** `_check_readonly_invariant` hashes plain
  directories only. `ls-files` and `rev-parse` do not write the index, so no
  change is needed there.

## Notes

- `git_tracked_files` and its `_git` helper live in `.meta/lib/adapt/tracked.py`;
  `_scan_target_files` in `plan.py` calls it and keeps the walk as the fallback.
- `just adapt plan /Users/christopher/fitch-mvp` now lists 96 `RETAIN`, 2
  `INTEGRATE` and 4 `CONFLICT` entries (`.gitignore`, `DR-001.yaml`,
  `domain_vocabulary.yaml`, `structure.yaml`), against 3,094 `RETAIN` before.
  The issue reported one conflict. Conflicts are scaffold paths, which this change
  still classifies from the disk as before, so the difference is probably that
  the target changed since the issue was written. That was not checked.
- The new probe case was checked to pass. It was not run against the old walk
  to see it fail; reading it, the walk would plan `scratch.txt` and
  `build/out.txt` and fail on both.
