---
name: py-quality-setup
description: Configure ruff and mypy for Python 3.13 targets, and hold the target-context contract the other py-* skills defer to. Use when setting up linters or type checkers, and when any py-* skill needs to know whether it is standing in inherited `.meta/` tooling or in a Project workspace.
status: stable
---

# Python Quality Tooling Setup

Configure comprehensive linting and type checking for Python 3.13 projects following Engineering Charter standards.

## Target contexts

A stereorepo portfolio holds two kinds of Python target. They carry different
configuration, run through different interpreters, and are held by different
gates. Settle which one you are standing in before running anything: the setup
this skill performs is right in one of them and damaging in the other.

This section, and the short form the other seven `py-*` skills carry, is
stereorepo's own (stereorepo's DR-212). Upstream has no equivalent, because upstream
has one target.

| | Repository tooling | A Project workspace |
|---|---|---|
| Where | `.meta/`, and nowhere else | wherever the Project was instantiated |
| Ruff | `.meta/ruff.toml` (stereorepo's DR-177) | the Project's own `pyproject.toml` (stereorepo's DR-096) |
| Mypy | `.meta/mypy.ini`, ratcheted against `.meta/checks/types.baseline.yaml` (stereorepo's DR-210) | the Project's own `pyproject.toml` |
| Run through | `python3` and `uvx` | `uv run`, from the Project's directory |
| Dependencies | none: no manifest, so no `[dependency-groups]` to add to | `[dependency-groups] dev` in the Project's manifest |
| Tests | none: no `pytest`, no `tests/` | `tests/` beside each package |
| Gate | `just gate meta` | `uv run gate`, from the Project's directory |

**Which one am I in.** Read `assertions/structure.yaml`. Every Project declares a
`gate:` — the command that must pass, typed at the root of the repository — and
the Project you are in is the one whose directory contains the path you are about
to change. The path alone settles nothing, because a Project is instantiated
wherever it was asked for: `just bootstrap python products/api` puts one at
`products/api`. Anything under `.meta/` is repository tooling, whatever else is
true of it.

### Three things this skill must not do

**Never write a `pyproject.toml` at the repository root.** A portfolio root has
no manifest and wants none. `.meta/` is configured by `.meta/ruff.toml` and
`.meta/mypy.ini`, which are inherited rather than generated; a Project is
configured by its own manifest, which arrives with the seed. A root manifest is a
third configuration that nothing declared, and every root-level `ruff check .`
would obey it.

**Never run a checker without naming the target's configuration.** `mypy` reads
its configuration from the working directory rather than per file, so `mypy .` at
the root runs past `.meta/mypy.ini` and past stereorepo's DR-210's baseline without reporting
that it did. `ruff` resolves configuration per file and does find `.meta/ruff.toml`
by proximity — but an explicit `--config` naming a ruleset that selects `RUF`
without `F` makes `RUF100` read `# noqa: F401  # reason: registers check steps`
as an unused suppression and strip the comment, after which the next `--fix` run
with `F` enabled deletes the import. Two runs, neither wrong on its own, and a
gate step goes silent. Name the configuration every time:

```bash
# Repository tooling
uvx ruff@0.14.0 check --config .meta/ruff.toml .meta/
uvx mypy@2.3.1 --config-file .meta/mypy.ini --strict --ignore-missing-imports .meta/

# A Project workspace, from the Project's own directory
uv run ruff check .
uv run mypy .
```

**Never grant `Bash(git commit *)`.** The permissions block below is upstream's,
and that entry is wrong here: A19 says a commit that does not name its Actor is
unattributable, and `git commit` names none. Commits go through
`.meta/say/commit`, which appends the Actor Trailer. The same applies to `gh`'s
writing verbs, which `.claude/settings.json` already denies in favour of
`.meta/say/post` and `.meta/say/move`; do not add them back
in `.claude/settings.local.json`.

### Verifying, by target

```bash
just gate meta      # repository tooling: ruff, mypy, and the rest of .meta/'s gate
just gate           # every Project the assertions declare
cd <project> && uv run gate    # one Project workspace
```

`.meta/` has no `pytest` and no `tests/`. Its behavioural tests are the probes
under `.meta/checks/probes/` (stereorepo's DR-209), which run as steps of
`just gate meta`.


## Objectives

1. Configure ruff for linting and formatting
2. Configure mypy for strict type checking
3. Configure basedpyright for additional type analysis
4. Ensure all tools target Python 3.13 or later
5. Add tools to dev dependencies

## Required Tools

**In a Project workspace**, add to `[dependency-groups]` dev: `"ruff"`, `"mypy"`, `"pytest"`.

**In `.meta/`**, add nothing. There is no manifest to add to. Its checkers are
pinned in the Project's `gate:` string in `assertions/structure.yaml` and reached
through `uvx`, which is what keeps `.meta/` runnable in a portfolio that has not
adopted Python at all.

- **ruff**: Fast linter (Rust-based, replaces isort and flake8)
- **mypy**: Standard Python type checker
- **basedpyright**: upstream's third checker, and **not part of this standard**.
  Nothing in stereorepo runs it, `uv run gate` has no step for it, and the seed's
  dev group does not carry it. Leave it out rather than adding a checker whose
  findings no gate reads.

## Required Configuration Files

### pyproject.toml (Canonical Reference)

**Not in `.meta/`, and not at the repository root** — see Target contexts above.
This section describes a Project workspace, and only a Project workspace.

**In a stereorepo portfolio the canonical configuration is the seed's**
(`bootstraps/python/seed/pyproject.toml`), which arrives with the Project and
already selects the rule set stereorepo's DR-096 settled, pins the gate's tools exactly while
letting the test tools float (stereorepo's DR-097), and targets the support floor rather than
the development interpreter (stereorepo's DR-095). Under Ratchet it is raised and never
lowered, so this skill's job in an existing Project is to read that manifest and
verify it, not to overwrite it with the reference below. `ignore` stays empty:
A2 says a suppression names its rule and its reason at the site, never in
configuration, and `uv run gate lints` refuses an entry.

Two differences from the reference below are deliberate and not drift.
`ruff format` is absent, because mechanical formatting was retired from this
gate (stereorepo's DR-193): it inflates agent context windows and manufactures rebase churn
across concurrent branches for no semantic gain. `basedpyright` is absent for
the reason given under Required Tools.

The reference below is upstream's, and is what a Project outside a stereorepo
portfolio should hold. It must include these sections:

```toml
[project]
requires-python = ">=3.13"

[dependency-groups]
dev = [
    "pytest>=8.0",
    "pytest-cov>=4.0",
    "ruff>=0.8.0",
    "mypy>=1.0",
    "basedpyright>=1.0",
    "pre-commit>=3.0",
    # Analysis tools (add as needed for py-* skills):
    # "radon", "vulture", "pylint", "bandit", "lizard",
    # "mutmut", "wily", "xenon", "pyupgrade", "coverage",
]

[tool.ruff]
line-length = 100  # or 140 for larger projects
target-version = "py313"
src = ["src"]  # adjust to your source directory

[tool.ruff.lint]
select = [
    "E",   # pycodestyle errors
    "W",   # pycodestyle warnings
    "F",   # pyflakes
    "I",   # isort
    "N",   # pep8-naming
    "UP",  # pyupgrade
    "B",   # flake8-bugbear
    "C4",  # flake8-comprehensions
    "SIM", # flake8-simplify
]
ignore = []

[tool.mypy]
python_version = "3.13"
strict = true
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_no_return = true
check_untyped_defs = true

# Add overrides for third-party packages without stubs
# [[tool.mypy.overrides]]
# module = "package_name"
# ignore_missing_imports = true

[tool.basedpyright]
pythonVersion = "3.13"
typeCheckingMode = "standard"  # or "recommended" for stricter
reportMissingTypeStubs = false
reportUnknownMemberType = false
reportUnknownArgumentType = false
reportUnknownVariableType = false
```

### pyrightconfig.json (optional, for multi-package projects)

A.When using `pyrightconfig.json` for multi-package projects, REMOVE the `tool.basedpyright` section from pyproject.toml

```json
{
  "include": ["src"],
  "exclude": ["**/node_modules", "**/__pycache__", "**/.*", "venv", ".venv"],
  "pythonVersion": "3.13",
  "typeCheckingMode": "recommended",
  "reportMissingImports": "error",
  "reportMissingTypeStubs": false,
  "reportUnknownMemberType": false,
  "reportUnknownVariableType": false,
  "reportUnknownArgumentType": false,
  "reportMissingParameterType": true,
  "reportUnusedVariable": true,
  "reportImplicitStringConcatenation": true,
  "reportUnnecessaryTypeIgnoreComment": true
}
```

## Setup Workflow

1. **Check existing configuration**
   - Read pyproject.toml
   - Check if dev dependencies exist
   - Verify Python version requirement

2. **Update or create configuration** — in a Project workspace only. In `.meta/`
   there is nothing to create: `.meta/ruff.toml` and `.meta/mypy.ini` are
   inherited, and a `pyproject.toml` written anywhere near them is the failure
   this skill's Target contexts section names.
   - Add dev dependencies if missing
   - Add/update [tool.ruff] section
   - Add/update [tool.mypy] section

3. **Install tools in venv**
   ```bash
   # Using uv (recommended):
   uv sync                      # Creates venv and installs dev group automatically

   # Or manually:
   uv venv
   source .venv/bin/activate
   uv sync --group dev

   # Fallback if uv not available:
   # python -m venv venv
   # source venv/bin/activate
   # pip install -e ".[dev]"
   ```

4. **Verify installation**
   ```bash
   which ruff mypy basedpyright
   ruff --version
   mypy --version
   basedpyright --version
   ```

5. **Run initial checks**, naming the target's configuration. A bare `ruff
   check .` or `mypy .` at the repository root sweeps both targets under one
   configuration, which is right for neither.
   ```bash
   # Repository tooling
   uvx ruff@0.14.0 check --config .meta/ruff.toml .meta/
   uvx mypy@2.3.1 --config-file .meta/mypy.ini --strict --ignore-missing-imports .meta/

   # A Project workspace, from the Project's own directory
   uv run ruff check .
   uv run mypy .
   ```

6. **Configure Claude Code permissions**

   Write `.claude/settings.local.json` so all py-* skills can run without permission prompts. If the file already exists, merge new entries into the existing `allow` list without removing user entries.

   ```json
   {
     "permissions": {
       "allow": [
         "Bash(ruff *)",
         "Bash(mypy *)",
         "Bash(basedpyright *)",
         "Bash(pytest *)",
         "Bash(vulture *)",
         "Bash(pylint *)",
         "Bash(radon *)",
         "Bash(lizard *)",
         "Bash(wily *)",
         "Bash(bandit *)",
         "Bash(mutmut *)",
         "Bash(pyupgrade *)",
         "Bash(scc *)",
         "Bash(pre-commit *)",
         "Bash(uv *)",
         "Bash(pip *)",
         "Bash(python3 *)",
         "Bash(python *)",
         "Bash(source *)",
         "Bash(which *)",
         "Bash(mkdir *)",
         "Bash(chmod *)",
         "Bash(ls *)",
         "Bash(ln *)",
         "Bash(git add *)",
         "Bash(git diff *)",
         "Bash(git status *)",
         "Bash(git log *)",
         "Bash(git ls-files *)",
         "Bash(git checkout *)",
         "Bash(git branch *)",
         "Bash(.meta/say/commit *)"
       ],
       "deny": []
     }
   }
   ```

   `Bash(git commit *)` is upstream's entry and is **not** in the list above. A19
   says a commit that does not name its Actor is unattributable, and `git commit`
   names none; `.meta/say/commit` appends the Actor Trailer. Do not add `gh`'s
   writing verbs either: `.claude/settings.json` denies them so that
   everything reaching GitHub passes through `.meta/say/post` and `.meta/say/move`
   and is signed, and a `local` file that allowed them back
   would be reopening a boundary rather than granting a convenience.

   **Merge logic**: Read existing file, parse JSON, take union of `allow` lists, write back. Create `.claude/` directory if needed.

7. **Install Stop hook lint gate**

   Symlink the lint gate script so Claude Code runs ruff and mypy on modified
   files before returning to the user. If either reports errors, Claude is
   blocked from stopping and must fix them first.

   The copy in this package routes by target: a file under `.meta/` is checked
   against `.meta/ruff.toml` and `.meta/mypy.ini`, a file in a Project workspace
   through that Project's `uv run`. It runs no formatter, because stereorepo's DR-193 retired
   mechanical formatting from this standard, and it does not invoke
   `basedpyright`. Point the symlink at this package's `lint-gate.py` rather than
   an upstream copy, which does all three of those things.

   ```bash
   mkdir -p ~/.claude/hooks
   ln -sf ~/.claude/skills/py-git-hooks/lint-gate.py ~/.claude/hooks/lint-gate.py
   ```

   Configure the Stop hook in `~/.claude/settings.json` (merge into existing hooks if present):

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

8. **Configure git hooks** (if requested)
   - See py-git-hooks skill, and read its Target contexts section first: in a
     repository that sets `core.hooksPath`, `pre-commit install` refuses, and the
     remedy it prints is destructive here.

## Tool-Specific Notes

### Ruff
- Fastest Python linter (Rust-based)
- Replaces: black, isort, flake8, and many plugins
- Auto-fix: `ruff check --fix .`
- Format: `ruff format .`

### Mypy
- Standard Python type checker
- Strict mode catches most type errors
- Use `# type: ignore[error-code]` sparingly
- Add overrides for packages without stubs

### Basedpyright
- Fork of Pyright with more features
- Catches some errors mypy misses
- More configurable than Pyright
- Works well alongside mypy

## Common Adjustments

**Monorepo/multi-package**:
- Use pyrightconfig.json with extraPaths
- Set namespace_packages = true in mypy

**Legacy codebase**:
- Start with less strict mypy (strict = false)
- Gradually enable strict checks
- Use mypy overrides per module

**Third-party packages without stubs**:
```toml
[[tool.mypy.overrides]]
module = "package_name"
ignore_missing_imports = true
```

## Verification Checklist

**Both targets**

- [ ] The target was identified from `assertions/structure.yaml` before anything ran
- [ ] No `pyproject.toml` was created at the repository root
- [ ] `.claude/settings.local.json` grants the quality tools and **not** `Bash(git commit *)` or any `gh` writing verb
- [ ] `~/.claude/hooks/lint-gate.py` points at this package's copy, and the Stop hook is configured in `~/.claude/settings.json`

**Repository tooling (`.meta/`)**

- [ ] `.meta/ruff.toml` is unchanged, and its `ignore` is still `[]`
- [ ] `uvx ruff@0.14.0 check --config .meta/ruff.toml .meta/` passes
- [ ] Every `# noqa` under `.meta/` still carries its `# reason:`
- [ ] `just gate meta` is green

**A Project workspace**

- [ ] pyproject.toml has requires-python = ">=3.13"
- [ ] dev dependencies include ruff and mypy, pinned exactly (stereorepo's DR-097)
- [ ] [tool.ruff] configured with target-version = "py313", and `ignore = []`
- [ ] [tool.mypy] configured with python_version = "3.13" and strict = true
- [ ] `uv run ruff check .` and `uv run mypy .` pass from the Project's directory
- [ ] `uv run gate` is green

## Examples

**Example: New project setup**
```
1. Create venv: uv venv && source .venv/bin/activate
2. Create pyproject.toml with [project], [tool.ruff], [tool.mypy], [tool.basedpyright]
3. Install: uv pip install -e ".[dev]"
4. Verify: ruff --version && mypy --version && basedpyright --version
5. Run initial checks: ruff check . && mypy . && basedpyright .
6. Fix issues or add ignores for false positives
```

**Example: Add quality tools to existing project**
```
1. Activate venv: source .venv/bin/activate
2. Update pyproject.toml:
   - Add ruff, mypy, basedpyright to [project.optional-dependencies] dev
   - Add [tool.ruff], [tool.mypy], [tool.basedpyright] sections
3. Install: uv pip install -e ".[dev]"
4. Run checks: ruff check . (expect many errors initially)
5. Auto-fix: ruff check --fix . && ruff format .
6. Run type checkers: mypy . && basedpyright .
7. Add [[tool.mypy.overrides]] for third-party packages without stubs
8. Iterate until all checks pass
```

**Example: Legacy codebase gradual adoption**
```
1. Start with minimal ruff rules: select = ["E", "F"]
2. Start mypy non-strict: strict = false
3. Fix errors incrementally, expand rules over time
4. Add per-module mypy overrides for problematic modules
5. Eventually enable strict mode project-wide
```

## Related Skills

- **Foundation**: This skill is the foundation for all other skills, and holds
  the Target contexts contract in full. The other `py-*` skills carry the short
  form and their own hazard; when one of them is ambiguous about which target it
  is addressing, this section settles it.
- **Next steps**: py-git-hooks (automate enforcement of configured tools)
- **See also**: py-modernize (for uv migration and syntax upgrades)
