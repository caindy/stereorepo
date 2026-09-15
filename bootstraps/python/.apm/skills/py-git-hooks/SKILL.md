---
name: py-git-hooks
description: Set up git pre-commit hooks to run ruff, mypy, and basedpyright before commits. Use when configuring automated quality checks in git workflow.
status: stable
---

# Python Git Hooks Setup

Configure git pre-commit hooks using the pre-commit framework to enforce code quality before commits.

## Target contexts

A solorepo portfolio holds two kinds of Python target, and this skill behaves
differently in each.

- **Repository tooling — `.meta/`.** Inherited by every portfolio through
  Specialization. Configured by `.meta/ruff.toml` and `.meta/mypy.ini`, run
  through `python3` and `uvx`, held by `just gate meta`. It has no
  `pyproject.toml`, no `[dependency-groups]`, and no `tests/`.
- **A Project workspace** — the directory of any Project that
  `assertions/structure.yaml` declares with a `gate:` of its own, such as
  `bootstraps/python/seed`. It owns its `pyproject.toml` and its dependency
  groups, and is held by `uv run gate` run from its own directory.

Which one you are in is settled by `assertions/structure.yaml`, not by the path:
`just bootstrap python products/api` puts a Project at `products/api`. Anything
under `.meta/` is repository tooling. **py-quality-setup** holds the contract in
full, including why every checker must be given its target's configuration by
name.

### Do not run `pre-commit install` in a repository that sets `core.hooksPath`

solorepo sets it:

```console
$ git config core.hooksPath
.meta/hooks
```

