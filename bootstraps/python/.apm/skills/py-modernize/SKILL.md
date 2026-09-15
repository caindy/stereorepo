---
name: py-modernize
description: Modernize Python codebases - migrate pip to uv, upgrade syntax to Python 3.13+, replace deprecated patterns, and update tooling to current best practices.
status: stable
---

# Python Codebase Modernization

Upgrade Python projects to use modern tooling, syntax, and patterns following Engineering Charter principles.

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

### `.meta/` is already modern, and is not migrated to uv

The migration this skill performs — consolidate to `pyproject.toml`, adopt `uv`,
set `requires-python` — is a Project workspace's migration. `.meta/` is not
behind on it; it is deliberately outside it.

- **Never consolidate `.meta/` into a `pyproject.toml`**, at the repository root
  or anywhere else. Its ruff configuration is `.meta/ruff.toml` and its mypy
  configuration is `.meta/mypy.ini` (solorepo's DR-177, solorepo's DR-210), both
  inherited by every portfolio rather than generated into one. A root manifest is
  the failure py-quality-setup's contract names first.
- **Never migrate `.meta/` to `uv run`.** Its programs are run by `python3` and
  reach their tools through `uvx`, and that is what keeps them runnable in a
  portfolio that has adopted no language bootstrap at all. A `uv` workspace at the
  root would make the repository's own tooling depend on a Project.
- **Syntax modernization applies, with the configuration named.** `UP` is in
  `.meta/ruff.toml`'s rule set and `target-version` is already `py313`, so the
  upgrade this skill performs is run as
  `uvx ruff@0.14.0 check --config .meta/ruff.toml --select UP --fix .meta/`.
  Never `pyupgrade --py313-plus` over `.meta/`. It reads no `noqa` at all — given
  `from typing import List  # noqa: UP035  # reason: ...` it rewrites the
  annotated line anyway — so the reasoned, site-local suppression that A2 makes
  the only permitted kind does not stop it. It is also not the checker the gate
  reads: `meta ruff` runs a pinned ruff, and a second rewriter working to its own
  idea of the rule set is how the two drift apart.
- **Verify with `just gate meta`**, not `pytest`.

