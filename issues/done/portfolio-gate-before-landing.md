---
difficulty: medium
---

# Run a portfolio's gate before a change to what portfolios receive lands

A defect that shows only in a portfolio can land in stereorepo unseen.
`_probe_adopt` failed every portfolio's `meta` gate, specialized or adopted,
and landed, because nothing runs a portfolio's gate before landing:
`just test-specialization` (`.meta/test_specialization.py`) builds a
portfolio and runs its gate (step 8), but neither the loop nor `just gate`
runs that recipe. `adopt-probe-passes-in-a-portfolio` made stereorepo's own
gate run that one probe's portfolio branch, which covers that probe and no
other. It was found by hand, in fitch-mvp.

The loop chooses what to gate before landing in `pair/touched.py`
(DR-303): a changed path selects the Project whose directory holds it, and
every path under `.meta/` selects `meta`. `placed()` there already reads
`.meta/bundle.yaml`, but only to keep the bundle's paths with `meta` beside a
root Project, and stereorepo declares no root Project, so here the bundle is
not read at all. No selection follows from a path being one a portfolio
receives, so nothing gates a portfolio for it.

## Wanted

Before a change lands that alters what a portfolio receives (a path inside
one of the managed items in `.meta/bundle.yaml`, the `source` of one of its
template items, such as `template/AGENTS.md` rather than the `path`
`AGENTS.md` it is copied to, or `.meta/bundle.yaml`, which lists itself as a
managed item), a specialized portfolio's gate runs against it, and a
failure there holds the landing as any gate failure does. A change that
touches none of it lands without that cost, in the spirit of DR-303.

One shape that fits the existing selection: declare the specialization as a
Project (or Product) in `.meta/assertions/structure.yaml` whose gate runs
`.meta/test_specialization.py`, and have `pair/touched.py` select it when a
changed path lies inside a bundle item. Whichever shape is chosen, its gate
reports in the gate contract's shape, and the choice is recorded in a
Decision Record that extends DR-303. That record also says whether `just gate`
with no argument (and so `select()` returning `None` for a change that picks
every Project) runs the specialization too. A declared Project joins it by
default.

Every Project in `structure.yaml` has a directory `name`, and `home()` gives
a path to the deepest Project whose directory holds it. A specialization
Project must not be given a `name` that holds `.meta/` paths, or it would
take them from `meta` instead of being selected beside it.

## Out of scope

- Adopting a repository in the test, as well as specializing one.
- Making `test_specialization.py` faster.
- Changes under `bootstraps/`. The seed Projects' own gates already cover
  them.
- Portfolio-owned items (`ownership: portfolio`, such as `stakeholders/`)
  and the symlink items: no copy or sync brings their contents from
  stereorepo.

## Done when

- A test of the selection in `pair/test_pair.py`: a change to a path inside
  a managed bundle item (for example under `.meta/checks/`) selects the
  portfolio gate beside `meta`, and so does a change to a template item's source or to
  `.meta/bundle.yaml`. A change only to `issues/`, `pair/`, or a `.meta/`
  path outside every bundle item (for example `.meta/test_specialization.py`
  if the bundle doesn't list it), or to `stakeholders/` outside its managed
  READMEs, does not.
- Running the selected gates for such a change runs the specialization and
  fails when the specialized portfolio's gate fails. Show it once by hand
  with a managed probe that reads a file only stereorepo has, and note the
  output here.

## The plan

The shape: a Project `work:project/specialization` in stereorepo's
`structure.yaml`, built into no Product, whose gate is
`.meta/test_specialization.py`. `pair/touched.py` adds it to the selection
when a changed path is one a portfolio receives.

1. **The Project.** Add it after `pair` in `.meta/assertions/structure.yaml`:
   `name: specialization` (no such directory exists, so `home()` gives it no
   paths and `.meta/` stays with `meta`), `language: Python`, and a gate that
   runs `.meta/test_specialization.py` under `uvx --python 3.13 --with pyyaml`,
   as the `test-specialization` recipe does. Leave it out of every Product's
   `built_from`. If it were in `scaffold`, every change to `meta` or `pair`
   would select it, which would defeat the narrowing. Re-render so the `gate`
   recipe's comment lists it. Then run the `meta` checks once to find any probe
   that treats a Project's `name` as a directory that must exist, such as
   wiki contexts, lockstep or artifacts. If one does, the fallback is
   `name: .meta/fixtures/specialization`, the specialization's fixture
   directory. But that `name` would take those fixture paths from `meta`,
   which the issue warns against, so prefer fixing the probe.
2. **The gate's report in the gate contract's shape (A21).** `.meta/gate`
   counts a Project as failed if it prints no line in A21's shape on stdout.
   `test_specialization.py` prints none. Its narration goes to stdout, and on
   failure `_run_gate` prints the inner portfolio gate's stdout, whose
   `ok …` and `x  … (n)` lines the outer runner would misread as this
   Project's own steps. Change it so that:
   - the narration and the inner gate's output go to stderr (the runner
     forwards stderr);
   - `main` prints one line on stdout at the end: `ok specialize — 9 steps`,
     or `x  specialize (1)` followed by `     step N: <what failed>`.

   Each `step_*` already returns a code. Have `execute_specialization_test`
   report which step failed so the problem line can name it. The
   `test-specialization` recipe keeps working; its reader sees the same
   text, now on stderr, and the summary line at the end.
