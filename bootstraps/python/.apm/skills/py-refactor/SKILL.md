---
name: py-refactor
description: Orchestrate comprehensive Python refactoring - coordinates security, complexity, testing, code health, and modernization skills to systematically improve code quality.
status: stable
---

# Python Refactoring Orchestrator

Comprehensive refactoring workflow coordinating specialized skills to improve Python code quality.

## Target contexts

A stereorepo portfolio holds two kinds of Python target, and this skill behaves
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

### Settle the target before Phase 1, and route every phase through it

This skill invokes the others, so it carries their hazards at once. Identify the
target first; each skill it dispatches to states its own prohibition, and
**py-quality-setup** holds the contract in full.

| Phase | In `.meta/` | In a Project workspace |
|---|---|---|
| Setup | nothing to set up: configuration is inherited, and no `pyproject.toml` is created | `uv sync`; the seed's manifest already carries the configuration |
| Analysis | `uvx` each tool, ruff with `--config .meta/ruff.toml` | `uv run`, from the Project's directory |
| Test quality | probes under `.meta/checks/probes/`; no `pytest`, no `mutmut`, no coverage figure | `uv run gate test` and `uv run gate mutants` |
| Code health | never delete a `# noqa: F401  # reason: ...` import or an `@check` function | the ordinary rules |
| Modernization | ruff `UP` under the pinned config; never `pyupgrade` | as written |
| Automation | never `pre-commit install`: `core.hooksPath` is set | as written |
| Validation | `just gate meta` | `uv run gate` |

Phase 2 writes scanner output to `reports/`. Write it outside the repository
instead — the scratch directory the harness gives the session. `reports/` is in
no `.gitignore` here, so it lands in `git status` and goes into the commit behind
the next `git add -A`; a run that analyses the tree should not also add to it.

## Overview

This skill orchestrates multiple focused skills to perform systematic refactoring:

| Skill | Purpose | Status |
|-------|---------|--------|
| `py-security` | Vulnerability detection and remediation | stable |
| `py-code-health` | Dead code and duplication removal | stable |
| `py-complexity` | Reduce cyclomatic/cognitive complexity | stable |
| `py-test-quality` | Coverage analysis and mutation testing | stable |
| `py-modernize` | Upgrade tooling and syntax | stable |
| `py-quality-setup` | Configure linters and type checkers | stable |
| `py-git-hooks` | Set up pre-commit hooks | stable |

## Refactoring Priorities

Follow this impact-based prioritization:

1. **Critical**: Security vulnerabilities (use `py-security`)
2. **High**: Code duplication, untested code (<80% coverage)
3. **Medium**: Complexity reduction, dead code removal
4. **Low**: Syntax modernization, style improvements

## Standard Refactoring Workflow

### Phase 1: Setup (if needed)

```
0. Settle the target (see Target contexts above). In .meta/ steps 1 to 3 are
   skipped entirely: the configuration is inherited, there is no manifest to add
   to, and the analysis tools are reached through uvx.

1. If quality tools not configured (pyproject.toml):
   → Invoke: py-quality-setup
   (also configures .claude/settings.local.json permissions for all tools)

2. Add analysis tools to [dependency-groups] dev in the Project's pyproject.toml:
   "radon", "vulture", "pylint", "bandit", "lizard",
   "pytest-cov", "mutmut", "wily", "ruff", "mypy"

3. Install and activate:
   uv sync && source .venv/bin/activate
```

### Phase 2: Comprehensive Analysis

Run all automated scanners to get baseline:

```bash
mkdir -p reports

# Security
ruff check . --select S > reports/security.txt
bandit -r . -f json -o reports/security.json

# Code health
vulture . --min-confidence 80 > reports/dead_code.txt
pylint --disable=all --enable=duplicate-code --recursive=y . > reports/duplication.txt

# Complexity
radon cc . -n C -s > reports/complexity.txt
lizard -l python -w > reports/cognitive_complexity.txt
radon mi . -n B > reports/maintainability.txt

# Test quality
pytest --cov=. --cov-report=html --cov-report=term > reports/coverage.txt

# Initialize complexity tracking
wily build .
```

### Phase 3: Prioritized Remediation

**Step 1: Security (Critical)**
```
If security.txt shows issues:
→ Invoke: py-security
   - Fix SQL injection, hardcoded secrets, weak crypto
   - Verify: ruff check . --select S (clean)
   - Run tests to ensure no regressions
```

**Step 2: Test Quality (High - enables safe refactoring)**
```
If coverage < 80%:
→ Invoke: py-test-quality
   - Write tests for untested code
   - Run mutation testing to verify test quality
   - Target: ≥80% coverage, ≥75% mutation score
```

**Step 3: Code Health (High)**
```
If duplication.txt or dead_code.txt show issues:
→ Invoke: py-code-health
   - Remove dead code (vulture findings)
   - Consolidate duplicates (pylint findings)
   - Verify: Tests still pass, coverage maintained
```

**Step 4: Complexity Reduction (Medium)**
```
If complexity.txt shows C+ functions or maintainability < 65:
→ Invoke: py-complexity
   - Extract functions, simplify conditionals
   - Use guard clauses, lookup tables
   - Track improvement with wily
   - Verify: radon cc . -n C (clean)
```

**Step 5: Modernization (Optional)**
```
If project uses old patterns or pip:
→ Invoke: py-modernize
   - Migrate pip → uv
   - Upgrade syntax to Python 3.13+
   - Consolidate to pyproject.toml
   - Verify: Tests pass, type checking works
```

### Phase 4: Automation

```
Set up enforcement to prevent regressions:
→ Invoke: py-git-hooks, and read its Target contexts section first

   Where core.hooksPath is set — stereorepo sets it to .meta/hooks — there are no
   pre-commit hooks to install, and the enforcement point is the gate:
   `just gate meta`, and `uv run gate` in each Project. What does apply in both
   targets is the Stop hook lint gate, which routes ruff and mypy by target.
```

### Phase 5: Final Validation

The gate is the validation suite. A bare `ruff check .` or `mypy .` at the
repository root sweeps both targets under one configuration, which is right for
neither.

```bash
# Repository tooling
just gate meta

# A Project workspace, from the Project's own directory
uv run gate

# Everything the assertions declare
just gate
```

The scanners this skill adds on top of the gate — the ones no gate step reads —
run per target:

```bash
# Repository tooling
uvx ruff@0.14.0 check --config .meta/ruff.toml --select S .meta/
uvx radon cc .meta/ -n C
uvx vulture --min-confidence 80 .meta/

# A Project workspace, from the Project's own directory
uv run ruff check . --select S
uvx radon cc . -n C
uvx vulture --min-confidence 80 .

# Track overall improvement
wily diff HEAD~1
wily report .
```

## When NOT to Use This Skill

Don't use orchestrated refactoring when:

- **Single focused task**: Use specific skill directly (e.g., just py-security for CVE fix)
- **No tests exist**: Write tests first (py-test-quality), then refactor
- **Active development**: Coordinate with team to avoid merge conflicts
- **Production incident**: Fix incident first, refactor later

## Additional Resources

- **WORKFLOWS.md**: Quick workflows for specific scenarios (security sweep, complexity sprint, legacy modernization)
- **METRICS.md**: Success metrics, tool reference, Engineering Charter alignment
