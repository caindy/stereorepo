---
difficulty: medium
---

# Audit a brownfield product against its language's bootstrap

DR-312 makes a bootstrap a reference and an audit for a product that already
exists: the audit compares the product with the reference, and each gap it
finds becomes an Issue in the backlog. Nothing does that yet; DR-312's second
consequence says so. `.meta/adapt.py` plans how stereorepo is installed into
an existing repository, and `.meta/bootstrap.py` makes a new Project from a
bootstrap. Neither looks at an existing product's own build and gate.

## What the reference already says

The reference is machine-readable today. Each bootstrap in
`.meta/assertions/bootstraps.yaml` lists its `discipline_implementations`,
and each implemented Discipline names the gate steps that hold it in
`held_by` (the Python standard: `doc`, `test`, `orphans`, `lints`, `ruff`,
`types`, `mutants`, `evidence`, `render`). A Discipline marked `exempt`
carries its `exemption_reason` and asks nothing of the Project. The gate
contract (Article 21, DR-092) is the report shape `.meta/gate` already parses
with its `OK`, `X`, `COULD_NOT` and `PROBLEM` patterns: `ok <step>` with an
optional ` — <scope>`, `x  <step> (<count>)` followed by five-space-indented
problem lines, and `?  <step>: <why>`.

## Wanted

A recipe, `just audit <project> <bootstrap>` (atomic identifiers only,
DR-349), that runs the named Project's gate as
`.meta/assertions/structure.yaml` declares it, reads its standard output,
and compares it with the named bootstrap. The line shapes come from
`.meta/gate`'s patterns, not from a second copy of them. A step counts as
reported whatever its mark (`ok`, `x` or `?`); the audit is not the gate and
does not judge outcomes. A gap is any of:

- a line of standard output that is not in the contract's shape (a problem
  line under an `x` report is in shape), or a gate that reports no step at
  all;
- a step that the `held_by` list of some implemented Discipline names and the gate
  does not report. One missing step is one gap, naming every Discipline it
  leaves unheld (`orphans` holds both Literate Programming and Nothing
  Unconsumed).

The audit prints each gap as the text of an Issue file (a `# ` title naming
the gap, then what is missing and which Discipline it serves), separated so
the developer can cut each into `issues/backlog/`. It exits 0 with no gap and
non-zero with one. A Project or bootstrap name that is not asserted ends the
audit non-zero, naming the ones that are; so does a Project with no `gate`
asserted. A bootstrap is named by the last segment of its id
(`work:bootstrap/python` is `python`), as a Project is. The comparison takes
the Project and bootstrap records as arguments rather than reading
`structure.yaml` itself, so a probe can hand it a stub Project without
touching the assertions. Record the recipe's shape in a
Decision Record that builds on DR-312, and cite it in the recipe's comment.

## Out of scope

- Writing the Issue files itself; it prints them.
- Judging whether a reported step does what the bootstrap's step does, or
  whether it passes. The audit compares step names and report shape, nothing
  deeper.
- Steps the gate reports that no `held_by` names; they are not gaps.
- Fixing any gap it finds, in any product.

## Done when

A probe beside the other tool probes (`.meta/checks/probes/tools/audit.py`)
loads the audit the way `gate.py` there loads `.meta/gate`, hands it the
real Python bootstrap record and a stub Project record whose `gate` command
prints fixed lines, and shows:

- a stub printing every step of the Python standard's `held_by` lists finds
  no gap and exits 0, even when one of those steps reports `x` with problem
  lines or `?`;
- the same stub without `mutants` reports exactly one gap, naming `mutants`
  and Observed Failure, and exits non-zero;
- the same stub without `orphans` reports exactly one gap naming both
  Literate Programming and Nothing Unconsumed;
- a stub that prints a line in no contract shape reports that line as a gap;
- a stub that prints nothing reports that no step was reported.

Run once by hand, on a machine where every python-seed step can run,
`just audit python-seed python` reports the reference's own two departures
and nothing else; the run's output is noted below.

- `render`, which the Python standard's Seeded Artifacts names in `held_by`
  and python-seed's gate has no step for (its `STEPS` end at `mutants`; the
  Rust seed's xtask has no `render` either):
  `issues/backlog/bootstrap-render-step.md`.
- The lines ruff, mypy, pytest and mutmut print on the gate's standard
  output, which the plan did not foresee: `issues/backlog/python-seed-gate-stdout.md`.