3. **The selection.** In `pair/touched.py`:
   - Add `SPECIALIZATION = "work:project/specialization"`.
   - Add `receives(tree) -> frozenset[str]`, the items of `.meta/bundle.yaml`
     whose `ownership` is `managed` or `template`, keyed by their
     `source`, falling back to `path` (a template item's `path` is where it is
     placed, `AGENTS.md`; its `source`, `template/AGENTS.md`, is what is
     copied, as `BundleItem.source_path()` in `.meta/lib/bundle` reads it).
     It uses `placed()`'s rule that a `dir` item is a prefix ending in `/`.
     Factor the bundle parsing out of `placed()` so the two share it;
     `placed()` keeps every item, as now. `bundle.yaml` lists itself as
     managed, so it needs no special case.
   - In `select()`, after `touched` is computed and before the `<= projects`
     check, add `SPECIALIZATION` to `touched` when it is a declared Project
     and some path matches `receives()`. A portfolio declares no such Project,
     so its selection doesn't change. Update the module docstring.
4. **The decision.** Write `.meta/assertions/decisions/DR-321.yaml` (check
   that it is still the next number). It extends DR-303 and records the
   Project shape over the alternatives: a gate step inside `meta`, which
   every `.meta/` change would pay for, and a step outside `structure.yaml`
   that the loop runs separately, which `.meta/gate` would not see. It also
   says that `just gate` with no argument runs the specialization, as every
   declared Project's gate does. The loop reaches that case only when every
   Project is selected or no structure is asserted. List `enacted_in` and
   re-render.
5. **Tests**, in `pair/test_pair.py` `GateSelectionTest`. The `Bench`
   structure has no specialization Project or bundle, so add a helper that
   commits a structure with `meta`, `pair` (both in a `scaffold` Product),
   `specialization`, and a fourth Project `seed` in no Product whose
   directory is `seed/`, beside a small bundle. The fourth Project matters:
   `select()` returns `None` when the selection is every declared Project,
   so with only `meta`, `pair` and `specialization` declared the positive
   cases would return `None`, not the list they assert. The bundle has a managed `dir`
   (`.meta/checks/`), a managed file (`.meta/bundle.yaml`), a template item
   with a `target`, a `portfolio` dir (`stakeholders/`) and a managed
   `stakeholders/README.md`. Cases:
   - `.meta/checks/x.py`, the template's source path and `.meta/bundle.yaml`
     each select `["meta", "pair", "specialization"]`;
   - `issues/backlog/a.md`, `pair/loop.py`, `.meta/test_specialization.py`
     and `stakeholders/p.md` each select `["meta", "pair"]`, and
     `stakeholders/README.md` brings in `specialization`;
   - with the specialization Project not declared, `.meta/checks/x.py`
     selects `["meta", "pair"]`, as a portfolio's selection would.

   The probe file `.meta/checks/probes/tools/test_specialization.py`
   already exists (it covers fixtures, inheritance and tokens); add a check
   there for the summary line. That file is managed and reaches portfolios,
   where `.meta/test_specialization.py` is absent, so the new check skips
   the same way its neighbours do. Given a step that fails, `main`'s stdout
   is exactly one `x  specialize (1)` line and its problem line, in A21's
   shape.
