---
difficulty: medium
parent: onboard-fitch-mvp
waits_on:
  - portfolio-owns-ratchet-baselines
---

# A recipe syncs a portfolio from a stereorepo checkout

Nothing syncs a portfolio with stereorepo. fitch-mvp was synced twice by
copying `lib.bundle`'s `managed_items()` over it, which never deletes. When
DR-305 made `.meta/adapt.py`, `.meta/lib/adapt/` and
`.meta/checks/probes/tools/test_brownfield.py` scaffold-only, fitch-mvp kept
its copies, and their probe reported `?` until they were removed by hand.

## Wanted

A recipe in a portfolio's rendered `justfile`, run at the portfolio's root and
given the path of a stereorepo checkout, makes every managed path match that
checkout. The suggested shape is a `sync` subcommand of `.meta/bundle.py`,
which is managed and so already ships, with the recipe emitted by
`.meta/lib/render/writers.py`. The recipe runs as follows:

1. **Old and new.** The old managed set is the managed items of the
   portfolio's own `.meta/bundle.yaml`, read before anything is copied. That
   file is itself managed, so the sync replaces it. The new set is the
   checkout's `.meta/bundle.yaml`.
2. **Copy.** For each new managed item, copy the files the checkout's git
   tracks under its `source_path()` to its `dest_path()`, leaving out
   `SCAFFOLD_ONLY_PATHS`. The checkout's untracked and ignored files, such as
   `__pycache__/`, are not copied.
3. **Remove.** Delete each file the portfolio's git tracks that is one of the
   following:
   - under a new managed directory item, but missing from the checkout's copy
     of that directory;
   - under an old managed item that `Bundle.manages()` of the new bundle no
     longer covers;
   - under `SCAFFOLD_ONLY_PATHS`.

   The portfolio's untracked and ignored files are never deleted.

The recipe leaves template items, symlink items, and every other path alone,
including `.meta/baselines/` (DR-314). It does not commit. It prints each path
it copied over a different file, added, or removed, so the developer can
review the diff before committing it.

Because it overwrites and deletes without committing, the recipe refuses,
exiting non-zero and changing nothing, when the given path has no
`.meta/bundle.yaml`, or when the portfolio's git shows uncommitted changes to
any tracked file it would copy over or remove. It does not re-render; the
developer runs `just render` after it, as after any change to `.meta/`.

## Out of scope

- Template and symlink items. Syncing them would need the token substitution
  that Specialization does.
- Managed files that an adopted portfolio integrated by hand, such as
  fitch-mvp's `.gitignore`. The sync overwrites them like any other managed
  file, and the printed diff shows what changed. That problem is
  `managed-files-a-portfolio-integrates` in the backlog.
- Applying an adoption plan to a repository that has never been synced (the
  `adoption-discipline` part).

## Done when

- A test builds two git repositories in a scratch directory: a source with a
  bundle, and a specialized portfolio of an earlier version of that bundle.
  The new bundle drops one managed file item, deletes one file inside a
  managed directory, and adds one managed file. The portfolio also tracks a
  scaffold-only path, a template item, a file of its own, a file under
  `.meta/baselines/`, and an untracked file inside a managed directory.
  After the sync:
  - the dropped item, the deleted file and the scaffold-only path are gone;
  - the added file is present, and so is the new `.meta/bundle.yaml`;
  - the template item, the portfolio's own file, the baseline and the
    untracked file are byte-for-byte unchanged;
  - nothing is committed.
- The test also finds the removed and added paths in the printed list.
- The test runs the sync twice more: once with a path that has no
  `.meta/bundle.yaml`, and once after modifying, without committing, a managed
  file the sync would overwrite. Each exits non-zero and leaves the
  portfolio's working tree as it was.
- A specialized portfolio's `just --list` shows the recipe.

## The plan

The sync goes in a new module, `.meta/lib/bundle/sync.py`. The module works
out every change before it makes any, so that a refusal changes nothing. It
is a library under `lib/bundle/`, which is managed, so every portfolio already
receives it. `.meta/bundle.py` gains a `sync` subcommand, and the rendered
`justfile` gains a `sync` recipe that calls it.