`.git/hooks/` is therefore dead here, and nothing reads what is written into it.
`.meta/hooks/` holds the hooks that are live: `post-checkout`, which materializes
the single-source APM assets into each harness on branch switch and new worktree
(solorepo's #430), alongside the Claude Code `PreToolUse` hooks
`signed_channel.py` (solorepo's DR-069) and `worktree_only.py` (solorepo's
DR-110). It is a tracked directory, so anything installed there is committed and
propagates into every portfolio.

pre-commit knows about the setting and refuses:

```console
$ pre-commit install
[ERROR] Cowardly refusing to install hooks with `core.hooksPath` set.
hint: `git config --unset-all core.hooksPath`
```

**The hazard is the hint, not the refusal.** Following it detaches
`.meta/hooks/post-checkout` and hands the hook path back to pre-commit, and
neither the unset nor the missing projection announces itself afterwards. Do not
run the hint. (`pre-commit install --force`, which this skill's Troubleshooting
section recommends below, is not a flag pre-commit has; it exits with
`unrecognized arguments: --force`.)

**Where pre-commit enforcement goes instead.** To the gate, which is the thing a
merge is held to:

```bash
just gate meta                 # repository tooling
cd <project> && uv run gate    # a Project workspace
just gate                      # every Project the assertions declare
```

The Stop hook lint gate below is the part of this skill that does apply, in both
targets. Use this package's `lint-gate.py`, described in the next section — not
an upstream copy.

## Objectives

1. Install pre-commit framework with Python quality hooks
2. Migrate any existing manual hooks to pre-commit framework
3. Configure Claude Code Stop hook lint gate (runs full lint suite before returning to user)
4. Ensure hooks run incrementally on changed files only
5. Auto-fix issues where possible, block on critical errors

## Required Tools

**In a solorepo portfolio**, none of these are added for hook management: the
enforcement point is the gate, and `pre-commit` is not installed. What remains of
this skill is the Stop hook lint gate, which reaches `ruff` and `mypy` the way its
target does — `uvx` for `.meta/`, `uv run` inside a Project.

**Elsewhere**, add to `[dependency-groups]` dev: `"pre-commit"`, `"ruff"`, `"mypy"`.

- **pre-commit**: Hook management framework
- **ruff**: Fast linter with auto-fix capability
- **mypy**: Standard Python type checker
- **basedpyright**: not part of this standard. Nothing here runs it, and the
  lint gate does not invoke it.

**Permissions**: Run py-quality-setup first to configure `.claude/settings.local.json` with all needed tool permissions.

## Setup Workflow

### Step 1: Check for Existing Hooks

**Check `core.hooksPath` first.** If it is set, stop: steps 2 to 4 do not apply,
and the reasons are in Target contexts above. Go to step 5.

```bash
git config core.hooksPath          # set? then .git/hooks/ is dead, and so is this section
ls -la .git/hooks/pre-commit 2>/dev/null
```

### Step 2: Create Pre-commit Configuration

Create `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.8.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.13.0
    hooks:
      - id: mypy
        additional_dependencies: []  # Add type stubs as needed

  - repo: local
    hooks:
      - id: basedpyright
        name: basedpyright
        entry: basedpyright
        language: system
        types: [python]
        pass_filenames: true
```

### Step 3: Install Hooks

**Not in a repository that sets `core.hooksPath`** — see step 1.

```bash
# Install pre-commit to project venv
uv pip install pre-commit

# Install git hooks
pre-commit install

# Verify installation
ls -la .git/hooks/pre-commit
```

### Step 4: Test Hooks

```bash
# Run on all files (initial validation)
pre-commit run --all-files

# Or test on staged files only
git add some_file.py
pre-commit run
```

### Step 5: Configure Claude Code Stop Hook Lint Gate

**Strongly recommended, and the part of this skill that applies in every
target**: Configure a Claude Code `Stop` hook that runs ruff and mypy on modified
Python files before Claude returns control to the user. If either reports errors,
Claude is blocked from stopping and must fix them first.

This replaces the older `PostToolUse` approach (which ran ruff after every individual edit, generating noise on intermediate states).

**Install the lint gate script** (symlink so updates propagate automatically):
```bash
mkdir -p ~/.claude/hooks
ln -sf ~/.claude/skills/py-git-hooks/lint-gate.py ~/.claude/hooks/lint-gate.py
```

**Configure the Stop hook** in `~/.claude/settings.json`:

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 ~/.claude/hooks/lint-gate.py"
          }
        ]
      }
    ]
  }
}
```

**How it works**:
- Fires once when Claude finishes responding, before the user sees the result
- Finds modified `.py` files via `git diff` (staged, unstaged, and untracked)
- Routes each file to its target: a path under `.meta/` is checked against
  `.meta/ruff.toml` and `.meta/mypy.ini`; a path inside a Project workspace runs
  through that Project's `uv run`, from the Project's own directory
- **Auto-fix pass**: runs `ruff check --fix`, always with the target's `--config`,
  to silently fix trivial issues such as import sorting. It runs **no formatter**:
  mechanical formatting was retired from this standard (solorepo's DR-193)
  because it inflates agent context windows and manufactures rebase churn across
  concurrent branches for no semantic gain
- **Check pass**: runs `ruff check` and `mypy` to find remaining unfixable errors.
  No `basedpyright`: nothing here runs it, so its findings would block on a
  standard no gate holds
- If errors remain: returns `{"decision": "block", "reason": "..."}` — Claude sees the lint output and continues working to fix the issues
- If clean (after auto-fix): returns `{"decision": "stop"}` — Claude returns to the user
- Loop prevention: if `stop_hook_active` is true in the input (meaning Claude is already retrying after a previous block), the hook allows the stop to prevent infinite loops
- Gracefully skips tools that aren't installed in the project

**Benefits over PostToolUse hooks**:
- Runs once per turn instead of after every edit — no noise from intermediate states
- Auto-fixes trivial issues so Claude only blocks on real errors
- Runs ruff and mypy, not just ruff, each under its target's own configuration
- User always sees a clean codebase when Claude returns
- Claude learns from the feedback and avoids repeating the same mistakes

## Migration from Manual Hooks

**Not in a repository that sets `core.hooksPath`**: there is nothing in
`.git/hooks/` to migrate, and migrating *out* of `.meta/hooks/` would be
dismantling the hook architecture rather than adopting a framework.

If the project has an existing manual `.git/hooks/pre-commit` script:

### Step 1: Backup Existing Hook

```bash
cp .git/hooks/pre-commit .git/hooks/pre-commit.backup
```

### Step 2: Analyze Existing Hook

Read the existing hook to understand what checks it runs:
- Linting (ruff, flake8, pylint)?
- Type checking (mypy, pyright)?
- Formatting (black, isort)?
- Custom checks?

### Step 3: Map to Pre-commit Config

For each check in the manual hook, add equivalent to `.pre-commit-config.yaml`:

| Manual Hook Check | Pre-commit Equivalent |
|-------------------|----------------------|
| `ruff check` | `ruff-pre-commit` repo |
| `black` | `ruff-format` (ruff replaces black) |
| `isort` | `ruff` with isort rules (I) |
| `flake8` | `ruff` (replaces flake8) |
| `mypy` | `mirrors-mypy` repo |
| `basedpyright` | local hook |
| Custom script | local hook with `entry: ./script.sh` |

### Step 4: Install Pre-commit and Remove Manual Hook

```bash
pre-commit install  # This overwrites .git/hooks/pre-commit
pre-commit run --all-files  # Verify all checks pass
```

### Step 5: Verify and Clean Up

```bash
# Test that hooks work
git add .
git commit -m "test" --dry-run

# If successful, remove backup
rm .git/hooks/pre-commit.backup
```

## Hook Behavior

**Auto-fixable issues** (handled by both pre-commit and the Stop hook lint gate):
- Import sorting
- Trailing whitespace
- Simple style violations
- Many code quality issues

**Blocking issues** (require Claude or manual intervention):
- Type errors (mypy/basedpyright)
- Syntax errors
- Complex linting violations that can't be auto-fixed

**Bypass (use sparingly)**:
```bash
git commit --no-verify
```

## Performance Optimization

**For large codebases**:
- Pre-commit runs on staged files only by default
- Use mypy incremental mode (cache in `.mypy_cache`)
- Consider running mypy/basedpyright in CI only for speed

**For monorepos**:
- Use `files:` pattern in hook config to limit scope
- Configure separate hooks per package

```yaml
- id: mypy
  files: ^src/mypackage/