6. **The demonstration by hand**, not committed. Add a managed probe under
   `.meta/checks/` that fails unless `pair/loop.py` exists, run the gates
   `touched.select` picks for that change, see `specialization` fail while
   `meta` passes, note the output here, and then remove the probe.

**Risks.**
- **Cost.** A full specialization (bootstrap, render, the portfolio's whole
  gate, then a fresh clone's `meta` gate) runs before landing on every change
  under `.meta/checks/`, `.meta/lib/` and the other managed items, and those
  are common. Making it faster is out of scope; record its wall time in the
  DR once from the demonstration.
- **Over-selection inside managed items.** `SCAFFOLD_ONLY_PATHS` in
  `.meta/lib/bundle/__init__.py` lists paths that lie inside managed items but
  never reach a portfolio (`.meta/lib/adapt`,
  `.meta/checks/probes/tools/test_brownfield.py`). `receives()` does not
  subtract them, because `pair/` cannot import `.meta/lib` and a third copy
  of that list would drift. A change only to one of them runs the
  specialization for nothing. The specialization still passes, so the cost
  is time, not a wrong verdict. Record this in the DR.
- **Concurrency.** `.meta/gate` runs Projects in parallel, so the
  specialization's temporary repository and `uv` runs share the machine with
  the `meta` gate. It writes only under its own temporary directory.
- **Uncommitted files.** `test_specialization.py` copies from the working
  tree, not from `HEAD`. The loop gates a committed worktree, so this only
  matters by hand.

## What was done

The plan held. Where the work departed from it:

- `execute_specialization_test` now returns `(code, step)`, the number of
  the step that failed (0 for loading the inherited paths, before step 1).
  The new `summary(code, step)` turns that into the report. `main` runs
  everything under `contextlib.redirect_stdout(sys.stderr)`, so the step
  narration and the inner gate's `ok …` and `x  …` lines reach stderr
  without touching each `print`. Only `release.py` (through
  `just test-specialization`) and the recipe call it, and both read only the
  exit code.
- The summary-line probe (`_check_report`) swaps in a fake
  `execute_specialization_test` and reads `main`'s stdout with `.meta/gate`'s
  own `OK`, `X` and `PROBLEM` patterns, so the shape it checks is the one
  the runner parses.
- The `meta file sizes` ratchet holds `.meta/test_specialization.py` at its
  baseline. To pay for the summary I cut three `Parameters:`/`Returns:`
  docstrings that restated their signatures, which took the file from 470 to
  469 lines, and lowered the baseline to 119.
- The Project's `name: specialization` broke no probe, so the fallback in
  step 1 was not needed.
- `pair/README.md` now says that the loop selects the specialization
  (DR-321 cites it).
- (secondary, in-progress) `receives()` first keyed template items by their
  `path`, which in the real bundle is the target: it selected the
  specialization for stereorepo's own `AGENTS.md`, `README.md` and
  `.meta/assertions/structure.yaml`, none of which reach a portfolio, and
  missed `template/`. The test's bundle hid this by giving its template item
  a `path` that was the source. `bundled()` now takes a `key`, and
  `receives()` reads `source`, falling back to `path`, as
  `BundleItem.source_path()` does; the test's bundle now has the real shape,
  so its `AGENTS.md` case guards against the regression.

**The demonstration.** On the clean tree, `just gate specialization` passed
in 34 s on this machine:

```
ok specialization/specialize — 9 steps, and the specialized portfolio's gate
ok specialization — 1 steps across 1 project
```

I then added a temporary pre-check `stereorepo only` to
`.meta/checks/probes/tools/gate.py`, which fails unless `pair/loop.py`
exists. `touched.select` gave `['meta', 'pair', 'specialization']` for that
change. `just gate meta specialization` exited 1. `meta` passed here, and the
specialization failed at step 8. On stdout:

```
x  specialization/specialize (1)
     step 8 failed (exit 1); its output is on stderr
x  meta specialization (1)
     specialization: specialize
```

On stderr, from the specialized portfolio's gate:

```
x  meta/stereorepo only (1)
     pair/loop.py is absent
```

The probe was then removed. `gate.py` is as it was on `main`.

## Pair notes

> **primary, backlog turn 1**
>
> The issue was already mostly ready to plan. I left `difficulty: medium` as it was and made four additions after checking what it says against `pair/touched.py`, `.meta/bundle.yaml` and `.meta/test_specialization.py`. They're committed as `87d5f33`.
>
> - **What counts as a change portfolios receive:** this now also includes the source `path` of a template item, which is the file that gets edited, not its `target`. It also includes `.meta/bundle.yaml` itself, which isn't one of its own items but still changes what a portfolio gets.
> - **The cost of running it every time:** if the specialization is declared as a Project, `just gate` with no argument will run it by default. That also happens whenever `select()` returns `None` because a change picks every Project. The Decision Record now has to say whether that's wanted.
> - **Out of scope:** changes under `bootstraps/` are left out, because the seed Projects' own gates already check them.
> - **Done when:** the selection test now also covers template sources and `.meta/bundle.yaml`. It adds a negative case: a `.meta/` path outside every bundle item, such as `.meta/test_specialization.py`, doesn't select the portfolio gate. I checked that the bundle doesn't list that file.

> **secondary, backlog turn 2**
>
> I kept `difficulty: medium` and committed four corrections to the issue as `e2d890a`. I checked it against `pair/touched.py`, `.meta/bundle.yaml` and `.meta/assertions/structure.yaml`.
>
> - **The bundle isn't read here at all.** `placed()` only reads `.meta/bundle.yaml` when there is a Project at the repository root, and stereorepo has none. So the change has to add its own reading of the bundle; it can't extend an existing one.
> - **`.meta/bundle.yaml` lists itself.** My partner's note said it wasn't one of its own items, but the bundle does list it as a managed item. I corrected that in the Wanted section.
> - **A risk in the suggested approach.** Every Project in `structure.yaml` has a directory `name`, and `home()` gives each path to the deepest Project whose directory holds it. If the new specialization Project got a `name` that holds `.meta/` paths, it would take those paths from `meta` instead of being selected alongside it. The issue now warns against that.
> - **Scope and test.** Out of scope now also covers portfolio-owned items (such as `stakeholders/`) and the symlink items, since stereorepo never copies their contents. The selection test now checks that the portfolio gate is picked beside `meta`. It also gains a case that should not select it: a change under `stakeholders/` outside its three managed READMEs.

> **primary, backlog turn 3**
>
> I'm changing nothing this turn. I checked my partner's corrections against `.meta/bundle.yaml` and they hold:
>
> - **The bundle lists itself.** `.meta/bundle.yaml` names itself as a managed item, so my earlier note saying it didn't was wrong, and their fix to the Wanted section is right.
> - **The `stakeholders/` case is right.** The bundle marks `stakeholders/` as portfolio-owned but lists its three READMEs as managed. A change elsewhere under `stakeholders/` shouldn't select the portfolio gate, so that negative test case is correct.
>
> Their other two points also match what I read in `pair/touched.py` last turn. The bundle is only read when a Project sits at the repository root, which stereorepo doesn't have. And a Project whose directory holds `.meta/` paths would take them from `meta`.
>
> The issue now says what is wanted, what is out of scope, and how anyone will know it is done, and `difficulty: medium` still fits.

> **primary, todo turn 1**
>
> I wrote the plan, after reading `pair/touched.py`, `.meta/gate`, the landing gate in `pair/loop.py`, `.meta/test_specialization.py` and the existing `GateSelectionTest`. The plan declares the specialization as its own Project, kept out of every Product so that a change to `meta` alone doesn't pull it in. Two findings shaped it. First, `.meta/gate` treats a Project as failed unless the Project prints a step line in the gate contract's shape on stdout, and `test_specialization.py` prints none. On failure it would also echo the inner portfolio gate's step lines, which the outer runner would misread, so the plan routes all of that to stderr and adds one summary line. Second, a Project needs a `name` that holds no paths, and the plan has the implementer check that no probe expects that name to be an existing directory.

> **primary, todo turn 1**
>
> The plan is written into the issue under `## The plan` and committed as `f6d82cf`; nothing is implemented yet. The approach is to add the specialization as its own Project, `work:project/specialization`, whose gate runs `.meta/test_specialization.py`, and to keep it out of every Product so a change to `meta` alone doesn't bring it in.
>
> Steps, in order:
>
> 1. **Declare the Project** in `.meta/assertions/structure.yaml` with `name: specialization`. No directory has that name, so it holds no paths and `.meta/` stays with `meta`. Then re-render.
> 2. **Make `test_specialization.py` report like every other gate.** `.meta/gate` counts a Project as failed unless it prints at least one step line in the gate contract's shape on stdout, and this script prints none. On failure it would also print the inner portfolio gate's step lines, which the outer gate would misread as its own. So all the script's narration and inner output go to stderr, and it ends with one stdout line, `ok specialize — 9 steps` or `x  specialize (1)`, naming the step that failed.
> 3. **Change the selection in `pair/touched.py`.** A new `receives()` reads the bundle's managed and template source paths, sharing its parsing with `placed()`. `select()` adds the specialization Project when a changed path matches and the Project is declared, so a portfolio's selection doesn't change.
> 4. **Write DR-321**, extending DR-303. It records this shape against the alternatives and says that `just gate` with no argument runs the specialization too.
> 5. **Tests.**
>    - In `GateSelectionTest`, in `pair/test_pair.py`:
>      - Paths inside a managed or template item, and `.meta/bundle.yaml`, select it.
>      - `issues/`, `pair/`, `.meta/test_specialization.py` and `stakeholders/p.md` don't.
>      - A portfolio that doesn't declare the Project keeps its old selection.
>    - A probe checks the new summary line.
> 6. **Demonstrate it once by hand.** Add a temporary managed probe that fails outside stereorepo, show the specialization failing while `meta` passes, note the output in the issue, then remove the probe.
>
> Risks:
>
> - **Name check.** Some probe may expect every Project's `name` to be an existing directory. If one does, that probe is the thing to fix.
> - **Cost.** A full specialization run will gate every change to common paths such as `.meta/checks/` and `.meta/lib/`. Making it faster is out of scope.
> - **Shared machine.** It runs alongside the other gates in parallel.
> - **Working-tree copy.** It copies the working tree rather than the last commit, which only matters when run by hand.

> **secondary, todo turn 2**
>
> I checked my partner's plan against the code and found one fault that would have broken it. I fixed that and added two smaller points to the plan. The rest is sound. Committed as `90b2c7a`.
>
> - **The planned tests would have failed.** The test setup declared only three Projects: `meta`, `pair` and `specialization`. But `select()` in `pair/touched.py` returns `None` whenever every declared Project is selected. So each change that should pull in the specialization would have returned `None`, not the list the test expects. The plan now adds a fourth Project, `seed`, which belongs to no Product, so those cases return a real list.
> - **The probe file already exists.** The plan described the summary-line check as if it went in a new file. `.meta/checks/probes/tools/test_specialization.py` already exists, and it is copied into portfolios, where `.meta/test_specialization.py` is missing. The plan now adds the check to that file and has it skip in a portfolio, as the checks already there do.
> - **Some changes will run the specialization for nothing.** Two paths sit inside items portfolios receive but never reach a portfolio: `.meta/lib/adapt` and `.meta/checks/probes/tools/test_brownfield.py`. A change to only one of them would still trigger the specialization, which then passes. That costs time but never gives a wrong result. Leaving them out would need a third copy of the list of such paths, because `pair/` can't import the existing one from `.meta/lib`. So the plan accepts this and has the Decision Record say so.
>
> I also confirmed that DR-321 is the next free Decision Record number. And `.meta/gate` does reject a Project whose gate prints no line in the standard report format, so the plan is right to make `test_specialization.py` print a one-line summary.

> **primary, todo turn 3**
>
> I'm changing nothing this turn. My partner's three corrections all hold up against the code:
>
> - **The fourth Project in the tests is needed.** `select()` in `pair/touched.py` returns `None` whenever every declared Project is selected. With only `meta`, `pair` and `specialization` declared, each case that should pull in the specialization would get `None` back, not the list the test expects. Adding `seed`, in no Product, fixes that.
> - **The probe file already exists and is copied into portfolios.** `test_specialization_probes()` returns nothing when `.meta/test_specialization.py` is missing, which is the case in a portfolio. The new summary-line check can skip the same way.
> - **Some changes will run the specialization for nothing, and accepting that is right.** `SCAFFOLD_ONLY_PATHS` in `.meta/lib/bundle/__init__.py` lists `.meta/lib/adapt` and `.meta/checks/probes/tools/test_brownfield.py`. Both sit inside managed directories but never reach a portfolio. A change to only one of them still triggers the specialization, which then passes. That costs time but never gives a wrong verdict. Leaving them out would need yet another copy of that list in `pair/`.
>
> The plan stands as committed, ready to implement.

> **primary, in-progress turn 1**
>
> I implemented the plan, and `just gate meta` and `just gate pair` both pass. The specialization is now its own Project with its own gate. `pair/touched.py` selects it when a change touches something a portfolio receives, and DR-321 records the choice. `.meta/test_specialization.py` sends all its narration to stderr and ends with one summary line on stdout. New tests cover the selection, and a new probe checks the summary line. I also showed it working by hand: a temporary check that fails outside stereorepo passed here but failed the specialized portfolio at step 8, which held the run; the output is under "What was done". The run takes 34 s on a clean tree. To stay inside the file-size limit for `.meta/test_specialization.py` I shortened three docstrings that only restated their signatures, and lowered that file's size baseline to match. This branch touches a managed probe file, so the loop will run the specialization on it before landing.

> **primary, in-progress turn 1**
>
> The change is in: a change to anything a portfolio receives now builds a specialized portfolio and runs its gate before it lands. `just gate meta` and `just gate pair` both pass; it's committed as `25c4f7e`.
>
> - **New Project.** `work:project/specialization` in `.meta/assertions/structure.yaml` has `.meta/test_specialization.py` as its gate. It sits in no Product, so a change to `meta` alone doesn't bring it in. Its name matches no directory, and no check objected to that.
> - **Selection.** `pair/touched.py` adds the specialization when a changed path is in an item `.meta/bundle.yaml` marks `managed` (the bundle file itself included) or is the source of a `template` item. Only a tree that declares the Project gets this, so a portfolio's selection is unchanged.
> - **Gate report.** `.meta/test_specialization.py` now sends all its narration, and the inner portfolio gate's output, to stderr. Stdout holds one line in the format `.meta/gate` expects: `ok specialize`, or `x  specialize (1)` plus the step that failed.
> - **Tests.** Two new tests in `GateSelectionTest` in `pair/test_pair.py` cover the paths that should and shouldn't select it, and a portfolio that doesn't declare it. A new check in `.meta/checks/probes/tools/test_specialization.py` reads the summary line with `.meta/gate`'s own patterns.
> - **Records.** DR-321 records the decision; `.meta/decisions.md` and the `gate` recipe's comment were re-rendered, and `pair/README.md` now mentions the specialization.
> - **Shown by hand.** On a clean tree the specialization passed in 34 s. I then added a temporary check that fails wherever `pair/loop.py` is missing, as it is in every portfolio. `meta` passed here, but the specialized portfolio failed at step 8, so the run exited 1. I removed the check afterwards; the output is in the issue file.
>
> **File-size limit.** The additions pushed `.meta/test_specialization.py` over its size ceiling. I shortened three docstrings that only restated their function signatures, which left the file one line shorter than before, and lowered its baseline from 120 to 119.
>
> **On landing.** This branch changes a managed check file, so the loop will run the specialization on it before it lands.

> **secondary, in-progress turn 2**
>
> My partner's implementation had one real bug, which I fixed and committed as `0bf2d5d`. `just gate pair` (227 tests) and `just gate meta` both pass.
>
> **The bug:** the selection looked at the wrong field for template items, so it ran the specialization for the wrong files.
> - In `.meta/bundle.yaml`, a template item's `path` is where the file lands in a portfolio, such as `AGENTS.md`. Its `source`, such as `template/AGENTS.md`, is the file that actually gets copied (that's how `BundleItem.source_path()` in `.meta/lib/bundle` reads it).
> - `receives()` in `pair/touched.py` read `path`. So editing stereorepo's own `AGENTS.md`, `README.md` or `.meta/assertions/structure.yaml` would have run the specialization, though none of them reaches a portfolio. Editing anything under `template/` would not.
> - The test missed it because its sample bundle put the source file under `path`, which the real bundle never does.
>
> **The fix:**
> - `receives()` now reads `source`, falling back to `path` when there is none. `placed()` still reads `path`, as before.
> - The test's sample bundle now has the real `path`/`source`/`target` layout, and its case for a template item's source uses `template/AGENTS.md`. The existing case that an `AGENTS.md` change selects only `meta` and `pair` now catches this bug if it returns.
> - DR-321, the module docstring and the issue's Wanted section and plan now say `source`. The issue's "What was done" section explains the bug for the next reader.
>
> The rest checks out. Every command `.meta/test_specialization.py` runs has its output captured, so moving its narration to stderr can't let a step's output leak onto stdout. The documentation artifacts DR-321 lists all exist in `structure.yaml`. I didn't rerun the specialization itself, because the loop runs it before landing.