### The hand run (2026-10-03)

`just audit python-seed python` exited 1 and printed two Issues:

```
<!-- issues/backlog/python-seed-gate-render.md -->
# Add a `render` step to python-seed's gate

The Python standard holds Seeded Artifacts with a gate step named `render`,
and python-seed's gate does not report one. Add the step, or record why
python-seed holds Seeded Artifacts another way (DR-312).

<!-- issues/backlog/python-seed-gate-report-shape.md -->
# Bring python-seed's gate output into Article 21's shapes

python-seed's gate printed 100 lines on standard output in none of
Article 21's shapes (DR-092) …

    All checks passed!
    Success: no issues found in 2 source files
    ============================= test session starts ==============================
    …
    ⠋ Generating mutants
```

Every step the Python standard asks for other than `render` was reported, so
no other gap. The run was taken before the quote was capped at ten lines;
the 100 lines were pytest banners and mutmut spinner frames.

## The plan

**Where it lives.** A new script `.meta/audit.py`, with the same `uvx
--python 3.13 --with pyyaml` shebang as `.meta/gate`. It loads `.meta/gate`
as a module through `importlib`'s `SourceFileLoader` (the file has no `.py`,
and its `main()` sits under `__main__`), and takes `OK`, `X`, `COULD_NOT`,
`PROBLEM`, `structure()`, `short()` and `ROOT` from it. It does not reuse
`gate.run()`, which re-prefixes step names and sends unshaped lines to
standard error, and the audit needs those lines. It is scaffold-only (see
below: the plan first said otherwise, and was wrong).

**Seams, in `.meta/audit.py`.**

- `reported(lines) -> tuple[set[str], list[str]]`: the step names in any of
  the three shapes, and the lines in none. A `PROBLEM` line counts as shaped
  only directly under an `x` report or another problem line, as in
  `gate.run()`. A blank line is neither.
- `held(bootstrap) -> dict[str, list[str]]`: each step named in the
  `held_by` list of an `implemented` Discipline, mapped to the Disciplines it
  holds, in declared order. `exempt` Disciplines contribute nothing.
- `gaps(project, bootstrap, lines) -> list[Gap]`: one gap per held step not
  reported; one gap holding every unshaped line together (a gate that writes
  thirty stray lines wants one Issue, not thirty); one gap if no step was
  reported at all. A frozen `Gap` dataclass carries a slug, a title and a body.
- `issue(gap) -> str`: the Issue text. Each gap is printed preceded by a
  comment line naming the file it would be, `<!-- issues/backlog/<slug>.md
  -->`, so the developer can cut them apart. Slugs: `<project>-gate-<step>`
  for a missing step, `<project>-gate-report-shape` for unshaped lines,
  `<project>-gate-reports-nothing` for no step. The body names the
  Disciplines by their record name (`work:discipline/observed-failure` reads
  as Observed Failure via `.meta/assertions/imported/disciplines.yaml`, or failing that the title-cased
  last segment) and cites DR-312 and the new DR.
- `audit(project, bootstrap, out=sys.stdout) -> int`: runs `project["gate"]`
  with `shell=True, cwd=ROOT`, standard output captured and standard error
  passed through, then prints the gaps to `out` and returns 1 if there are
  any, else 0. The gate's own exit code is not consulted.
- `main(argv)`: exactly two arguments; resolves the Project through
  `gate.structure()` and the bootstrap from `.meta/assertions/bootstraps.yaml`,
  both by `short()` of the id; an unknown name, or a Project with no `gate`,
  exits non-zero through `sys.exit` naming what is asserted.

**Steps, in order.**

1. Write `.meta/audit.py` with docstrings carrying the doctests for
   `reported` and `held` on literal input.
2. Write the probe `.meta/checks/probes/tools/audit.py`, one `@check` in the
   form of `tools/gate.py`, but `load_module(META / "audit.py")` with the
   default `register=True`: the frozen `Gap` dataclass needs its module in
   `sys.modules` while it is built (`harness/loaders.py` says so),
   the Python bootstrap read from `bootstraps.yaml`, a stub Project
   `{"id": "work:project/stub", "gate": "printf '%s\n' …"}` per case, `audit`
   called with a `StringIO`. Import it in `tools/__init__.py` after `gate`,
   and name it in that module's docstring, which lists every probe.