In a Project workspace this skill applies as written, with one subtraction: the
seed already targets `py313` deliberately as the support floor rather than the
development interpreter (solorepo's DR-095), so do not raise `requires-python` to
match `.python-version`.

## Objectives

1. Migrate from pip to uv for faster dependency management
2. Upgrade Python syntax to 3.13+ modern patterns
3. Replace deprecated APIs and patterns
4. Update tooling to current best practices
5. Ensure pyproject.toml is the single source of configuration

## Required Tools

**Install uv globally** (via package manager): `sudo zypper install uv` or `pip install --user uv`
**Add to `[dependency-groups]` dev**: `"pyupgrade"`, `"ruff"`

- **uv**: Fast package installer (pip replacement)
- **pyupgrade**: Auto-upgrade syntax to newer Python
- **ruff**: Modern linter with UP rules

**Permissions**: Run py-quality-setup first to configure `.claude/settings.local.json` with all needed tool permissions.

## Package Manager: pip → uv

### Why uv?

- **10-100x faster** than pip
- Better dependency resolution
- Improved caching
- Compatible with pip (drop-in replacement)
- Actively developed by Astral (same team as ruff)

### Migration Workflow

```bash
# 1. Verify current setup
cat requirements.txt setup.py setup.cfg pyproject.toml

# 2. Install uv globally (not recommended, ask user to install via package manager)
# curl -LsSf https://astral.sh/uv/install.sh | sh

# 3. Replace venv creation
# OLD: python -m venv venv
uv venv

# 4. Replace pip install
# OLD: pip install -e ".[dev]"
uv pip install -e ".[dev]"

# 5. Replace pip install from requirements.txt
# OLD: pip install -r requirements.txt
uv pip install -r requirements.txt

# 6. Compile requirements (faster dependency resolution)
uv pip compile pyproject.toml -o requirements.txt

# 7. Sync environment (install exactly what's in requirements.txt)
uv pip sync requirements.txt
```

### Update CI/CD

```yaml
# .github/workflows/test.yml

# BEFORE
- name: Install dependencies
  run: |
    python -m venv venv
    source venv/bin/activate
    pip install -e ".[dev]"

# AFTER
- name: Install uv
  uses: astral-sh/setup-uv@v1

- name: Install dependencies
  run: |
    uv venv
    source .venv/bin/activate
    uv pip install -e ".[dev]"
```

### Update Documentation

Update README.md:

```markdown
<!-- BEFORE -->
## Development Setup

python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"

<!-- AFTER -->
## Development Setup

# Install uv if not already installed (via package manager preferred)
# sudo zypper install uv  # openSUSE
# or: pip install --user uv

uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
```

## Python Syntax Modernization

### Target Version

Set target in pyproject.toml:

```toml
[project]
requires-python = ">=3.13"

[tool.pyupgrade]
target-version = "py313"

[tool.ruff]
target-version = "py313"

[tool.ruff.lint]
select = ["UP"]  # Enable pyupgrade rules
```

### Run Syntax Upgrades

```bash
# Using pyupgrade directly (modifies files in-place)
pyupgrade --py313-plus **/*.py

# Using ruff (shows what would change)
ruff check . --select UP
ruff check . --select UP --fix  # Apply fixes

# Verify changes
git diff

# Run tests to ensure functionality preserved
pytest
```

### Common Modernizations

Run `pyupgrade --py313-plus .` or `ruff check . --select UP` to auto-upgrade:

- **Type hints**: `List[str]` → `list[str]`, `Optional[int]` → `int | None`
- **Remove `__future__`**: imports (built-in 3.11+)
- **String formatting**: `%` or `.format()` → f-strings
- **Type unions**: `Union[int, str]` → `int | str`
- **Walrus operator**: `if x := func():` (reduce temp variables)
- **Match statements**: Replace long if/elif chains (3.10+)
- **Pathlib**: Replace `os.path` with `Path` objects
- **Dataclasses**: Replace manual `__init__` with `@dataclass`


## Configuration Modernization

Consolidate setup.py/setup.cfg/requirements.txt → pyproject.toml.

**Not `.meta/`**, which is configured by `.meta/ruff.toml` and `.meta/mypy.ini`
and consolidates into no manifest.

**Note**: For the complete pyproject.toml configuration, and for which of these
tools this standard actually holds, see **py-quality-setup**.

Basic structure:

```toml
[project]
name = "myproject"
version = "1.0.0"
requires-python = ">=3.13"
dependencies = ["requests", "pydantic"]

[build-system]
requires = ["setuptools>=68.0"]
build-backend = "setuptools.build_meta"
```

After: `rm setup.py setup.cfg; uv pip install -e .; pytest`

## Deprecated Pattern Updates

Common deprecations to fix:

- `collections.Iterable` → `collections.abc.Iterable` (deprecated 3.3, removed 3.10)
- `datetime.utcnow()` → `datetime.now(UTC)` (deprecated 3.12)
- `datetime.utcfromtimestamp()` → `datetime.fromtimestamp(ts, UTC)` (deprecated 3.12)
- `imp` module → `importlib` (removed 3.12)
- `typing.List`, `typing.Dict` → `list`, `dict` (3.9+)
- `typing.Optional[X]` → `X | None` (3.10+)
- `typing.Union[X, Y]` → `X | Y` (3.10+)

Search for deprecated patterns:
```bash
# Find deprecated datetime usage
grep -rn "datetime.utcnow\|datetime.utcfromtimestamp" --include="*.py" .

# Find old typing imports
grep -rn "from typing import.*List\|from typing import.*Dict\|from typing import.*Optional" --include="*.py" .

# Find old collections imports
grep -rn "from collections import.*Callable\|from collections import.*Iterable" --include="*.py" .
```

## Verification Checklist

**Repository tooling (`.meta/`)**

- [ ] No `pyproject.toml` was created, at the root or under `.meta/`
- [ ] `pyupgrade` was not run over `.meta/`
- [ ] `uvx ruff@0.14.0 check --config .meta/ruff.toml --select UP .meta/` reports no issues
- [ ] No deprecated `datetime.utcnow()` or `datetime.utcfromtimestamp()` usage
- [ ] No old-style typing imports (`List`, `Dict`, `Optional`, `Union`)
- [ ] `just gate meta` is green

**A Project workspace**

- [ ] `uv` is used for venv creation and package installation
- [ ] `pyproject.toml` is the single configuration source (no setup.py/setup.cfg)
- [ ] `requires-python` still states the support floor, not the development interpreter (solorepo's DR-095)
- [ ] `uv run ruff check . --select UP` reports no issues (or only accepted exceptions)
- [ ] No deprecated `datetime.utcnow()` or `datetime.utcfromtimestamp()` usage
- [ ] No old-style typing imports (`List`, `Dict`, `Optional`, `Union`)
- [ ] `uv run gate` is green from the Project's directory

## Examples

**Example: Migrate pip to uv**
```
1. Check current setup:
   - ls -la | grep -E "setup.py|requirements.txt|pyproject.toml"
   - cat pyproject.toml

2. Install uv (if not already installed):
   - Via package manager: sudo zypper install uv  # openSUSE
   - Or as user package: pip install --user uv

3. Test uv with current project:
   - uv venv
   - source .venv/bin/activate
   - uv pip install -e ".[dev]"
   - pytest (verify all tests pass)

4. Update CI/CD:
   - Edit .github/workflows/test.yml
   - Replace pip commands with uv

5. Update README:
   - Replace pip instructions with uv

6. Commit: "Migrate from pip to uv for dependency management"
```

**Example: Modernize syntax to Python 3.13**
```
1. Update pyproject.toml:
   [project]
   requires-python = ">=3.13"

2. Run pyupgrade:
   pyupgrade --py313-plus **/*.py

3. Review changes:
   git diff
   # Check: List[X] → list[X], Union[X, Y] → X | Y, etc.

4. Run ruff for additional upgrades:
   ruff check . --select UP --fix

5. Verify type checking still works:
   mypy .
   basedpyright .

6. Run tests:
   pytest

7. Commit: "Modernize syntax to Python 3.13+"
```

**Example: Complete modernization**
```
1. Migrate to uv (see Example 1)

2. Consolidate configuration:
   - Read setup.py and setup.cfg
   - Migrate all config to pyproject.toml
   - Remove setup.py and setup.cfg
   - Verify: uv pip install -e ".[dev]"

3. Modernize syntax (see Example 2)

4. Update deprecated APIs:
   - grep -r "from collections import.*Iterable" .
   - Replace with collections.abc
   - grep -r "datetime.utcnow" .
   - Replace with datetime.now(UTC)

5. Final validation:
   - ruff check . --select UP (clean)
   - pytest (all pass)
   - mypy . && basedpyright . (no errors)

6. Update documentation:
   - README reflects uv usage
   - CONTRIBUTING.md updated

7. Commit: "Modernize codebase: uv, Python 3.13 syntax, pyproject.toml"
```

## Related Skills

- **Prerequisites**: py-quality-setup (tool configuration), py-test-quality (safety net before syntax changes)
- **Enforcement**: py-git-hooks (enforce modern syntax via ruff UP rules)
- **See also**: py-complexity (modernization often enables simplification)
