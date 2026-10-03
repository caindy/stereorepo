---
difficulty: developer
waits_on:
  - specialized-portfolio-gate
---

# Cut an APM release with a recipe instead of a workflow

The APM package (`.meta/apm.yml`, DR-206) was released by a GitHub Actions
workflow on a `v*` tag: it ran the gate, `just apm validate` and
`just test-specialization`, then created a GitHub Release. The bootstrap
removed every workflow, since the pair loop gates each Issue locally before
it lands, so nothing now cuts a release. `.meta/.apm/README.md` says "The
procedure is not yet a recipe."

## Wanted

A recipe, `just release <version>`, with a `--dry-run` flag, invoking a tool
under `.meta/` like every recipe. The justfile is generated, so the recipe is
declared in `.meta/assertions/structure.yaml` and re-rendered. In order, it:

1. refuses on a dirty tree, on a branch other than `main`, on a `main` that
   differs from the remote's after a fetch, on a tag `v<version>` that already
   exists, or on a `<version>` that is not the one `.meta/apm.yml` declares;
2. runs `just gate`, `just apm validate` and `just test-specialization`, and
   refuses if any fails;
3. tags `v<version>`, pushes the tag, and creates the GitHub Release.

With `--dry-run` it does steps 1 and 2 and prints what step 3 would do.

It waited on `specialized-portfolio-gate` because `just test-specialization`
failed, which would have made the recipe refuse every release; that Issue has
landed.

## Out of scope

- Publishing an actual release. That is the developer's act, never the
  pair's: seats run only `--dry-run` and the refusal paths.
- Bumping `.meta/apm.yml`'s version, or writing a changelog or release notes beyond what
  `gh release create --generate-notes` writes.

## Done when

- Tests against a scratch repository with a local bare remote show each
  refusal of step 1: a dirty tree, a branch other than `main`, a `main` behind
  or ahead of the remote, an existing `v<version>` tag, and a version that
  differs from `.meta/apm.yml`'s. Each exits non-zero, says why, and leaves no
  tag.
- A test with the step-2 commands stubbed shows that one failing check stops
  the release before any tag, and that `--dry-run` on a clean, current `main`
  exits zero, prints the tag and `gh release create` it would run, and creates
  neither.
- `just --list` shows `release`, and `.meta/.apm/README.md` names the recipe
  in place of "The procedure is not yet a recipe."
- At the desk check the developer runs `just release <version> --dry-run` on
  their checkout and reads what it would publish.

## The plan

### Files and seams

- **`.meta/release.py`** (new), a uvx/pyyaml script shaped like
  `.meta/test_specialization.py`: an argparse parser (`version`, `--dry-run`)
  and one entry, `release(root, version, dry_run, checks=CHECKS, out=print)`,
  that returns an exit code. `root` and `checks` are the seams the probe
  injects through: `root` is the repository it acts on, and `checks` is the
  list of step-2 commands (default `just gate`, `just apm validate`,
  `just test-specialization`, run from `root`). Each refusal message is a
  module-level constant with a docstring, as `test_specialization.py` does.
  - `refusals(root, version) -> list[str]`, step 1: `git status --porcelain`
    is empty; `git branch --show-current` is `main`; `git fetch origin main`
    then `rev-parse HEAD` equals `rev-parse origin/main`; `git rev-parse -q
    --verify refs/tags/v<version>` fails (also `git ls-remote --tags origin`
    so a tag only on the remote counts); `version` equals the `version:` of
    `<root>/.meta/apm.yml`. It reports every refusal at once, not just the
    first.
  - Step 2 runs each check in order and stops at the first non-zero exit,
    naming it.
  - Step 3 builds the commands `git tag -a v<version> -m v<version>`,
    `git push origin v<version>`, `gh release create v<version> --verify-tag
    --title v<version> --generate-notes`. With `--dry-run` it prints them and
    runs none; otherwise it runs them in order.
- **`.meta/lib/render/writers.py`** `justfile()`: a `release *args:` recipe,
  `uvx --python 3.13 --with pyyaml python .meta/release.py {{args}}`,
  emitted when `work:artifact/meta-release` is asserted, as
  `test-specialization` is, with a `# ...` comment line above it, because
  that line is what `just --list` shows. Then `just render` regenerates `justfile`.
- **`.meta/assertions/structure.yaml`**: artifacts `meta-release`
  (`.meta/release.py`) and `meta-checks-probes-tools-release`.