3. The recipe: add `audit` to `.meta/lib/render/writers.py` beside
   `bootstrap`, unconditionally, as
   `audit project bootstrap:` / `    .meta/audit.py {{project}} {{bootstrap}}`
   (so `.meta/audit.py` is committed executable, mode 755, as `.meta/gate` is)
   with a comment citing the new DR; declare it in `CONTRACT` in
   `.meta/checks/files/justfile.py` as
   `(("project", IDENTIFIER), ("bootstrap", IDENTIFIER))`.
4. `.meta/assertions/structure.yaml`: artifacts `work:artifact/meta-audit`
   and `work:artifact/meta-checks-probes-tools-audit`.
5. The Decision Record, DR-353 unless a higher one has landed: the audit
   compares step names and report shape only, prints rather than writes
   Issues, one gap per missing step and one for all stray lines. Builds on
   DR-312, `enacted_in` the two new artifacts and `work:artifact/justfile`.
6. `just render`, which regenerates `justfile` and `.meta/decisions.md`.
7. The hand run, noted here.

**Tests.** The five probe cases under Done when, plus the doctests in step 1.

**Where the work departed from the plan.**

- No doctests: nothing runs doctests in `.meta/` scripts, so an example in a
  docstring would be checked by nobody. Every case lives in the probe, which
  gained a sixth: twelve stray lines quote ten and say `… and 2 more`.
- `.meta/gate` reads `__file__` at its top level, so `.meta/audit.py` builds
  its spec with `spec_from_loader`, which sets the origin, rather than a bare
  `ModuleSpec`.
- A gate that reports no step yields only the reports-nothing gap, not one
  more gap for every held step it therefore misses.
- An Issue quotes at most `QUOTED` (ten) stray lines, after the hand run
  showed a hundred.
- The slot-citation check reads a Discipline's possessive followed by a
  backticked `held_by` as a claim that the slot sits on the `Discipline`
  class, where it sits on the implementation; the prose says "the `held_by`
  list of an implemented Discipline" instead.
- `main` takes the asserted Projects as an optional argument, read from
  `structure.yaml` when omitted, so the probe can hand it a Project with no
  gate; every asserted Project has one, so that refusal was otherwise
  untestable.

- **Scaffold-only, not shipped.** A specialized portfolio holds no
  `bootstraps.yaml`; the bootstrap records stay in stereorepo, and only the
  seed's files travel. The probe failed the specialization gate there. So
  `.meta/audit.py` and its probe join `.meta/adapt.py` on the scaffold-only
  lists (`SCAFFOLD_ONLY` in `.meta/checks/files/scaffold.py`,
  `SCAFFOLD_ONLY_PATHS` in `.meta/lib/bundle/__init__.py`), `audit` joins
  `SCAFFOLD_RECIPES`, the recipe renders only where `work:artifact/meta-audit`
  is asserted, and `tools/__init__.py` imports both scaffold-only probes in
  one loop where present. That loop dropped one `F401` suppression, and the
  plain import of `release` now carries the one the import group needs. The
  audit's printed Issues cite "stereorepo's DR-nnn", since they land in other
  repositories. Auditing a product that lives in another repository is
  `issues/backlog/audit-another-repository.md`.

**Risks.**

