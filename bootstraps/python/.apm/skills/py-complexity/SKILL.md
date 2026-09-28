---
name: py-complexity
description: Reduce cyclomatic and cognitive complexity in Python code. Break down complex functions, simplify control flow, and track complexity trends over time.
status: stable
---

# Python Complexity Reduction

Reduce code complexity to improve maintainability and understandability.

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

### What actually holds complexity in each target

The measurement tools below are advisory in both targets: `radon`, `lizard`,
`xenon` and `wily` are reached through `uvx`, no gate step reads any of them, and
no threshold they report blocks a merge here.

What does hold is ruff's `C90`:

- **A Project workspace** selects `C90` with `max-complexity = 12` in its
  `pyproject.toml` (stereorepo's DR-096), and `uv run gate ruff` enforces it.
- **`.meta/`** does not select `C90` in `.meta/ruff.toml`, so complexity there is
  unmeasured by the gate. Reducing it is still worth doing; claiming a gate holds
  it is not. Raising `.meta/`'s rule set is an edit to `.meta/ruff.toml` reviewed
  like any other, not something this skill does in passing.

Two prohibitions carry over from the other skills, because extraction touches
what they protect. **Never remove an import carrying
`# noqa: F401  # reason: ...`** while reorganizing a module, and **never rename
or remove an `@check`-decorated function** in `.meta/`: the registry calls it,
and nothing else does (see py-code-health). Verify with `just gate meta` and read
the step count, not only the colour.

Objective 6 below — enforce thresholds in CI — has no counterpart here. The gate
is the CI, and it holds what `.meta/ruff.toml` and the Project's manifest select.

Effective use of context windows.

## Objectives

1. Measure cyclomatic and cognitive complexity
2. Identify overly complex functions and modules
3. Identify overly long files (no code files >500 lines, unless unavoidable)
4. Apply refactoring patterns to reduce complexity
5. Track complexity improvements over time
6. Enforce complexity thresholds in CI/CD

## Required Tools

**In a Project workspace**, add to `[dependency-groups]` dev: `"radon"`,
`"lizard"`, `"xenon"`, `"wily"` — or reach them through `uvx` and add nothing,
since no gate step reads them.
**In `.meta/`** there is no manifest; `uvx` is the only route.

- **radon**: Cyclomatic complexity & maintainability index
- **lizard**: Cognitive complexity (better for readability)
- **xenon**: CI/CD threshold enforcement
- **wily**: Track trends across git history

**Permissions**: Run py-quality-setup first to configure `.claude/settings.local.json` with all needed tool permissions.

## Discovery Phase

### Measure Complexity

```bash
# Key commands
radon cc . -n C              # Functions with complexity ≥11
lizard -C 15 .               # Cognitive complexity warnings
radon mi . -n B              # Maintainability index <65
wily build .                 # Initialize tracking (one-time)
wily diff HEAD~10            # Compare trends
scc --by-file --ci           # Optional: code statistics (called 'sccount' on openSUSE)
```

### Thresholds

- **Cyclomatic**: Refactor at ≥C (11+)
- **Cognitive**: Refactor at >15
- **Maintainability**: Refactor at <65
- **Lines per code file**: Split if significantly >500, unless unavoidable

### Manual Pattern Detection

Use Explore agent to find these complexity-increasing patterns:

**Magic numbers and strings**:
- Numeric literals (except 0, 1, -1) scattered in code
- String literals used as keys, thresholds, or configuration
- Search: `grep -rE '\b[0-9]{2,}\b' --include='*.py'` for multi-digit numbers
- Look for: fee calculations, timeout values, buffer sizes, regex patterns

**Repetitive field operations**:
- Multiple similar if-statements checking/setting object fields
- Pattern: `if obj.field: obj.field = func(obj.field)`
- Search: Functions with 5+ lines doing similar operations on different fields
- Candidates: configuration loading, validation, serialization, field clearing

**Repeated complex type definitions**:
- Same complex type annotation used in multiple places
- Example pattern: `Literal["a", "b", "c"] | None` repeated across functions/classes
- Search: `grep -r 'Literal\[' --include='*.py'` then look for duplicates
- Also: Complex union types, nested generics used multiple times
- Candidates: Function parameters, return types, class attributes, cast() calls

**Long if/elif chains**:
- 5+ conditional branches doing similar operations
- Can often be replaced with lookup tables or polymorphism

**Deeply nested code**:
- 4+ levels of indentation
- Multiple nested loops or conditionals

## Refactoring Patterns

### Extract Function

Break complex functions into focused sub-functions:

```python
# BEFORE - 20+ lines, complexity: 15
def process_order(order: dict) -> bool:
    # Validation, payment, confirmation logic all mixed

# AFTER - Each function <5 lines, complexity: <5
def process_order(order: dict) -> bool:
    return is_valid_order(order) and process_payment(order) and complete_order(order)
```

### Guard Clauses

Replace nested conditions with early returns:

```python
# BEFORE - Deep nesting
if user:
    if user.get("active"):
        if user.get("verified"):
            return True
return False

# AFTER - Guard clauses
if not user or not user.get("active") or not user.get("verified"):
    return False
return True
```

### Lookup Tables

Replace if/elif chains with dictionaries:

```python
# BEFORE - Nested conditionals (complexity: 7)
if customer == "gold" and total > 1000: return 0.20
elif customer == "gold": return 0.15
# ... more branches

# AFTER - Lookup table (complexity: 2)
RATES = {("gold", "high"): 0.20, ("gold", "low"): 0.15, ...}
return RATES.get((customer, tier), 0.0)
```

### Extract Magic Numbers and Strings

Extract scattered literals to configuration classes:

```python
# BEFORE - Magic numbers throughout code
if amount < 100: base_fee = 2.50
elif amount < 1000: base_fee = 5.00
if account_type == "premium": return base_fee * 0.5

# AFTER - Configuration class
class FeeConfig:
    TIER_SMALL = 100
    FEE_SMALL = 2.50
    PREMIUM_DISCOUNT = 0.5

if amount < FeeConfig.TIER_SMALL:
    base_fee = FeeConfig.FEE_SMALL
```

**Benefits**: Single source of truth, easy to change, self-documenting, can load from environment

### Replace Repetitive Field Operations

Replace repetitive if-statements with loops over field names:

```python
# BEFORE - 15 similar if-statements (complexity: 9)
if config.email.smtp_host:
    config.email.smtp_host = substitute_secret(config.email.smtp_host, secrets)
if config.email.smtp_user:
    config.email.smtp_user = substitute_secret(config.email.smtp_user, secrets)
# ... 13 more similar lines

# AFTER - Loop over field list (complexity: 3)
email_fields = ["smtp_host", "smtp_user", "smtp_password", "smtp_from"]
for field in email_fields:
    if value := getattr(config.email, field, None):
        setattr(config.email, field, substitute_secret(value, secrets))
```

**Pattern**: Use getattr/setattr loops for: validation, field clearing, transformation, serialization

### Extract Repeated Complex Type Definitions

Replace repeated complex type annotations with TypeAlias:

```python
# BEFORE - Type repeated 8 times across files
cache_mode: Literal["use", "only", "refresh"] | None
# ... used in 8 different functions, classes

# AFTER - Define once, use everywhere
CacheMode = Literal["use", "only", "refresh"]
CacheModeOptional = CacheMode | None

cache_mode: CacheModeOptional
```

**Placement**:
- Module-level: types used within one module
- `types.py`: project-wide types
- `__init__.py`: package-wide exports

**Benefits**: DRY, semantic names, easier to change, reduced typos

## Verification Checklist

- [ ] `radon cc . -n C` reports no functions with complexity ≥C (11+)
- [ ] `lizard -C 15 .` reports no cognitive complexity warnings
- [ ] `radon mi . -n B` reports no modules with maintainability index <65
- [ ] No code files >500 lines (unless unavoidable)
- [ ] `wily build .` initialized for tracking

**Repository tooling (`.meta/`)**

- [ ] Every `# noqa: F401  # reason: ...` import and `@check` function survived the extraction
- [ ] `just gate meta` is green **and reports the same number of steps as before**
- [ ] No complexity threshold was claimed to be gate-enforced: `.meta/ruff.toml` does not select `C90`

**A Project workspace**

- [ ] `uv run gate ruff` passes, `C90` included, at `max-complexity = 12`
- [ ] `uv run gate` is green from the Project's directory: `test` and `mutants` included
- [ ] Coverage maintained or improved

## Examples

**Example: Complexity reduction workflow**
```
1. Measure: radon cc . -n C; lizard -CCN 15 .
2. Found: handlers.py:process_data (complexity D: 25)
3. Apply patterns: Extract functions, guard clauses, lookup tables
4. Result: 4 functions with complexity A-B
5. Track: wily diff HEAD~1 shows 20-point reduction
```

**Example: Apply specialized patterns**
```
# Magic numbers: Search with grep, extract to config class
if amount < 100: fee = 2.50  # BEFORE
if amount < FeeConfig.TIER_SMALL: fee = FeeConfig.FEE_SMALL  # AFTER

# Repetitive fields: Replace 15 if-statements with loop
for field in ["smtp_host", "smtp_user", ...]:
    if value := getattr(config, field, None):
        setattr(config, field, process(value))

# Complex types: Extract repeated Literal types to TypeAlias
CacheMode = Literal["use", "only", "refresh"]  # Used 8 times → defined once
```

## Related Skills

- **Prerequisites**: py-quality-setup (tool configuration), py-test-quality (safety net before refactoring)
- **Prior cleanup**: py-code-health (remove dead code first to reduce noise)
- **Enforcement**: py-git-hooks (add complexity checks to pre-commit)