```

## Troubleshooting

**Hook not running**: first check `git config core.hooksPath`. If it is set,
pre-commit never installed and never will; see Target contexts above. Do not run
the `git config --unset-all core.hooksPath` that pre-commit suggests.

```bash
pre-commit install   # reinstall. `--force` is not a flag pre-commit has
```

**Tools not found**:
```bash
# In a Project workspace: the dev group carries them
uv sync

# For .meta/, which has no manifest: reach them through uvx
uvx ruff@0.14.0 --version
```

**Hook too slow**:
- Profile: `pre-commit run --verbose`
- Consider removing mypy/basedpyright from pre-commit, run in CI instead
- Use `stages: [manual]` for slow hooks, run explicitly

**Update hook versions**:
```bash
pre-commit autoupdate
```

## Migration from PostToolUse Hooks

If the project was previously set up with `PostToolUse` hooks for ruff (the older approach), migrate to the Stop hook lint gate:

### Step 1: Check for Existing PostToolUse Hooks

```bash
grep -A 10 '"PostToolUse"' ~/.claude/settings.json
```

### Step 2: Remove PostToolUse Ruff Hooks

Edit `~/.claude/settings.json` and remove any `PostToolUse` entries that match `Edit|Write|MultiEdit` and run `ruff check`. Keep any non-ruff PostToolUse hooks.

### Step 3: Install Stop Hook

Follow Step 5 in the Setup Workflow above to install `lint-gate.py` and configure the Stop hook.

### Step 4: Verify

Make a Python edit that introduces a ruff error. Confirm that:
- No feedback appears after the edit itself (PostToolUse hook removed)
- When Claude finishes responding, the Stop hook fires and blocks with the error
- Claude fixes the error and returns clean output

## Lint Learning

Claude should learn from lint gate feedback to avoid repeating the same mistakes.

**After being blocked by the lint gate**: note the error pattern. If the same linter rule triggers repeatedly across edits, record it in auto-memory under the `lint-patterns` topic. Format:

```
- **[rule-code]** (tool): What triggers it and how to avoid it.
```

**Before editing Python files**: consult auto-memory for known lint pitfalls in this project. Apply those lessons proactively so the lint gate passes on the first try.

This creates a cross-session feedback loop: each lint gate block teaches Claude to write cleaner code next time.

## Verification Checklist

**In a repository that sets `core.hooksPath` (solorepo does)**

- [ ] `git config core.hooksPath` still reports `.meta/hooks`, and was never unset
- [ ] No `.pre-commit-config.yaml` was added, and `pre-commit install` was not run
- [ ] `.meta/hooks/` gained no file: nothing installed a hook into a tracked directory every portfolio inherits
- [ ] `~/.claude/hooks/lint-gate.py` points at this package's copy, installed and executable
- [ ] Claude Code Stop hook configured in `~/.claude/settings.json`
- [ ] Any old PostToolUse ruff hooks removed from settings
- [ ] `just gate meta` and `uv run gate` in each Project are green — the enforcement point

**Elsewhere**

- [ ] `.pre-commit-config.yaml` exists with ruff and mypy hooks
- [ ] `pre-commit install` has been run
- [ ] `pre-commit run --all-files` passes
- [ ] Any existing manual hooks have been migrated
- [ ] Bypass with `--no-verify` works for emergencies (git pre-commit only)

## Examples

**Example: New project setup**
```
1. Create venv: uv venv && source .venv/bin/activate
2. Install tools: uv pip install pre-commit ruff mypy basedpyright
3. Create .pre-commit-config.yaml with ruff, mypy, basedpyright
4. Install hooks: pre-commit install
5. Test: pre-commit run --all-files
6. Install lint-gate.py and configure Stop hook in settings.json
```

**Example: Migrate from PostToolUse to Stop hook**
```
1. Remove PostToolUse ruff hooks from ~/.claude/settings.json
2. Symlink lint-gate.py to ~/.claude/hooks/
3. Add Stop hook to ~/.claude/settings.json
4. Verify: make an edit with a ruff error, confirm block-on-stop behavior
```

**Example: Migrate existing manual hook**
```
1. Backup: cp .git/hooks/pre-commit .git/hooks/pre-commit.backup
2. Read backup to identify checks (ruff, mypy, custom scripts)
3. Create .pre-commit-config.yaml mapping each check
4. Install: pre-commit install (overwrites manual hook)
5. Verify: pre-commit run --all-files
6. Clean up: rm .git/hooks/pre-commit.backup
```

**Example: Add to existing pre-commit config**
```
1. Edit .pre-commit-config.yaml
2. Add basedpyright local hook
3. Run: pre-commit run --all-files
4. Commit updated config
```

## Related Skills

- **Prerequisites**: py-quality-setup (tools must be configured before adding hooks)
- **Complements**: py-security (add bandit to pre-commit for security scanning)
- **See also**: All skills benefit from automated enforcement via hooks