1. **The plan of changes** (`lib/bundle/sync.py`). A function
   `plan(source, portfolio) -> Changes` reads two bundles and lists the
   changes, without touching the disk.
   - It reads the new bundle with `load_bundle(repo_root=source)`, and the old
     one from the portfolio's own `.meta/bundle.yaml`. A missing old bundle
     counts as empty.
   - It gets each side's tracked files from `git ls-files -z`, run on each
     repository. It cannot reuse `lib/adapt/tracked.py`, which is scaffold-only.
   - `Changes` holds three groups: the paths it copies over a different file,
     the paths it adds, and the paths it removes. For copies, it walks each new
     managed item's tracked files under `source_path()`, maps each to
     `dest_path()`, and skips anything under `SCAFFOLD_ONLY_PATHS`. A file
     whose bytes already match is left out. Removals follow the three rules
     under Wanted. The `under` test inside `Bundle.manages()` becomes a
     module-level helper, so `sync.py` can share it.
2. **Refusals** (same module). Before planning, it raises `SyncRefused`, a
   `BundleError`, in these cases:
   - the source has no `.meta/bundle.yaml`;
   - either directory is not a git work tree;
   - the portfolio holds `template/`, which marks it as stereorepo itself.
     Without this check, `just sync` run in the scaffold would delete the
     scaffold's own scaffold-only paths. `checks/files/justfile.py` uses the
     same marker to tell the scaffold from a portfolio.

   After planning, it raises `SyncRefused` if
   `git status --porcelain -z --untracked-files=all` lists any path that the
   plan copies over, adds or removes. The message names those paths.
   `--untracked-files=all` matters: without it git reports an untracked
   directory as one entry, and an untracked file of the portfolio's that the
   checkout now tracks at the same path would be overwritten unnoticed. The
   probe covers that case too.
3. **Apply** (same module). `apply(changes, source, portfolio)` copies files
   with `shutil.copy2`, recreates tracked symlinks as symlinks, deletes the
   removals, and then prunes any directories the removals emptied. It
   returns the three lists so they can be printed.
4. **The subcommand** (`.meta/bundle.py`). `sync SOURCE` runs against
   `--root`, which defaults to the portfolio's root. It prints one line per
   path, prefixed `updated`, `added` or `removed`, and exits 0. On
   `SyncRefused` it prints the reason to stderr and exits 1.
5. **The recipe.**
   - `lib/render/writers.py` emits `sync *args:` (body
     `.meta/bundle.py sync {{args}}`) for every repository, so a portfolio's
     justfile has it.
   - Add `"sync": (("args", FLAGS),)` to `CONTRACT` in
     `checks/files/justfile.py`, but not to `SCAFFOLD_RECIPES`. The justfile
     step then fails in any portfolio whose surface lacks the recipe. The gate
     run inside `test_specialization.py`'s scratch portfolio (step 8) checks
     that, which meets the issue's `just --list` condition.
   - Re-render stereorepo's `justfile`.
6. **Probe** (`checks/probes/tools/sync.py`, imported in
   `checks/probes/tools/__init__.py` before the scaffold-only import). Under a
   temporary directory, it builds the source and portfolio git repositories
   described under Done when. Each repository's bundle has a few items: a
   managed directory, a managed file the new bundle drops, a managed file it
   adds, and a template item. The probe runs `plan` and `apply` through the
   CLI function, so it covers the exit codes and the printed lines, and then
   makes each assertion in Done when:
   - it checks that `git rev-parse HEAD` is unchanged, which shows nothing
     was committed;
   - it runs the two refusal cases, plus a run in a portfolio that holds
     `template/`, and compares `git status --porcelain` and file hashes
     before and after each.
7. **Record.**
   - Write the next Decision Record (DR-315 unless one lands first). It
     says that a sync mirrors the managed items from the checkout's tracked
     files, removes what the bundle dropped and the scaffold-only paths,
     refuses to run over uncommitted changes, and never commits.
   - Its `enacted_in` names a new artifact, `work:artifact/meta-lib-bundle-sync`,
     added to `structure.yaml`.
   - Re-render.

