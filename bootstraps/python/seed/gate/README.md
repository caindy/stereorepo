The gate for this workspace, as a console script: `uv run gate` runs every
step, and `uv run gate <step>` runs one. It is a workspace member rather than
a script so that it has tests holding it and its probes have somewhere to
live, and so that a Python Project needs nothing but `uv` to be held to its
standard.

Every step answers to four rules, and they are the whole contract:

- **A5 — no gate step rewrites the tree.** Every tool invocation here is a
  type check, linter or a test. Fixing is `ruff check --fix`, run by a person,
  never from here.
- **A6 — every step has three outcomes.** `CouldNotRun` is loud, unmarked and
  exits zero where a person runs it, and non-zero under CI, so a missing tool
  is reported rather than passed. `Passed` is marked. `Found` is non-zero.
- **A7 — a check-mark is a claim about scope.** A passing step prints what it
  covered beside its mark, so `ok orphans` says how many files it looked at and
  under how many packages.
- **A21 — a gate reports each step in the one shape every gate here prints.**
  `ok`, `x` or `?`, the step, then what it covered, found, or could not do. The
  Portfolio's own gate and the Rust xtask print the same lines, and a runner
  above the Projects reads all three without knowing which language any is in.

The steps, in the order they run:

| Step | What it holds | Discipline |
|---|---|---|
| `lints` | no rule switched off in a manifest, every ruff configuration selecting at least `SELECT_FLOOR`; every `noqa` and `type: ignore` carries a reason | Ratchet |
| `comments` | zero commented-out code, specific suppression codes, and the four permissible comment exceptions within function bodies | Literate Programming |
| `wheel` | each member's wheel `packages` entry is a directory with an `__init__.py`, and every package under `src/` is one of them | Nothing Unconsumed |
| `ruff` | `ruff check`, with the rule set the workspace manifest selects | Ratchet |
| `types` | `mypy --strict` over each package's source and tests | Ratchet |
| `doc` | every module and every public function, class and method has a docstring | Literate Programming |
| `test` | `pytest`, doctests included | Literate Programming |
| `orphans` | every markdown file under a package is named by a source file or manifest in it | Nothing Unconsumed |
| `evidence` | every history entry names a test that pytest collects | Nothing Unconsumed |
| `mutants` | `mutmut`, the signal behind the tests | Observed Failure |

The pure steps — `lints`, `comments`, `wheel`, `doc`, `orphans`, `evidence` — are functions over a
path, so `tests/test_probes.py` can watch each of them fail against a tree
built to fail it. A guardrail never observed to fail is not evidence of
anything.
