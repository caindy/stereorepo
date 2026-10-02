---
difficulty: medium
parent: onboard-fitch-mvp
---

# Leave a portfolio no step that can never run there

A freshly specialized portfolio's `meta` gate reports two steps as `?` for
good: `brownfield adoption probes` (no `template/` to adopt from) and
`comment probes` (no `bootstraps/python/seed/gate/src` to keep in step with
`comments.py`). Both steps exercise something only the scaffold has. The
`specialized-portfolio-gate` Issue made them say so rather than fail. But a
`?` fails the run wherever `CI` is set (`.meta/check.py`, `closing_block`,
DR-261). So a portfolio whose CI sets `CI` fails on every run, and so does
`just test-specialization` run under CI, since `step_8_run_gate` passes the
environment through.

Since `landing-gate-holds-on-could-not-run`, the pair loop also holds every
landing whose gate reports a step that could not run. fitch-mvp's `meta` gate
reports both, so no Issue can land in fitch-mvp until this one does.

## How to reproduce it

Run `just test-specialization` with `CI=1` in the environment. Step 8 runs
the portfolio's gate, which lists both steps under "steps that could not
run" and exits non-zero.

## Wanted

A freshly specialized portfolio's `meta` gate reports no step as `?`, so it
passes with `CI` set. The developer's answers below say how; what the code
shows about each:

- **Brownfield.** Specialization copies a whitelist (`.meta/bundle.yaml`, and
  the *Copy what is inherited* step in `.meta/assertions/disciplines.yaml`).
  `.meta/adapt.py` is an entry in both and comes out of both. `.meta/lib/`
  and `.meta/checks/` are copied whole, so `.meta/lib/adapt/` and
  `.meta/checks/probes/tools/test_brownfield.py` become entries of
  `SCAFFOLD_ONLY` and `SCAFFOLD_ONLY_PATHS`, and the copy leaves out anything
  those name. `checks/probes/tools/__init__.py` imports `test_brownfield`
  unconditionally, so a portfolio must not fail on its absence. The `adapt`
  recipe is rendered only where `work:artifact/meta-adapt` is asserted
  (`.meta/lib/render/writers.py`). A portfolio's `structure.yaml` comes from
  `template/` and does not assert it, so the portfolio already gets no
  `adapt` recipe; only the test for its absence is new. The *Confirm scaffold-only paths absent* step
  names the new paths, and `SPECIALIZE.md` is re-rendered. The
  `scaffold-only paths` step scans inherited files for every `SCAFFOLD_ONLY`
  entry, so an inherited file that names one of the new paths bare must
  qualify it with the scaffold's name or drop it.
- **Comment probes.** The synchronization half reads the Python Projects from
  `structure.yaml` (`language: Python`) and checks each one's `gate/src`
  package, where it has one, against `comments.py`. In the scaffold that is
  `bootstraps/python/seed` (the `pair` Project has no `gate/src`), so
  `SEED_GATE` and its could-not-run branch go. Each Project's `gate` module is
  imported afresh: a second `import gate` would otherwise answer from
  `sys.modules` for the first Project. A disagreement names the Project.

## Out of scope

- How `closing_block` treats a `?` under CI (DR-261 stands).
- Any other step that is `?` in the scaffold itself.
- Rust Projects: their gate has no copy of `comments.py`'s detectors.

## Done when

- `just test-specialization` run with `CI=1` passes step 8; its gate output
  has no `brownfield adoption probes` step at all, and `comment probes`
  passes having checked `core-lib`'s gate package.
- The specialized fixture has no `.meta/adapt.py`, `.meta/lib/adapt/`,
  `.meta/checks/probes/tools/test_brownfield.py` or `adapt` recipe, and
  step 7 fails if any of them is present.
- The scaffold's `meta` gate still runs both steps and they pass, with
  `comment probes` checking `bootstraps/python/seed`.
- `comment probes` probes its own synchronization: a Project gate package
  that disagrees with `comments.py` fails, naming that Project; two
  Projects are each checked; no Python Project with a gate package passes,
  saying in its scope that there was none to check.
- A DR records the three answers below.

## The developer's answers (2026-10-02)

1. **`brownfield adoption probes`: remove.** Specialization removes
   `.meta/adapt.py`, `lib/adapt` and their probe from a portfolio, since they
   have no subject there.
2. **`comment probes`: keep the Projects in lockstep.** In a portfolio, the
   synchronization half of the step checks every Python Project's `gate`
   package (each one `just bootstrap python` laid down, such as
   `core-lib/gate` in the specialization fixture) against
   `.meta/checks/comments.py`, in place of the scaffold's seed. A Project's
   `uv run gate` and the root `just gate` must give the same verdict on the
   same code. Otherwise a seat's targeted gate can pass a change that the
   landing gate refuses. The cost is accepted: a change to `comments.py`
   updates every Python Project's copy in the same change. A portfolio with
   no Python Project has nothing to synchronize, and the step says so in its
   scope and passes.
