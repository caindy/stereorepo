# Success Metrics & Tool Reference

Quality targets and tool guidance for Python refactoring.

**Read py-refactor's Target contexts section first.** Every command in this file
is written for a Project workspace and typed from that Project's own directory.
Run none of them from the repository root, where they would sweep `.meta/` under
a configuration that is not its own, and run none of them against `.meta/`
without the substitutions in the second table below.

## Success Metrics by Dimension

| Dimension | Target | Tool | Command |
|-----------|--------|------|---------|
| **Security** | Zero high/medium vulnerabilities | bandit, ruff | `uv run ruff check . --select S` |
| **Testing** | Every mutant killed | pytest, mutmut | `uv run gate test && uv run gate mutants` |
| **Complexity** | No functions ≥C (11+) | radon, ruff `C90` | `uv run gate ruff` |
| **Maintainability** | Index ≥65 all modules | radon | `uvx radon mi . -n B` |
| **Code Health** | No dead code, no duplicates >6 lines | vulture, pylint | `uvx vulture . --min-confidence 80` |
| **Modernization** | Python 3.13+ syntax, uv tooling | ruff `UP` | `uv run ruff check . --select UP` |
| **Automation** | The gate passes | gate | `uv run gate` |

The mutation target is not a score. `uv run gate mutants` requires every mutant
killed, with no threshold and no survivor budget; the ≥75% figure elsewhere in
these skills is upstream's.

### The same dimensions in `.meta/`

| Dimension | What holds it | Command |
|-----------|---------------|---------|
| **Security** | nothing: `S` is not in `.meta/ruff.toml`'s ruleset | `uvx ruff@0.14.0 check --config .meta/ruff.toml --select S .meta/` — advisory |
| **Testing** | the probes under `.meta/checks/probes/` | `just gate meta` |
| **Complexity** | nothing: `C90` is not in the ruleset | `uvx radon cc .meta/ -n C` — advisory |
| **Code Health** | `F` in the ruleset, and `# noqa: F401  # reason:` on the registration imports | `just gate meta` |
| **Modernization** | `UP` in the ruleset | `uvx ruff@0.14.0 check --config .meta/ruff.toml --select UP .meta/` |
| **Types** | `mypy --strict`, ratcheted two-sided against `.meta/checks/types.baseline.yaml` | `just gate meta` |
| **Automation** | the gate | `just gate meta` |

`.meta/` has no coverage figure and no mutation score, because it has no pytest
suite. Reporting one is reporting on a suite that does not exist.

## Tool Reference

### Complexity Analysis

| Tool | Purpose | When to Use |
|------|---------|-------------|
| **radon** | Cyclomatic complexity, maintainability index | Primary complexity measurement |
| **lizard** | Cognitive complexity | Readability-focused analysis |
| **xenon** | CI/CD threshold enforcement | Automated quality gates |
| **wily** | Complexity trends over git history | Track improvement over time |

### Code Quality

| Tool | Purpose | When to Use |
|------|---------|-------------|
| **vulture** | Dead/unused code detection (AST-based) | Remove unused code |
| **pylint** | Duplicate code detection | Find copy-paste code |
| **ruff** | Fast linter/formatter | Primary linting |

### Security

| Tool | Purpose | When to Use |
|------|---------|-------------|
| **bandit** | AST-based vulnerability scanner | Comprehensive security audit |
| **ruff --select S** | Built-in Bandit rules | Quick security check |

### Testing

| Tool | Purpose | When to Use |
|------|---------|-------------|
| **pytest-cov** | Code coverage measurement | Identify untested code |
| **mutmut** | Mutation testing | Verify test effectiveness |

### Type Checking

| Tool | Purpose | When to Use |
|------|---------|-------------|
| **mypy** | Standard type checker | General type checking |
| **ruff** | Fast linting with auto-fix | Code style enforcement |

`basedpyright` is upstream's third checker and is not part of this standard.
Nothing here runs it, and no gate step reads its findings.

## Engineering Charter Alignment

These skills implement Engineering Charter principles:

| Charter Principle | Skill Implementation |
|-------------------|---------------------|
| Maintainable, idiomatic code | py-complexity, py-code-health |
| Self-documenting code | py-complexity (reduce need for comments) |
| Update callers, no shims | py-modernize (direct upgrades) |
| Consolidate similar code | py-code-health (deduplication) |
| Never commit secrets | py-security, py-git-hooks |
| Run linters incrementally | py-quality-setup, py-git-hooks |
| Code must pass ruff and mypy | py-quality-setup |
| Enforcement at the gate, not at a committed hook | py-git-hooks |

## Validation Commands

The gate is the validation suite, and it is the thing a merge is held to:

```bash
just gate meta                 # repository tooling
cd <project> && uv run gate    # a Project workspace
just gate                      # every Project the assertions declare
```

`ruff format --check` is absent on purpose: mechanical formatting was retired
from this standard (solorepo's DR-193).

The advisory scanners, which no gate step reads, run per target:

```bash
# A Project workspace, from the Project's own directory
uv run ruff check . --select S
uvx radon cc . -n C
uvx vulture --min-confidence 80 .

# Repository tooling
uvx ruff@0.14.0 check --config .meta/ruff.toml --select S .meta/
uvx radon cc .meta/ -n C
uvx vulture --min-confidence 80 .meta/

# Track improvement
wily diff HEAD~1
wily report .
```
