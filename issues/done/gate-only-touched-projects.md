---
difficulty: medium
---

# Gate only the Projects a change touches

Before an Issue lands, the loop runs the whole `just gate`: every Project in
the portfolio, the Rust and Python seeds' mutation testing included, whatever
the change touched. That is a catch-all, and it is slow: it is paid on every
landing, and for most changes most of it checks code nothing changed.

`.meta/assertions/structure.yaml` already says which Project each path belongs
to, so the loop could gate only the Projects a change touches, and the
Products built from them. The cost is the catch-all itself: a change that
breaks a Project through something the mapping does not see, such as a shared
tool or a generated file, would land unchecked.

On 2026-10-01 the developer decided not to wait for evidence that this is
safe, such as the "defects found after landing" measure from
`pair-versus-single-seat`: the loop needs to move faster, and the risk is
accepted. The full gate before each landing cost 2 to 2.5 minutes an Issue
that day. Record the decision and the risk it accepts in a Decision Record.

## What is wanted

Wherever the loop gates today (`pair/pair.py` `gate`, called from the stage
exits and from `merge` in `pair/loop.py`), it gates a selection computed from
the branch's diff against `main` (`git diff --name-only main...HEAD`, as
`touches_code` reads it):

1. A changed path belongs to the Project whose `name` in `structure.yaml` is a
   directory containing it (`.meta`, `bootstraps/rust/seed`,
   `bootstraps/python/seed`, `pair`). A path under no Project's directory
   (`wiki/`, `justfile`, `AGENTS.md`, `bootstraps/rust/render`, …) belongs to
   `work:project/meta`, whose checks are the portfolio-wide ones. That
   includes `issues/`: the `meta` gate checks the board
   (`.meta/checks/files/board.py`), and the grooming and Flight-check exits
   gate today on branches that change only `issues/`. The existing
   `touches_code` conditions on the in-progress exit and on `merge` stay as
   they are, so an `issues/`-only change still skips the gate there.
2. Each touched Project brings in every Product whose `built_from` names it,
   and the selection is every Project those Products are built from. So a
   change to `pair/`, `.meta/`, `wiki/` or `issues/` gates `meta` and `pair`
   (the scaffold); a change to `bootstraps/rust/seed/` alone gates
   `rust-seed`.
3. The mapping is read from `structure.yaml` in the worktree, not hard-coded,
   so a Project added there is selected without a code change.
4. When the selection is every Project, the result is the same as `just gate`
   today.
5. An empty selection (the diff against `main` is empty) passes without
   running `.meta/gate`, which refuses a selection of nothing.
6. A gate failure handed back to the seats names what was gated (the
   requirement text in `gate_fails` says `just gate` today).

`.meta/gate` takes one word today (`main` reads `argv[1]`) and the `gate`
recipe in `justfile` takes one `target`. Extend both so `just gate <a> <b>`
gates the union of what each word selects, in one run with the Projects in
parallel as now; `just gate` with no argument keeps gating every Project.

A Decision Record, `DR-303` or the next free number, records the decision of
2026-10-01: gate only the touched selection before landing, the cost it
saves, and the risk it accepts (a break through a shared tool, a generated
file or anything else the path mapping does not see lands unchecked).

## Out of scope

- Detecting dependencies the path mapping does not see (shared tools,
  generated files, cross-Project imports). That is the accepted risk.
- Making any Project's own gate faster, or skipping mutation testing inside a
  Project that is selected.
- Running the whole gate on a schedule or after landing as a backstop.

## Done when

- Tests in `pair/test_pair.py` show the selection for: a change under `pair/`
  only (meta and pair), under `bootstraps/rust/seed/` only (rust-seed), under
  `wiki/` only (meta and pair), under both seeds (both seeds, nothing else),
  under `issues/` only (meta and pair), and an empty diff (nothing, and the
  gate passes without running).
- A test shows a Project added to a `structure.yaml` written in the test's
  repository is selected for a change under its directory.
- A test shows `.meta/gate` given two words gates the union of their
  Projects, and given none gates every Project. Nothing tests `.meta/gate`
  today; the test can copy it into a temporary tree beside a `structure.yaml`
  whose Projects' gates only print an `ok` step, since it reads the file
  relative to itself.
- A test shows the merge-time gate after `main` moves uses the same selection
  for the squashed change.
- A test shows a gate failure handed back to the seats names the targets
  gated.
- The Decision Record exists and the decision index is re-rendered.

## The plan