3. **How removal is expressed: accept nested paths.** `SCAFFOLD_ONLY_PATHS`
   (`.meta/test_specialization.py`) and `SCAFFOLD_ONLY`
   (`.meta/checks/files/scaffold.py`) accept paths below the top level, so a
   single probe module under `.meta/checks/probes/` can be scaffold-only.

Record these answers as a Decision Record, with the change.

## The plan

### 1. Scaffold-only paths below the top level

- `.meta/checks/files/scaffold.py`: `SCAFFOLD_ONLY` gains `.meta/adapt.py`,
  `.meta/lib/adapt/` and `.meta/checks/probes/tools/test_brownfield.py`.
  Its two readers already work on prefixes (`rel.startswith` in
  `files/prose.py`, `name in line` in `scaffold_only_lines`). No inherited
  `.md` or `.yaml` names these paths today, so the scan does not start failing.
- `.meta/test_specialization.py`: `SCAFFOLD_ONLY_PATHS` gains the same three
  entries, without the trailing slash, which is how it spells them. Step 7
  already checks `target_path / entry`, so it covers nested paths unchanged.
  `_copy_item` takes an `ignore` that drops any scaffold-only path. Step 2
  copies `.meta/lib/` and `.meta/checks/` through `shutil.copytree(...,
  ignore=...)`, with the ignore keyed on the path relative to the scaffold
  root, so a fixture never holds what step 7 refuses.
- The two lists stay separate, because `test_specialization.py` is not
  imported by the gate (DR-150). The scaffold-only path probe
  (`checks/probes/files/scaffold.py`) gains a case asserting that they name
  the same paths, ignoring the trailing slash. It loads `test_specialization.py`
  with `load_module`, and where that file is absent, as in a portfolio, it
  skips the case.

### 2. Leave the brownfield machinery out of a portfolio

- `.meta/bundle.yaml`: remove the `.meta/adapt.py` item, leaving 28 managed
  items. `_check_bundle` requires at least 25, so it still passes.
- `.meta/assertions/disciplines.yaml`:
  - *Copy what is inherited* drops `.meta/adapt.py` and says the copy leaves
    out the paths in *Confirm scaffold-only paths absent*.
  - *Confirm scaffold-only paths absent* names all seven paths.
  - Then `just render` regenerates `SPECIALIZE.md` and `.meta/disciplines.md`.
- `.meta/checks/probes/tools/__init__.py`: import `test_brownfield` only
  where `test_brownfield.py` sits beside `__init__.py`, keeping its place in
  the import order (DR-218). Nothing else inherited imports `lib.adapt`; the
  only importers are `.meta/adapt.py` and `test_brownfield.py`.
- `test_brownfield.py` keeps `NO_TEMPLATE`, `_check_without_template` and
  its could-not-run branch, and only its docstring changes: a specialized
  portfolio no longer has the module, so the branch now answers only for a
  brownfield-adopted repository. The module is not only where `template/`
  is. `lib/adapt/plan.py` plans `.meta/checks/` as one `dir` item
  (`_classify_dir` never looks inside), so an adopted repository still gets
  `test_brownfield.py` without `template/`. Leaving such paths out of the
  adoption plan is `adoption-plan-omits-scaffold-only-paths` in the backlog,
  not this Issue.
- The `adapt` recipe needs no change: the reason is recorded under *Wanted*.

### 3. Comment probes keep every Python Project in lockstep

- In `.meta/checks/probes/tools/comments.py`, `SEED_GATE` is replaced by
  `python_gates(root=ROOT)`. It reads `.meta/assertions/structure.yaml` with
  `yaml.safe_load`, because the step is `pre=True` and runs before the index
  exists. A Project's `name` is its directory (`bootstraps/python/seed`,
  `core-lib`; `.meta/bootstrap.py` registers it that way). It returns
  `(project name, <name>/gate/src/gate/__init__.py)` for
  each Project whose `language` is exactly `Python` and whose file exists.
  In the scaffold that is `bootstraps/python/seed` only. In the fixture it is
  `core-lib`. The `meta` Project's language is `LinkML YAML, with Python …`,
  so an exact match excludes it.
- `_seed_gate_sync(comments, gate_file, project)` loads each gate with
  `checks.probes.harness.load_module(path, f"gate_{n}", register=True)`. That
  gives a fresh module per Project, with no `sys.path` edit and no stale
  `sys.modules["gate"]`. The seed gate is a single-file package with no
  intra-package imports, so loading it from a path is sound. Every problem
  line names the Project.
- `comment_probes` returns a `StepOutcome`:
  - `Found` listing the problems, or
  - `Passed`, whose scope names the Projects checked, or says that no Python
    Project has a gate package to keep in lockstep.
  - It never returns `CouldNotRun`.
  
  The signature's seam becomes `root: pathlib.Path = ROOT`, for the probes.
- The probe `_seed_absent` is replaced by `_lockstep`, which writes
  `structure.yaml` and gate packages into a temporary root. It does not copy
  the seed, which a portfolio lacks. Each package is a stub module that
  re-exports the eight names the sync reads (`DIRECTIVE`, `NOTICE`,
  `CITATION`, `NOQA`, `TYPE_IGNORE`, `STATEMENTS`, `keep_exception`,
  `python_code`) from `checks.comments`. A stub that agrees does so by
  construction; a disagreeing stub rebinds `NOQA`. `_lockstep` asserts:
  - two agreeing Projects are both checked and both named in the scope;
  - one disagreeing Project fails, and the failure names that Project only;
  - a Rust Project, and a Python Project with no `gate/src`, are skipped;
  - no Python Project with a gate package passes, saying so.