- **`.meta/checks/probes/tools/release.py`** (new) and an import in
  `.meta/checks/probes/tools/__init__.py` (and its docstring's list).
- **`.meta/.apm/README.md`** line 88: name `just release <version>`
  (`--dry-run` to see what it would publish) in place of "The procedure is
  not yet a recipe."
- **`.meta/assertions/decisions/DR-320.yaml`**: a release is cut by the
  developer with `just release`, not by a workflow on a tag, since the
  bootstrap removed the workflows; re-render so `decisions.md` lists it.

### Order

1. `release.py` with `refusals`, the check runner and the dry-run printer.
2. The probe, run with `just gate meta` while working only as a targeted
   check.
3. Artifacts, recipe in `writers.py`, DR-320, `just render`.
4. README line.

### Tests (the probe)

Each case builds, under a temporary directory, a bare repository as
`origin` and a clone on `main` with one commit holding `.meta/apm.yml`
(`version: 0.1.0`), pushed. Checks are injected as `["true"]` or
`["false"]` so no real gate runs. Cases, each asserting a non-zero return,
the expected message, and `git tag -l` empty in clone and origin:

- an untracked file in the clone (dirty tree);
- on a branch `other`;
- `main` behind (a second clone pushes a commit) and ahead (an unpushed
  local commit);
- `v0.1.0` already tagged locally, and tagged only on origin;
- version `0.2.0` against the manifest's `0.1.0`;
- a clean tree with checks `[["true"], ["false"]]`: refused at the
  second check, no tag.

And one passing case: clean, current `main`, checks `[["true"]]`,
`dry_run=True`: returns 0, output names `git tag -a v0.1.0`,
`git push origin v0.1.0` and `gh release create v0.1.0`, and no tag exists.
Every case, refusals included, passes `dry_run=True`. Step 1 runs
`gh auth status` on a real run, so a refusal case without `dry_run` would
call `gh` and, on a machine with no `gh` login, also refuse for that reason,
which would muddy the message it asserts. With `dry_run` throughout, no
probe can push or call `gh`.

### Risks

- **A real publish from a test.** Kept out by construction: every probe
  case is `dry_run=True`. The
  remote is always a local bare repository.
- **`just gate` inside step 2 recursing.** The probe runs inside the gate, so
  it must never use the default `CHECKS`; every case passes `checks`.
- **Portfolios.** (Corrected while implementing: the plan said
  `test_specialization.py` ships to a portfolio. It does not; it is absent
  from the Specialization discipline's *Copy what is inherited* list, and its
  probe returns no problems where the script is absent.) `release.py`
  follows it exactly: not inherited, not added to `SCAFFOLD_ONLY_PATHS`, and
  its probe, which does ship inside `.meta/checks/`, returns no problems
  where `.meta/release.py` is absent. The recipe is rendered only where
  `work:artifact/meta-release` is asserted, which a portfolio's own
  `structure.yaml` does not do.
- **A half-made release.** Step 3 runs three commands in turn, so a
  `gh release create` that fails after `git push origin v<version>` leaves a
  pushed tag with no Release, and a retry is refused at step 1 because the tag
  exists. Two guards: on a real run (not `--dry-run`), refuse in step 1 if
  `gh auth status` fails, so neither a tag nor the long step 2 is spent on a
  release that cannot be published; and if `gh release create` fails after the push,
  exit non-zero and print that command so the developer can run it by hand
  (`--verify-tag` accepts the tag that already exists). Neither guard is
  probed, because every probe case runs with `dry_run`.
- **Git identity in the scratch repository.** Set `user.name`/`user.email`
  per repository and `GIT_CONFIG_GLOBAL=/dev/null`, and turn off
  `tag.gpgSign`/`commit.gpgSign`, so the probe runs the same on any machine
  and under the seat sandbox.

## Notes for the next reader

- **Seams the plan missed.** `.meta/checks/files/justfile.py`'s `CONTRACT`
  declares every recipe's parameters (stereorepo's DR-259), so `release`
  is declared there as taking flags. A citation in an inherited file must
  read "stereorepo's DR-320", never bare.
- **Shape of `release.py`.** Step 1 is split into `_branch_refusals`,
  `_version_refusals` and `_gh_refusals` to stay under ruff's branch limit;
  `refusals` joins them and asks `gh` only when not `dry_run`. Each
  message is a module constant, and the probe asserts the fixed text before
  the first `{` of the constant it names, so rewording a message does not
  break the probe.
- **A push that fails** after `git tag -a` deletes the local tag again, so the
  retry is not refused at step 1 for a tag that never reached `origin`. Like
  the guard for a half-made release, this is not probed, because it only
  happens on a real run.
- **The probe** is the `release probes` step of the meta gate
  (`.meta/checks/probes/tools/release.py`). It strips `GIT_*` from the
  environment and points `GIT_CONFIG_GLOBAL` at `/dev/null` while it runs,
  since `release.py` runs git with the environment it inherits.
- **Render in the seat sandbox.** `just render` wrote `justfile` and
  `.meta/decisions.md`, then stopped on a permission error writing
  `.claude/skills/`, which the seat sandbox denies (the backlog Issue
  `render-in-seat-sandbox`). Nothing under `.claude/` changes in this
  Issue, and the meta gate's render-freshness steps pass.
- **Not run.** No real release, and no `just release <version> --dry-run`
  against this checkout: it runs the whole gate as its step 2, which a
  seat does not run. That is the developer's desk check.