Four parts, done in this order, each with its tests: the runner learns to take
several targets, the loop learns what to pass it, the docs and prompts follow,
and the Decision Record goes in last.

**1. `.meta/gate` takes several words.**
- `.meta/gate`: add `select_all(words, projects, products)`, which runs
  `select` on each word and returns the union in the order the Projects are
  declared, each Project once. It returns every Project when `words` is empty.
  `main` passes it `argv[1:]`, and the label it prints is the words joined
  with spaces, or `portfolio` when there are none. The parallel run is
  unchanged. The file is 204 lines, well under its ceiling of 350.
- `.meta/lib/render/writers.py` (`justfile()`): render the recipe as
  `gate *targets:` running `.meta/gate {{targets}}`. Its doc comment keeps
  reading the names from `structure.yaml` (the `takes` string), worded as
  "or any of the Projects: … — and the Products: …" rather than "one".
  The `.meta/gate` module docstring and `main` docstring say it takes words,
  not a word. `.meta/checks/files/justfile.py`
  `CONTRACT`: `"gate": (("targets", FLAGS),)`. Then run `just render`, which
  regenerates `justfile`. Do not edit `justfile` by hand.
- Test: extend the probe in `.meta/checks/probes/tools/gate.py`, which already
  loads `.meta/gate` as a module. On in-memory Project and Product dicts it
  asserts:
  - `select_all([])` is every Project;
  - `select_all(["pair", "rust-standard"])` is pair and rust-seed;
  - `select_all(["scaffold", "pair"])` is meta and pair, each once.

  This replaces the issue's suggestion to copy the script into a temporary
  tree: the probe already loads the module, and the union is pure.

**2. The loop gates what the branch touches.**
- New `pair/touched.py`, with `select(tree, paths) -> list[str] | None`:
  - It reads `<tree>/.meta/assertions/structure.yaml` and returns `None` when
    the file is absent, which means the whole gate. That keeps the loop
    working on a repository that asserts no structure, the test `Bench`
    included.
  - Each path maps to the Project whose `name` is a directory prefix of it
    (the longest prefix wins), or to `work:project/meta` when no Project's
    directory contains it, `issues/` included.
  - Each touched Project brings in the Products whose `built_from` names it,
    and the result is the short ids of those Products' Projects, in declared
    order. A touched Project that no Product is built from still counts.
  - The result is `[]` for no paths, and `None` when the selection is every
    Project, so that case runs exactly `just gate` as today (requirement 4).
- `pair/loop.py`:
  - `Gate` becomes `Callable[[Path, Sequence[str] | None], tuple[bool, str]]`.
  - New `Loop.run_gate() -> GateFailure | None`. It reads the diff against
    `main` (all paths, `issues/` included), returns `None` without calling the
    gate when the diff is empty, and otherwise calls
    `self.gate(self.wt, touched.select(self.wt, paths))`.
  - It replaces the five `ok, out = self.gate(self.wt)` sites: grooming, the
    two Flight-check exits, in-progress and `merge`. `merge` keeps its own
    branching on the result.
  - `gate_fails(out, targets)` names what ran, as "`just gate meta pair`
    fails", or "`just gate` fails" when `targets` is `None`.
  - The `touches_code` conditions stay where they are.
- `pair/pair.py` `gate(tree, targets)`: runs
  `["just", "gate", *(targets or [])]`, and its docstring says it gates what
  the branch touches (and why, citing the new Decision Record).
- Tests in `pair/test_pair.py`:
  - **What gets gated.** Pure tests of `touched.select` on a fixture
    `structure.yaml` mirroring the four Projects and three Products, written
    into a temporary tree. Each case from "Done when" is covered (`pair/`;
    the Rust seed; `wiki/`; both seeds; `issues/`), plus no paths giving
    `[]`, no `structure.yaml` giving `None`, and a selection of every Project
    giving `None`.
  - **The loop wiring.** The `Bench` fake gate records the `targets` it is
    given in a new `gate_targets` list. A test commits a fixture
    `structure.yaml` that adds a `widgets` Project and a Product built from
    it, has the seat change `widgets/x.py`, and asserts that the recorded
    targets contain `widgets` and leave out the seeds.
  - **The gate at landing.** The same setup, with `main` moved before landing
    (the pattern in `test_a_commit_on_main_while_merge_gates_is_not_reverted`).
    It asserts that `merge`'s gate receives the same targets as the
    in-progress gate.
  - **The failure message.** The same setup, with `b.gates = [False, True]`.
    It asserts that the note handed to the primary seat contains
    "`just gate widgets` fails" (or whatever the fixture selects).
  - **An empty diff.** Calling `run_gate` on a worktree with no change
    against `main` returns `None` with `gate_runs` still at 0.