- Rewrite the docstrings of `comment_probes`, `_verdict` and the module:
  the could-not-run paragraph goes, and the sync is described as being over
  the Projects, citing the new DR.

### 4. Decision Record

`DR-305` records the three answers and their alternatives:
- keep reporting `?` (not chosen);
- move the step's sync into the seed's own gate (not chosen: it would not
  check a portfolio's copies).

Its consequences: a change to `comments.py` updates every Python Project's
gate, and a scaffold-only entry may be nested. Its `enacted_in` lists
`.meta/checks/probes/tools/comments.py`, `.meta/checks/files/scaffold.py` and
`.meta/test_specialization.py`, by their artifact ids. Re-render.

### Order

Do 1, then 2, then 3, then 4. Step 1 makes the nested exclusions possible
before step 2 relies on them, and step 3 is independent of both. Run
`just test-specialization` with `CI=1` last, as the end-to-end check from
*Done when*.

### Tests

- The probes added in steps 1 and 3 (list agreement, and `_lockstep`).
- A case in `test-specialization probes`: `_copy_item` over a temporary tree
  holding `.meta/checks/probes/tools/test_brownfield.py` and
  `.meta/lib/adapt/` leaves both out.
- A case in `test-specialization probes`: step 7 over a temporary target
  holding `.meta/adapt.py` returns 1.
- `just test-specialization` with `CI=1`: step 8 passes, with no brownfield
  step, and `comment probes` passes naming `core-lib`.

### Risks

- **Fixture and seed must already agree.** `core-lib`'s gate is a rendered
  copy of the seed, so the token substitution in step 4 must not touch the
  patterns. If the end-to-end run shows a disagreement, that is a real
  finding, not something to suppress.
- **Stub gates.** A stub module importing `checks.comments` needs `.meta/` and
  `.meta/checks/` on `sys.path`; `load_module` puts them there.
- **Discipline wording.** `scaffold-only paths` scans inherited `.yaml`. If
  `disciplines.yaml` is ever inherited, its new bare path names would be
  flagged. Today it is not inherited, and it already names `template/` and
  `bootstraps/` bare, so this adds nothing new.

## What the implementation found

Where the work departed from the plan:

- **The lockstep has its own module.** It lives in
  `.meta/checks/probes/tools/lockstep.py`, not inside
  `.meta/checks/probes/tools/comments.py`. Kept in `comments.py`, the probe
  took the file to 512 lines, past its 500-line ceiling. The new module
  holds `python_gates`, `lockstep`, `verdict`, `gate_sync` and
  `lockstep_probes`, and `comments.py` imports them. It is asserted as
  `work:artifact/meta-checks-probes-tools-lockstep`.
- **The step's verdict.** The `comment probes` step returns `Found`, or
  `Passed` with a scope naming the Projects checked: in the scaffold,
  "in lockstep with the gate of bootstraps/python/seed"; in the fixture,
  "… of core-lib".
- **The brownfield probe is imported last.** In
  `checks/probes/tools/__init__.py` the guarded import is the final line, so
  the step now reports after `comment probes`, not before `gate runner`.
  Putting the guard mid-block would have split the import block and needed a
  second `I001` suppression.
- **`.meta/test_specialization.py` is shorter.** It was at its file-size
  baseline, so the eight `code = …; if code != 0` pairs became a loop over
  the steps, and an `if load_bundle is not None` that is always true went.
  It is now 478 lines, and its baseline is lowered to 128.
- **A second baseline is lowered.** `comments.py`'s long-line baseline is
  now 28: the old seed-gate docstring was one of its 29 long lines.
- **The Specialization step leaves the new paths bare.** *Copy what is
  inherited* refers to them through *Confirm scaffold-only paths absent* and
  does not name them in backticks. `read_inherited_paths` takes every
  backticked token in that step as a path to copy.
- **`just render` stopped part-way.** The sandbox refused its write to
  `.claude/skills/wikisplain/SKILL.md`. It had already rewritten
  `SPECIALIZE.md`, `.meta/disciplines.md` and `.meta/decisions.md`, and
  `rendered prose` passes, so nothing under `.claude/` needed to change.
- **An incomplete gate package fails, naming its Project.** `gate_sync`
  first checks that the package has every name it compares (`PATTERNS` and
  `DETECTORS` in `lockstep.py`), and catches a `SyntaxError` as well as an
  `ImportError` on loading. Before this, a Project gate without `STATEMENTS`
  stopped the step with an `AttributeError` that named no Project.
  `lockstep_probes` has a case for it.

Verified:
- `CI=1 just test-specialization` exits 0. The portfolio's gate has no
  `brownfield adoption probes` step and no step that could not run.
- `just gate meta` passes, with both steps running in the scaffold.