**Risks.**
- **The first sync.** The recipe runs the portfolio's own `bundle.py` and
  `lib/bundle/sync.py`, which a portfolio such as fitch-mvp does not have
  until it has been synced once. Its first sync runs the checkout's tool
  instead: `<checkout>/.meta/bundle.py --root <portfolio> sync <checkout>`.
  So `sync` must take its portfolio from `--root` and never from where
  `bundle.py` lives, and the probe calls it that way, with `--root`. The DR
  states the bootstrap command.
- **The sync replaces itself.** It overwrites `bundle.py` and `lib/bundle/`
  while they run. Python has already loaded them, so this is safe as long as
  `apply` imports nothing lazily from `lib/bundle/` after it starts copying.
- **Deleting a portfolio's own file.** Mirroring deletes any tracked file
  that the checkout lacks under a managed directory. A portfolio that kept its
  own file inside, say, `stakeholders/` or `wiki/stereorepo/` loses it from
  the working tree. It can still be recovered from git, because the sync
  never commits and refuses to run over uncommitted changes. The printed
  `removed` lines are how the developer sees it happen. DR-314 already moved
  the one known case, the baselines, out of the managed directories.
- **Relative paths.** `just` runs the recipe from the root, so a relative
  SOURCE is read relative to the portfolio's root, not to wherever the
  developer ran it from. The subcommand resolves SOURCE against the current
  directory and states the root in its help text.
- **`source_revision: dynamic`.** The bundle is copied as it is, with the
  word `dynamic` rather than a fixed revision. That matches what
  Specialization does today, so the sync leaves it alone.

## What was built

The plan held. These are the places where the code differs from it, and
what the next reader should know.

- **Names.** The exception is `SyncRefusedError`, not `SyncRefused`,
  because ruff's N818 wants the suffix. `Bundle.manages()`'s inner helper is
  now two module-level functions in `lib/bundle/__init__.py`: `under(relative,
  root)` and `scaffold_only(relative)`. `sync.py` and `manages()` both use
  them.
- **One rule the plan did not state.** A removal never touches a path under
  a template or symlink item of the *new* bundle. Without that rule, an item
  that moved from managed to template, such as a hypothetical `README.md`,
  would be deleted because the old bundle managed it.
- **Recorded as DR-315.** Its `enacted_in` leaves out
  `checks/files/justfile.py`, because the `enacting citations` step requires
  every named file to cite the DR back, and the contract entry is one line
  that needs no decision. DR-315 also records the first-sync bootstrap
  command.
- **`bundle.py`'s `main`.** It now takes `argv` and returns the exit code,
  and the `__main__` block wraps it in `sys.exit(main())`, so the probe calls
  it in-process. `sync` is imported through the existing
  `from lib.bundle import (...)` statement, which needs no new `noqa`.
- **Git environment.** `sync._git` drops `GIT_DIR`, `GIT_WORK_TREE` and
  `GIT_INDEX_FILE`, so that a sync run from a hook still reads the
  repositories it was given. The probe's commits pass their own identity and
  `commit.gpgsign=false`, so they never reach the developer's signing setup.
- **What was run.** `just gate meta` passes, with the new `bundle sync
  probes` step. `CI=1 just test-specialization` passes. Its step 8 gate runs
  the justfile contract in the scratch portfolio, which shows that the
  portfolio's surface carries `sync`.
- **A failure while applying.** `bundle.py sync` reports an `OSError` raised
  by `apply` apart from a refusal raised by `plan`. Once copying has started,
  the portfolio is partly synced, and the message says so and points to
  `git status`, instead of claiming that nothing changed.
- **Its own stakeholders are at risk.** `stakeholders/` is a managed directory, so a
  sync removes every Persona and Role the portfolio wrote there. The
  `removed` lines show it, and git can recover the files. The fix belongs to the
  bundle rather than the sync: `sync-keeps-a-portfolios-stakeholders` in
  the backlog.
- **Not done here: a sync of fitch-mvp itself.** The seats cannot reach that
  repository. Its first sync is
  `<stereorepo>/.meta/bundle.py --root <fitch-mvp> sync <stereorepo>`,
  followed by `just render` and a review of the printed `removed` lines.
  `.gitignore` will be among the `updated` lines; see
  `managed-files-a-portfolio-integrates`.