**3. Docs and prompts.**
- `pair/README.md`: lines 8, 30–32, 51 and 170 say the loop runs the full
  `just gate`. They should say it gates the Projects the change touches and
  the Products built from them, and cite the new Decision Record.
- `pair/prompts/primary.md` and `pair/prompts/secondary.md` share the
  sentence "Never run the whole `just gate` … the loop runs it once both of
  you leave a stage". Keep the instruction; change "runs it" to "runs the
  gate of what the branch touches" in both, word for word alike.
- `pair/prompts/stage-in-progress.md` says "the loop runs it before the
  issue lands". Its per-directory list of targeted gates stays (the seat
  still checks its own work), but the loop's sentence changes the same way.
  `stage-backlog.md` and `stage-grooming.md` say "the loop runs the gate",
  which stays true; leave them.

**4. The Decision Record.**
- Add `.meta/assertions/decisions/DR-303.yaml`, or the next free number,
  modelled on DR-302 and enacted in `work:artifact/pair`,
  `work:artifact/pair-readme`, `work:artifact/meta-gate` and
  `work:artifact/meta-lib-render-writers` (all four declared in
  `structure.yaml`). The context is the full gate costing 2 to 2.5
  minutes an Issue on 2026-10-01. The rejected alternatives are waiting for
  the "defects found after landing" measure, and keeping the full gate. The
  consequence is the accepted risk: a break through a shared tool, a
  generated file or another path the mapping does not see lands unchecked.
- Run `just render` again, which regenerates `.meta/decisions.md`.

**Risks.**
- `pair-accept` lands through `merge(force_gate=…)` (in `Loop.accept`), so
  the accept path is covered by the `merge` site; there is no sixth site.
- Existing tests that count `gate_runs` could shift if any of them reached
  the gate with an empty diff. `Bench` has no `structure.yaml`, so every
  other path still runs the whole gate as today. Run the pair tests after
  step 2 and read every changed count rather than editing it to pass.
- Only `run_gate` and `pair.gate` change signature. A test or caller that
  builds a `Loop` with a one-argument gate breaks loudly, which is the point.
- A `just` variadic with no arguments must expand to nothing, so `just gate`
  stays the whole portfolio. Check by hand once that `.meta/gate` receives an
  empty `argv[1:]`.
- The selection reads `structure.yaml` from the branch, so a branch that adds
  a Project is gated on its own declaration, which is the intent.

## Notes from the implementation

- The plan held, with three changes:
  - **`touched.select` covers one more case.** A path that falls to `meta`
    when the structure declares no `meta` Project returns `None`, the whole
    gate. Without that, a repository whose `structure.yaml` lacks `meta`
    would select nothing for a change to `wiki/` and skip its gate.
  - **`run_gate` checks the diff before calling `touched.select`.** An empty
    diff passes before the selection runs, so `Bench`, which has no
    `structure.yaml`, still never runs a gate on an empty branch.
  - **No existing `gate_runs` count changed.** The 156 existing pair tests pass
    unedited, beside the 9 new ones.
- The tests live in `GateSelectionTest` in `pair/test_pair.py`. Its fixture
  `STRUCTURE` adds a fifth Project, `widgets`, that stereorepo does not have.
  That is how the tests show a newly asserted Project being selected, and it
  means no fixture selection is ever every Project by accident.
- Every branch changes its Issue file under `issues/`, and `issues/` counts as
  `meta`'s, so in this repository the loop always gates at least `meta` and
  `pair` (the scaffold). A change confined to one seed is still gated with
  the scaffold's Projects as well. The saving is in the seeds' gates, the
  mutation testing among them, which no longer run unless a seed changes.
- `just render` fails in a seat's sandbox, because it rewrites
  `.claude/skills/*/SKILL.md` and the sandbox denies writes there. It writes
  every page before reaching those files, and `render.py --check` reported
  "up to date" afterwards, so nothing it renders was left stale.
- `just --dry-run gate` prints a bare `.meta/gate`, so with no targets the
  variadic expands to nothing and the gate still covers every Project.
- `run_gate` reads the diff with `--no-renames`. `git diff` detects renames
  by default and `--name-only` then lists only the new path, so a file moved
  out of `bootstraps/rust/seed/` into `wiki/` would not have gated
  `rust-seed`. `test_a_file_moved_out_of_a_project_gates_the_project_it_left`
  fails without the flag.