> **primary, in-progress turn 3**
>
> My partner's fix is right, and it was my bug. Real template items in `.meta/bundle.yaml` carry `source: template/…`, and `BundleItem.source_path()` reads `source` before `path`, as `receives()` now does. I kept the fix and only rewrapped the lines it had left over 100 characters, in `pair/touched.py`, DR-321 and this issue's Wanted section and plan. I also shortened one constant's docstring of mine that ran to 102. Nothing else changed.

> **primary, in-progress turn 3**
>
> I kept my partner's fix. It was my bug: for template items, the selection read the wrong field of `.meta/bundle.yaml`.
>
> - **The bug.** A template item's `path` is where the file lands in a portfolio (`AGENTS.md`), and its `source` is the file actually copied (`template/AGENTS.md`). My `receives()` read `path`, so editing stereorepo's own `AGENTS.md` would have run the specialization, and editing anything under `template/` would not.
> - **The fix holds.** It now reads `source` and falls back to `path`, matching how `BundleItem.source_path()` in `.meta/lib/bundle` reads the bundle. The test's sample bundle now has the real layout, so the `AGENTS.md` case catches this if it comes back.
>
> My only change was rewrapping lines the fix had left over 100 characters. Those were in `pair/touched.py`, DR-321, and the issue's Wanted section and plan. I also shortened one docstring of my own that ran to 102.
>
> `just gate meta` and `just gate pair` both pass. Committed as `8f41e28`.

> **secondary, in-progress turn 4**
>
> My partner's last turn was only rewrapping long lines, and their changes are fine. It missed two lines in the issue file that were still over 100 characters: one in the Wanted section and one in step 3 of the plan. I rewrapped both and committed that as `7b382b4`.
>
> I didn't change any code. `just gate meta` passes after the rewrap. I didn't run `just gate pair` again because nothing under `pair/` changed. The implementation already matches the plan.

> **primary, in-progress turn 5**
>
> I'm changing nothing this turn. My partner's last commit, `7b382b4`, only rewrapped the two long lines in the issue file that I missed: one in the Wanted section and one in step 3 of the plan. Those are fine. The code already matches the plan, and `just gate meta` and `just gate pair` both passed after the last code change.