- python-seed's `closing_block` deliberately prints a blank line, a `?  steps
  that could not run (n) — …` line with no colon, and two-space-indented
  lines when any step could not run. Under the rule above those are a
  report-shape gap. That is a true reading of Article 21, but it means the
  hand run is only clean where every tool is installed; if it is not, the
  noted output says so rather than the rule bending.
- `.meta/gate` loaded as a module runs its top level, which imports `yaml`
  and reads nothing else; the shebang supplies `pyyaml`, so loading is safe.
- `printf` in the stub runs under `/bin/sh`; quote with `shlex.quote` per
  line so `?` and `—` survive.
- The file-size and comment baselines may need the new files recorded;
  `just render` and the probe step will say so.

## Pair notes

> **primary, backlog turn 1**
>
> I groomed `issues/underway/bootstrap-audit.md`, kept `difficulty: medium`, and committed it as `ff319725`.
>
> The issue was already close to plannable. I checked it against the code and made these changes:
>
> - **Gate output format:** the issue listed only part of what a gate prints. `.meta/gate` also accepts an optional ` — <scope>` after `ok` lines and indented problem lines under an `x` line. The audit now has to reuse the patterns `.meta/gate` already has (`OK`, `X`, `COULD_NOT`, `PROBLEM`) rather than write its own. Without that, every failing step's problem lines would be reported as gaps.
> - **What counts as reported:** a step counts whether it is marked `ok`, `x` or `?`. Whether it passes is the gate's job, not the audit's. Steps that no Discipline lists are not gaps.
> - **Steps shared by two Disciplines:** `orphans` holds both Literate Programming and Nothing Unconsumed. A missing step is now one gap that names every Discipline it leaves unheld.
> - **Unknown names:** if the Project or bootstrap name isn't declared, the audit stops with a non-zero exit and lists the names that are.
> - **Where the tests go:** tests for `.meta` tools live as probes under `.meta/checks/probes/tools/`, so the test is now `.meta/checks/probes/tools/audit.py`. I added three cases: a step reporting `x` or `?` still counts as present, removing `orphans` gives one gap naming both Disciplines, and a stub that prints nothing reports that no step was reported.
> - **The hand check:** the manual run is now spelled out as `just audit python-seed python`.
>
> I didn't split the issue, because it is one recipe, one script, one probe and one Decision Record.

> **secondary, backlog turn 2**
>
> I checked my partner's grooming of `issues/underway/bootstrap-audit.md` against the code, and it holds up. The gate's line patterns in `.meta/gate`, the `held_by` lists in `bootstraps.yaml`, the gate commands in `structure.yaml` and the probe location are all as the issue describes them. I kept `difficulty: medium` and didn't split it.
>
> I closed three gaps that would have stalled planning, and committed them as `75bd7cd5`:
>
> - **A Project with no gate:** if the named Project has no `gate` declared, the audit now stops with a non-zero exit, the same as an unknown name.
> - **Bootstrap names:** a bootstrap is named by the last part of its id, so `work:bootstrap/python` is `python`. That is how `just audit python-seed python` resolves.
> - **How the probe gets a stub Project:** Projects are read from `structure.yaml`, so the issue's "temporary Project" had no way in. The comparison now takes the Project and bootstrap records as arguments. The probe loads the audit the way `.meta/checks/probes/tools/gate.py` loads `.meta/gate`, then passes the real Python bootstrap record and a stub Project whose gate command prints fixed lines. Nothing in the declared Projects has to change.

> **primary, backlog turn 3**
>
> I'm leaving the issue as it is: my partner's three additions check out against the code, so it stays at `difficulty: medium`, unsplit.
>
> - **A Project with no gate:** `.meta/gate` already treats this as its own case, printing `?  <name>: no gate asserted` instead of running anything. Having the audit stop with a non-zero exit there is the right parallel.
> - **Bootstrap names:** naming a bootstrap by the last part of its id matches how `.meta/gate` names Projects. `work:bootstrap/python` becomes `python`, which is what `just audit python-seed python` needs.
> - **How the probe gets a stub Project:** passing the Project and bootstrap records in as arguments is what lets the probe supply a fake gate. `.meta/checks/probes/tools/gate.py` already loads `.meta/gate` this way through `load_module`, so the pattern exists.

> **primary, todo turn 1**
>
> I wrote the plan into `issues/todo/bootstrap-audit.md` under `## The plan` and committed it as `36f949d1`. Reading the code showed that the issue's manual check can't pass as written, so I changed it.
>
> **The manual check was wrong.** The Python standard says the `render` step holds Seeded Artifacts. Neither bootstrap's own gate has a `render` step: python-seed's steps run from `lints` to `mutants`, and the Rust seed's xtask has none either. Run against python-seed, the audit will rightly report a `render` gap. The issue now expects exactly that one gap. I filed the mismatch itself as `issues/backlog/bootstrap-render-step.md`, set to wait on this issue. It asks the developer to choose: add the step to both seeds, or change or exempt the Discipline.
>
> **The plan:**
> - **Script:** a new `.meta/audit.py` loads `.meta/gate` as a module to reuse its line patterns, `structure()` and `short()`. It does not reuse `gate.run()`, because that sends badly formatted lines to standard error, and those lines are what the audit needs to see.
> - **Functions:** `reported` (which steps the gate reported, and which lines are out of format), `held` (which steps the bootstrap expects, and which Disciplines each holds), `gaps`, `issue`, `audit` (takes the Project and bootstrap records, returns the exit code) and `main` (resolves the names).
> - **Badly formatted lines:** all of them together make one gap, not one gap each, so a noisy gate produces one Issue instead of thirty.
> - **Printed output:** each gap is preceded by a comment naming the backlog file it would become, so the developer can cut them apart.
> - **Order:** the script with doctests, then the probe `.meta/checks/probes/tools/audit.py` (registered after the gate probe), then the recipe.
>   - The recipe is added to `.meta/lib/render/writers.py`, which generates the `justfile`, and to the recipe contract in `.meta/checks/files/justfile.py` as two identifier arguments.
>   - Then the two new files are declared in `.meta/assertions/structure.yaml`, followed by a new Decision Record (DR-353, building on DR-312), `just render`, and the manual run.
>
> **Main risk:** when any of python-seed's checks can't run (for example, because a tool isn't installed), its gate prints a closing summary on standard output that doesn't follow the gate report format, on purpose. The audit would report that summary as a gap. The plan keeps the strict rule. So the manual run is only clean on a machine where every python-seed check can run, and if it isn't, the recorded output will show that.

> **secondary, todo turn 2**
>
> I checked my partner's plan in `issues/todo/bootstrap-audit.md` against the code, and most of it holds up. A few claims I confirmed:
>
> - **The `render` step:** neither seed's gate has a `render` step, so the backlog Issue `issues/backlog/bootstrap-render-step.md` is justified.
> - **python-seed's closing lines:** python-seed's gate deliberately prints closing lines outside the report shape when a step can't run, as the plan's main risk says.
> - **Discipline names:** `disciplines.yaml` gives the display names, for example Observed Failure.
> - **Decision Record number:** DR-352 is the latest, so the new record is DR-353.
> - **The audit ships to portfolios:** `.meta/audit.py` isn't on the scaffold-only list.
>
> I made three corrections in the plan's steps and committed them as `b37fee68`:
>
> - **Loading the module:** the plan had the probe load `audit.py` with `register=False`. The audit defines a frozen `Gap` dataclass, and `harness/loaders.py` says a module defining a dataclass has to be registered while it loads. The plan now uses the default, `register=True`.
> - **Listing the probe:** the docstring of `tools/__init__.py` lists every probe, so the plan now says to add the new one there as well as importing it.
> - **Executable bit:** the recipe calls `.meta/audit.py` directly, as the `gate` recipe calls `.meta/gate`. The plan now says to commit the script as executable (mode 755), as `.meta/gate` is.

> **primary, todo turn 3**
>
> I'm leaving the plan as it is: I checked my partner's three corrections against the code and all of them hold.
>
> - **Loading the module:** `.meta/checks/probes/harness/loaders.py` says a module that defines a dataclass has to be registered in `sys.modules` while it loads. The audit's frozen `Gap` dataclass is one, so the probe needs the default `register=True`. No standard-library module is called `audit`, so registering under that name collides with nothing.
> - **Listing the probe:** the docstring of `.meta/checks/probes/tools/__init__.py` names each tool its probes cover. The new audit probe belongs in that list as well as in the imports.
> - **Executable bit:** `.meta/gate` and `.meta/adapt.py` are both committed executable (mode 755), and their recipes call them directly. The `audit` recipe will call `.meta/audit.py` the same way, so it needs the same mode.

> **primary, in-progress turn 1**
>
> `just audit <project> <bootstrap>` now exists, and `just gate meta` passes. The manual run on python-seed found one more gap than the plan expected: the bootstrap's own gate prints tool output where only step reports belong. Everything is committed as `382e828d`.
>
> **What was added:**
> - **`.meta/audit.py`** runs the named Project's gate and reads what it prints. It reuses `.meta/gate`'s report patterns rather than keeping its own copy.
>   - A step counts as reported whether it passed, failed or couldn't run.
>   - Each missing step is one gap naming every Discipline it leaves unheld.
>   - All lines outside the report format make one gap together, and the Issue quotes at most ten of them.
>   - A gate that reports no step at all is a single gap.
>   - Each gap is printed as Issue text, headed by a comment naming the backlog file it would become. The audit exits 1 if it finds any gap.
> - **The probe** `.meta/checks/probes/tools/audit.py` runs the audit against stub gates and the real Python standard record. It covers the five cases the issue asks for, plus a sixth for the ten-line cap; all pass.
> - **The rest:** the `audit` recipe (in `.meta/lib/render/writers.py` and the recipe contract), both new files declared in `structure.yaml`, the probe added to the probe package's docstring, DR-353 building on DR-312, and a re-render.
>
> **The manual run:** `just audit python-seed python` exited 1 with two gaps.
> - **`render`:** both bootstraps name a `render` step and neither seed's gate has one. That was expected and is already filed as `issues/backlog/bootstrap-render-step.md`.
> - **Output format:** python-seed's gate lets ruff, mypy, pytest and mutmut print straight to its standard output, 100 lines on this run. This is a real departure in the reference, so I filed it as `issues/backlog/python-seed-gate-stdout.md` rather than loosening the rule. It is also why I added the ten-line cap.
>
> **Where I departed from the plan,** all recorded in the issue file:
> - There are no doctests, because nothing runs doctests in `.meta/` scripts; every case lives in the probe instead.
> - `.meta/gate` is loaded with a spec that records its file path, because the gate reads its own path when it loads.
> - A gate that reports nothing gets only the one gap, not an extra gap for every step it therefore misses.
> - Some prose in the issue file had to be reworded because the slot-citation check misread a Discipline in the possessive followed by the backticked slot name.
>
> I left DR-312's line saying the audit "is not built yet" as it is, since earlier Decision Records keep what they said at the time. DR-353's context records that it is now built.

> **secondary, in-progress turn 2**
>
> The implementation matches the plan and Done when. I checked `just audit` by hand with an unknown Project and an unknown Bootstrap: each exits 1 and names what is asserted. I changed three things:
>
> - **Probe for name resolution:** nothing tested `main`'s refusals, so the probe now puts an unknown Project and an unknown Bootstrap to it and checks that the exit message names the refused name and an asserted one. It names only `meta` and `python`, which a specialized portfolio still asserts; `python-seed` would not be there, because `bootstraps/` is scaffold-only. The no-gate refusal is still untested, because no asserted Project lacks a gate and `main` reads the real `structure.yaml`.
> - **Usage first:** `main` checks its argument count before it reads any assertions.
> - **The meta gate:** the Pair note above quoted the possessive form the slot-citation check rejects, which failed `cited schema slots`. It is reworded, and `just gate meta` now passes.

> **secondary, in-progress turn 2**
>
> `just audit` works, and `just gate meta` passes. It had been failing on a sentence in my partner's note in the issue file, which I reworded. I committed my changes as `e015336a`.
>
> My partner's implementation matches the plan and the issue's done-when list. When I gave it a Project or bootstrap name that isn't declared, it exited non-zero and listed the names that are. I changed three things:
>
> - **Gate failure in the issue file:** my partner's note quoted a Discipline in the possessive followed by the backticked slot name, and the check that reads `held_by` citations takes that wording to mean a field on Disciplines themselves, so it failed. I reworded the note.
> - **Probe cases for unknown names:** nothing tested how the audit handles names that aren't declared. The probe now passes it an unknown Project and an unknown bootstrap, and checks that the error names both the rejected name and a declared one. It expects only `meta` and `python`, because a portfolio built from this repository still declares those but not `python-seed`, so naming `python-seed` would break the probe there.
> - **Argument check first:** the audit now checks it was given exactly two names before it reads any files.
>
> One case is still untested: a Project with no gate declared. Every declared Project has one, and the audit only looks names up in the real list, so the probe has no way to produce that case.
>
> The first new probe version tripped the line-length and type checks; I fixed both before committing. The issue file has a note for the next reader covering these changes.

> **primary, in-progress turn 3**
>
> I kept my partner's changes and closed the one case they had left untested: the audit refusing a Project that has no gate. `just gate meta` passes, and everything is committed as `e9d9a4d0`.
>
> - **The no-gate case:** `main` in `.meta/audit.py` can now be handed the list of declared Projects; it reads `structure.yaml` only when none is given. The probe hands it a stub Project with no gate and checks that the error message names it and says it has no gate. Before this, the case couldn't be tested, because every declared Project has a gate.
> - **The meta gate again:** it was failing on the issue file once more. The second copy of my partner's in-progress note quoted the same possessive wording that the citation check rejects. I reworded it.
> - **The issue file:** the "Where the work departed from the plan" list now includes the new parameter on `main`.
>
> Only `.meta/` and the issue file changed, so no other Project's gate applies.

> **secondary, in-progress turn 4**
>
> My partner's no-gate probe case and the `projects` argument on `main` check out. `just gate meta` was failing again for the same reason as before: the latest note quoted the rejected possessive wording while describing the fix for it. I reworded that note and joined the new departure item to the list above it. `just gate meta` now passes. A note that needs to mention that wording should describe it, not quote it.

> **secondary, in-progress turn 4**
>
> Your partner's code changes are good, but `just gate meta` was failing again on the issue file. It passes now that I've fixed that, and the fix is committed as `4b10bbf4`.
>
> - **What I checked:** `main` in `.meta/audit.py` now accepts the list of declared Projects as an optional argument, so the probe can pass it a Project with no gate. That covers the last untested refusal, and both changes are fine.
> - **Why the gate failed:** your partner's new note described the earlier gate failure by quoting the same wording that caused it. The check that reads citations of `held_by` treats a Discipline in the possessive followed by `held_by` as a claim that Disciplines carry that field. This is the third time a note has tripped it.
> - **What I changed:** I reworded the note to describe the wording rather than quote it. I also removed a stray blank line that split the "Where the work departed from the plan" list in two. My note in the issue file warns the next reader not to quote that wording.
>
> Only `.meta/` and the issue file have changed, so no other Project's gate applies.

> **primary, in-progress turn 5**
>
> I'm changing nothing this turn: my partner's fix is correct, and the implementation matches the plan and the done-when list.
>
> My last turn's gate run passed, but my turn summary is added to the issue file after my turn ends. That summary quoted the same wording the citation check rejects, so the gate failed again. My partner reworded it and joined the list that a blank line had split; both edits are right. From here, any note that needs to mention that wording will describe it rather than quote it.

> **primary, in-progress turn 6**
>
> The specialization gate failed because the plan was wrong: a specialized portfolio holds no bootstrap records, so the audit can't work there. I made the audit scaffold-only, like the adoption tool, and `just gate meta specialization` now passes. I didn't run `just gate pair` because nothing under `pair/` changed. Committed as `722c32d7`.
>
> **What broke:** the audit's probe ships to every portfolio, but `.meta/audit.py` was missing from the shipped files. Once I added it, the real problem showed: `.meta/assertions/bootstraps.yaml` stays in stereorepo, and only the seed's files reach a portfolio. The plan had assumed portfolios hold both. The audit's printed Issues also cited bare `DR-312`, which a portfolio's citation check rejects.
>
> **What I changed:**
> - **Kept out of portfolios:** `.meta/audit.py` and its probe are now on both scaffold-only lists (in `.meta/checks/files/scaffold.py` and `.meta/lib/bundle/__init__.py`). I reverted the line I had briefly added to `.meta/bundle.yaml`.
> - **Recipe:** `audit` is now a scaffold-only recipe and is only rendered into the `justfile` where the audit script is declared. Inside stereorepo, `just audit` works as before.
> - **Probe loading:** `.meta/checks/probes/tools/__init__.py` now imports the two scaffold-only probes in one loop, only where they exist. That leaves the count of "registers check steps" suppressions at its baseline.
> - **Citations:** everything in `.meta/audit.py`, including the Issue text it prints, now cites "stereorepo's DR-nnn", because those Issues land in other repositories. I also removed one more instance of the possessive wording the citation check rejects, in a docstring.
> - **Records:** DR-353 gains a consequence saying the audit is scaffold-only and audits the Projects stereorepo declares. The issue file corrects the plan's wrong premise and lists this under where the work departed from the plan.
>
> **New backlog issue:** `issues/backlog/audit-another-repository.md`. DR-312's audit is meant for a brownfield product, which lives in its own repository, and today's audit can only reach Projects stereorepo itself declares. The issue asks for the audit to take a target repository, the way `just adapt plan <repository>` does.

> **secondary, in-progress turn 7**
>
> I'm changing nothing this turn. Your partner's fix is correct, and `just gate meta` passes with the issue file as it stands.
>
> - **Why the plan was wrong:** a portfolio built from this repository doesn't get `.meta/assertions/bootstraps.yaml`, so the audit has nothing to compare against there. Your partner made the audit, its probe and its `audit` recipe stereorepo-only, the same way the adoption tool already is.
> - **What I checked:** `just audit` still runs here. Given an unknown bootstrap name, it exits non-zero and lists `python` and `rust`.
> - **Follow-up work:** auditing a product that lives in another repository is filed separately as `issues/backlog/audit-another-repository.md`.
>
> Only `.meta/` and the issue files changed, so no other Project's gate applies.
