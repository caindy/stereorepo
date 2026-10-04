---
difficulty: medium
---
# python-seed's tests pass when its wheel names a package that is not there

Found while implementing `seed-rendered-gate-lost`. With the
`'packages = ["src/seed"]'` entry dropped from `RENAMES` in
`bootstraps/python/render`, the rendered copy's
`packages/acme/pyproject.toml` tells hatch to package `src/seed`, which no
longer exists. The `python-seed` gate still reported `ok` for `test`, `types`
and `mutants`; only `evidence` reported
`?  python-seed/evidence: pytest --collect-only in acme exited with 2`, and the
gate exited 0. The pair loop holds a landing on any `?`, so the fault would
reach the developer, but as a step that could not run rather than a failure.

A portfolio built from such a render would ship a wheel without its package.

## Why the steps pass

Read from the code in `bootstraps/python/seed/gate/src/gate/__init__.py`.
The broken render was not re-run while grooming.

- `test` runs `pytest --doctest-modules … src tests README.md` in each
  package. Collecting `src` as doctest modules under pytest's default
  `prepend` import mode puts `src/` on `sys.path`, so `import acme` resolves
  from the tree whatever the wheel's `packages` says. `evidence` runs
  `pytest --collect-only` with no paths, so only `testpaths = ["tests"]` is
  collected, nothing puts `src/` on the path, and the import fails with exit 2.
  That exit 2 shows the editable install does not expose `acme`, so the
  editable install is not the cause.
- `types` hands mypy the source and test directories by path, so it never
  consults the install.
- `mutants` runs mutmut on its own copy of `src`, which it puts on the path.

## What is wanted

The seed's gate fails a step, reporting `✗` rather than `?`, when a member
package's `[tool.hatch.build.targets.wheel] packages` names a directory that
does not exist. The check reads the manifests and the tree; it runs no tool.
It is a new pure step (call it `wheel`) placed with the other pure steps
under the `# --- pure steps` banner and listed in `STEPS` before `ruff`, so it
reports before any tool is paid for. It walks the packages that `packages` in
`gate/__init__.py` already finds (the seed member and the gate itself, with
`mutants/` copies skipped), and for each one whose manifest has that table it
reports:

- each `packages` entry that is not a directory under the package,
- each entry that is a directory but has no `__init__.py`, and
- each importable directory directly under `src/` (one with an
  `__init__.py`) that no entry names, so the wheel would leave it out.

Settled while grooming: the gate does **not** build and import a wheel.
Building one means fetching hatchling into an isolated build environment,
which is slow and needs the network that a seat's sandbox does not give it.
The manifest check finds the same fault with neither. Record this as a DR
and enact it in the gate's `README.md` step table.

## Out of scope

- Changing `test`'s import mode (for example `--import-mode=importlib`) so
  that tests run against the install. That would change what every portfolio's
  tests import, which is wider than this fault. If it is wanted, write it as a
  separate backlog Issue.
- `evidence` still reporting `?` alongside the new `✗`.
- The Rust seed. Cargo has no counterpart to this setting.

## Done when

- A probe in `bootstraps/python/seed/gate/tests/test_probes.py` builds a tree
  whose member manifest names `src/seed` while only `src/acme` exists, and
  shows the step returns `Found` naming that entry and the unpackaged
  `src/acme`.
- A probe shows a named directory without `__init__.py` is `Found`.
- A probe shows the seed's own layout (`packages = ["src/seed"]` with
  `src/seed/__init__.py`) and a member with no hatch wheel table both pass.
- `uv run gate wheel` in `bootstraps/python/seed` reports `ok` on the
  unbroken seed, which checks both `packages/seed` and `gate`.
- With the `packages` entry removed from `RENAMES` again, gating the rendered
  copy reports the new step as `✗` and exits non-zero. Check this by hand
  once and do not commit the broken `RENAMES`.
- The gate `README.md` step table has a row for the check, and the DR is
  written and rendered.

## The plan

All paths below are under `bootstraps/python/` unless they start with
`.meta/`.

1. **Probes first** (`seed/gate/tests/test_probes.py`). Import `wheel`
   from `gate` and add the three probes listed under "Done when". Each one
   writes a hatch table into `packages/probe/pyproject.toml` using
   `Tree.write`. The default `PACKAGE_MANIFEST` has no hatch table, which
   already gives the "no table passes" case, so the existing probes are
   unaffected. Write one probe that ends in a pass after the fix, so that
   each check is seen to fail and then pass, as the module docstring
   requires. Run them and watch them fail on the missing import.
2. **The step** (`seed/gate/src/gate/__init__.py`, under the
   `# --- pure steps` banner, next to `orphans`):
   - `wheel(root) -> Outcome` loops over `packages(root)`. Two helpers do
     the work for one member, which keeps `wheel` within the limits of 12
     branches and complexity 12. `wheel_entries(manifest)` reads the
     entries, and `unpackaged(root, package, named)` compares them with
     the tree. (The plan first had one helper doing both. The
     implementation split it so the counts in the `Passed` scope come
     from `wheel` itself.)
   - `wheel_entries` parses the manifest with `tomllib`. It returns `None`
     when the manifest does not parse, because `lints` runs first and
     already reports that.
   - It reads `tool.hatch.build.targets.wheel.packages`. `tomllib` gives
     back untyped data, so narrow it with `isinstance` checks, which
     mypy strict needs.
   - It reports each entry whose `package / entry` is not a directory, and
     each entry that is a directory without `__init__.py`.
   - It reports each `src/*/__init__.py` whose parent directory no entry
     names.
   - Problems are written as `relative(root, manifest): …`, and the
     `Passed` scope counts what was checked, for example
     `N wheel packages under M manifests, each present and importable` (A7).
   - Add the step to `STEPS` between `comments` and `ruff`.
   - The `doc` and `comments` steps also hold this code: a docstring on
     every function, and no commentary inside function bodies.
3. **Which Discipline holds it.** The step goes under Nothing Unconsumed:
   a source package the wheel does not ship is code nothing uses.
   - Add `wheel` to the `held_by` of the Python Bootstrap's Nothing
     Unconsumed implementation in `.meta/assertions/bootstraps.yaml`.
   - Add a `uv run gate wheel` paragraph to `nothing-unconsumed.md`,
     after the `orphans` paragraph.
   - Add a `wheel` row to the step table in `seed/gate/README.md`, and add
     `wheel` to the list of pure steps under that table.
   - Add `"ok wheel"` to `FULL` in `.meta/checks/probes/tools/audit.py`.
     `FULL` is the stub gate that reports every step the Python `held_by`
     lists name, and its `every step` case expects no Issue. Without the
     line, `held` asks for `wheel`, the stub does not report it, and that
     case raises a gap. The `meta` gate runs this probe, so the loop
     will see it before landing.
4. **The DR.** Write `.meta/assertions/decisions/DR-361.yaml`, or the
   next free number if one has landed since. It records the choice of a
   manifest check over building a wheel, the alternatives (build and
   import the wheel, or switch `test` to `--import-mode=importlib`), and
   the Discipline the step sits under. Its `enacted_in` lists
   `work:artifact/bootstraps-python-gate` (the gate source) and
   `work:artifact/bootstraps-python-readme`, which are the ids
   `.meta/assertions/structure.yaml` already declares. The other files
   have no artifact id, and none is minted for them. Then run `just render`, which regenerates
   `.meta/decisions.md` and the "Held by" column in `README.md`.
5. **Check by hand.** In `seed/`, run `uv run gate wheel` and see `ok`.
   Then drop the `packages` line from `RENAMES` in `render` in the working
   tree only, render into `$TMPDIR`, run `uv run gate wheel` in the copy,
   and see `x` naming `src/seed` and `src/acme`. Restore `render` with
   `git checkout bootstraps/python/render`. Record what was seen in the
   Issue file.

**Risks.**
- Adding `wheel` to `held_by` means `.meta/audit.py`
  (`held`) will now ask every audited Python Project for a `wheel`
  step. That is the intent, but an adopted repository that lacks the step
  will get an Issue from the next audit. The DR says so.
- The hand check needs `uv sync` in the rendered copy, and the sandbox
  may refuse it. If it does, record that it could not run rather than
  claiming a result. The probes carry the claim either way.
- `mutants` mutates only members under `packages/`, so mutation testing
  never covers the new gate code. The probes are the only evidence for
  it.

## What was done

- **The step.** `wheel`, `wheel_entries` and `unpackaged` are in
  `bootstraps/python/seed/gate/src/gate/__init__.py`, and `wheel` sits
  between `comments` and `ruff` in `STEPS`. On the seed, `uv run gate wheel`
  reports `ok wheel — 2 wheel packages under 2 manifests, each present and
  importable, none left out`, which covers `packages/seed` and `gate`.
- **The probes.** Three probes in `gate/tests/test_probes.py`:
  `test_a_wheel_naming_a_package_that_is_not_there_is_found`,
  `test_a_wheel_package_without_an_init_is_found` and
  `test_a_member_without_a_wheel_table_passes`. Each was run before the
  step existed and failed on the import.
- **The hand check on a broken render.** I monkeypatched `RENAMES` in a
  throwaway script rather than editing `render`, so the broken rename was
  never on disk. I rendered the seed twice into `TMPDIR` and called `wheel`
  on each copy directly. This needs no `uv sync`, because the step runs no
  tool. With every rename the copy reports `ok wheel`. Without the
  `packages` rename it reports:

  ```
  x  wheel (2)
       packages/acme/pyproject.toml: the wheel packages `src/seed`, which is not a directory
       packages/acme/pyproject.toml: the wheel leaves out `src/acme`
  ```

  The issue also asks for the gate to exit non-zero in this case. That
  follows from `run`, which fails on any `Found`, and the probe
  `test_only_a_finding_fails` already covers it.
- **Riding along:**
  - `wheel` is added to the Python Nothing Unconsumed `held_by` in
    `.meta/assertions/bootstraps.yaml`.
  - `"ok wheel"` is added to `FULL` in
    `.meta/checks/probes/tools/audit.py`.
  - `bootstraps/python/nothing-unconsumed.md` has a paragraph on the step.
  - The gate `README.md` has a new step row, and its pure-step list names
    `wheel`.
  - DR-361 is written. `just render` regenerated `.meta/decisions.md` and
    the "Held by" column of `bootstraps/python/README.md`.
- **A limit the next reader should know.** DR-361 records it too: the check
  trusts hatch's `packages` setting alone. It does not read the hatch
  settings `only-include`, `force-include` or `sources`. The seed uses none
  of them.

## Pair notes

> **primary, backlog turn 1**
>
> I've groomed `issues/underway/python-seed-packages-rename-unseen.md` and set it to `difficulty: medium`.
>
> **Why the bad render still passes `test`:** I worked this out from the code in `bootstraps/python/seed/gate/src/gate/__init__.py`. I tried to render a broken copy to confirm it, but that command needed approval and didn't run.
> - **`test`** gives pytest the `src` directory with `--doctest-modules`. In pytest's default import mode, that puts `src/` on the import path, so `import acme` works whatever the wheel's `packages` setting says.
> - **`evidence`** runs `pytest --collect-only` with no paths and fails with exit 2. That shows the installed copy can't import `acme`, so the issue's guess that the editable install hides the fault is wrong.
> - **`types`** hands mypy the files by path, and **`mutants`** puts its own copy of `src` on the path, so neither ever checks what the wheel would contain.
>
> **What the issue now asks for:** a new step in the seed's gate that only reads the manifests and the tree. It fails when a member's `[tool.hatch.build.targets.wheel] packages` names:
> - a directory that doesn't exist,
> - or a directory with no `__init__.py`.
>
> It also fails when an importable directory under `src/` is not named, because the wheel would leave it out.
>
> **Decided while grooming:** the gate will not build and import a wheel. Building one fetches hatchling, which is slow and needs network access a seat's sandbox doesn't have. The issue asks for this to be written up as a decision record and added to the gate `README.md`'s step table.
>
> **Out of scope:**
> - changing `test`'s import mode
> - `evidence` still showing `?` next to the new failure
> - the Rust seed
>
> **How we'll know it's done:**
> - Tests in `test_probes.py` cover a wrong package name, a missing `__init__.py`, and the layouts that should pass.
> - One manual check: take the rename out of `bootstraps/python/render` again, gate the rendered copy, and confirm it now fails rather than reporting `?`.

> **secondary, backlog turn 2**
>
> I agree with how my partner groomed this issue, including `difficulty: medium`. Their explanation of why the broken render passes matches the gate code in `bootstraps/python/seed/gate/src/gate/__init__.py`. I added three things so it can be planned without guessing:
>
> - **Name and place:** the new check is a pure step called `wheel`. It goes under the `# --- pure steps` banner and comes before `ruff` in `STEPS`, so it reports before any tool runs.
> - **What it covers:** it goes through the packages that the gate's existing `packages` function finds. That means the gate's own package as well as the seed's package, and the `mutants/` copies are skipped.
> - **One more "done when" check:** `uv run gate wheel` reports `ok` on the unbroken seed, so a correct layout passes for both packages.
>
> I committed the change to the issue file.

> **primary, backlog turn 3**
>
> I'm leaving the issue as it is. I checked each of my partner's additions against the code, and all three are right:
>
> - **The banner exists:** `# --- pure steps: functions over a path, watched failing by the probes` is in `bootstraps/python/seed/gate/src/gate/__init__.py`.
> - **`packages` covers both members:** the `packages` function in that file returns every member that has its own `pyproject.toml`. That means `packages/seed` and `gate`, and `mutants/` copies are already skipped.
> - **The new check would pass on the gate too:** `gate/pyproject.toml` has `packages = ["src/gate"]` in `[tool.hatch.build.targets.wheel]`, so `uv run gate wheel` on the unbroken seed checks both members.
>
> `difficulty: medium` still fits.

> **primary, todo turn 1**
>
> I've written `## The plan` into `issues/todo/python-seed-packages-rename-unseen.md`. Nothing is implemented yet.
>
> **Order of the steps:**
> 1. **Tests first:** add the three probes to `test_probes.py` and watch them fail.
> 2. **The new step:** add `wheel` and a per-member helper, `unpackaged`, under the pure-steps banner in the gate source, then put `wheel` in `STEPS` between `comments` and `ruff`. If a manifest doesn't parse, the step stays quiet, because `lints` runs first and already reports it.
> 3. **Which Discipline holds it:** the step goes under Nothing Unconsumed, since a source package the wheel doesn't ship is code nothing uses. That means adding it to `held_by` in `.meta/assertions/bootstraps.yaml`, a paragraph in `nothing-unconsumed.md`, and a row in the gate `README.md` step table.
> 4. **The decision record:** write DR-361, listing the two files that already have artifact ids (the gate source and the Python bootstrap README), then run `just render`.
> 5. **Check by hand:** `uv run gate wheel` should report `ok` on the seed and `x` on a deliberately broken render in `$TMPDIR`. Restore `render` afterwards.
>
> **Risks named in the plan:**
> - **Adopted repositories:** with `wheel` in `held_by`, the audit will raise an Issue for any adopted Python Project whose gate has no `wheel` step.
> - **Sandbox:** the hand check needs `uv sync`, which the sandbox may refuse. If so, the Issue should say the check couldn't run.
> - **No mutation coverage:** mutation testing only covers packages under `packages/`, so the probes are the only evidence for the new gate code.
>
> Putting the step under Nothing Unconsumed is my call and wasn't in the groomed issue. If my partner would rather keep it out of the Bootstrap's list, step 3 shrinks to just the README row.

> **secondary, todo turn 2**
>
> My partner's plan was sound, but it missed one file that would break, so I added that step to the plan in `issues/todo/python-seed-packages-rename-unseen.md` and committed it.
>
> **The missing step:** the plan adds `wheel` to the Python Nothing Unconsumed `held_by` list in `.meta/assertions/bootstraps.yaml`. That would break a test in `.meta/checks/probes/tools/audit.py`:
> - `FULL` in that file is a fake gate's output that reports every step the Python `held_by` lists name.
> - Its `every step` case expects the audit to raise no Issue.
> - Once `held_by` names `wheel`, `held` in `.meta/audit.py` asks for a `wheel` step that `FULL` does not report. The audit then raises an Issue for the missing step and the case fails.
>
> The plan's step 3 now adds `"ok wheel"` to `FULL`. The `meta` gate runs that test, so the loop will check it before landing.
>
> **What I checked and found correct:**
> - **The test setup:** the existing probes' package manifest, `PACKAGE_MANIFEST`, has no hatch table, so they are unaffected, and new probes can add one with `Tree.write`.
> - **Size limits:** ruff caps a function at 12 branches and complexity 12, which is why the plan splits the work into a helper, `unpackaged`.
> - **Artifact ids:** the two the decision record will cite already exist in `.meta/assertions/structure.yaml`.
> - **Decision record number:** the highest is DR-360, so the new one is DR-361.
> - **Exposition file:** `nothing-unconsumed.md` exists in `bootstraps/python/`, and its `orphans` paragraph is where the plan puts the `wheel` one.
>
> I'm happy with my partner's call to put the step under Nothing Unconsumed.

> **primary, todo turn 3**
>
> I'm leaving the plan as it is. My partner's addition is correct and nothing else is missing:
>
> - **The `FULL` fix is needed:** `FULL` in `.meta/checks/probes/tools/audit.py` lists one report line per step the Python `held_by` lists name. The "every step" case expects no Issue, so once `wheel` joins `held_by`, the stub needs an `"ok wheel"` line or that case fails.
> - **No other place would break:** I searched `.meta/checks` for anything else tied to the Python `held_by` list. The only other hits are the `held_by` lists in `.meta/checks/probes/structure.py`, which are a self-contained example that never reads `bootstraps.yaml`. Nothing else in `.meta/checks` runs the audit against the real seed gate.

> **primary, in-progress turn 1**
>
> The seed's gate now fails when a wheel names a package that isn't there. A broken render reports `x wheel` instead of passing `test` and leaving only a `?` on `evidence`. `just gate meta` and `just gate python-seed` both pass, and on `python-seed` the new step reports `ok` on the rendered `acme` copy.
>
> **The change:**
> - **New step:** `wheel` in `bootstraps/python/seed/gate/src/gate/__init__.py` runs between `comments` and `ruff`. It reads each member's `[tool.hatch.build.targets.wheel] packages` and fails on:
>   - an entry that isn't a directory,
>   - an entry with no `__init__.py`,
>   - a package under `src/` that no entry names.
>
>   It runs no tool and needs no network.
> - **Tests:** three new tests in `gate/tests/test_probes.py` cover a wrong name, a missing `__init__.py`, and a member with no hatch table. I ran them before the step existed and watched them fail; all 28 tests pass now.
> - **Hand check:** I rendered the seed twice into `TMPDIR` with a throwaway script, so the broken `RENAMES` never touched disk. The full render passes. Without the `packages` rename, the copy reports `x wheel`, naming `src/seed` as missing and `src/acme` as left out.
> - **Files that change with it:**
>   - `wheel` is added to the Python Nothing Unconsumed `held_by` list in `.meta/assertions/bootstraps.yaml`, and to `FULL` in `.meta/checks/probes/tools/audit.py`.
>   - `nothing-unconsumed.md` gets a paragraph on the step, and the gate `README.md` gets a row.
>   - DR-361 is written, and `just render` regenerated `.meta/decisions.md` and the Python bootstrap README.
>
> **Where the work departed from the plan:**
> - I split the planned single helper in two, `wheel_entries` and `unpackaged`, and updated the plan to match.
> - The first `meta` run failed because the plan's wording cited `held_by` as a slot of Discipline, which it isn't (it belongs to a Bootstrap's Discipline implementation). I reworded it and the rerun passed.
>
> **For the next reader:** the issue file has a "What was done" section. It records that the check reads only hatch's `packages` setting and ignores `only-include`, `force-include` and `sources`. The seed uses none of these, and DR-361 says the same.
>
> I found no work outside this issue, so I wrote no new backlog file. The change is committed as `f5e8daf0`.

> **secondary, in-progress turn 2**
>
> The `meta` gate was failing when I started this turn, and it passes now after a one-line fix to the issue file.
>
> **What was failing:** the "cited schema slots" check. My partner's pair note explained an earlier failure by quoting the bad wording, which named `held_by` as a slot of Discipline. That quote set off the same check again. I reworded the note to describe the problem without repeating the phrase, and committed it.
>
> **The implementation itself:** I reviewed my partner's code and found nothing to change.
> - The new `wheel` step follows the plan. It reads each package's `[tool.hatch.build.targets.wheel] packages` and fails on an entry that is missing, one with no `__init__.py`, and a package under `src/` that no entry names.
> - The three new tests match exactly what each case should report, and they also check that the fixed tree passes.
> - DR-361 cites an artifact id that exists in `.meta/assertions/structure.yaml`.
> - The fake gate output in `.meta/checks/probes/tools/audit.py` now reports `ok wheel`.
>
> **Gates:**
> - `just gate meta`: passes, all 95 steps.
> - `just gate python-seed`: passes, all 10 steps, including `mutants`.
>
> I found no work outside this issue, so I wrote no new backlog file.

> **primary, in-progress turn 3**
>
> `just gate meta` failed again when I re-ran it. My partner's new pair note quoted the same wording it said it had removed, so the "cited schema slots" check fired on that quote. I reworded the note to describe the problem without quoting the phrase, and `meta` now passes. The fix is committed as `5330c7fc`.
>
> Because the loop copies each turn's closing message into the issue's pair notes, this message also leaves the phrase out.
>
> That edit was the only change this turn; the code is unchanged. I didn't re-run `python-seed`: nothing under `bootstraps/python/seed/` has changed since its last pass, which included `mutants`.

> **secondary, in-progress turn 4**
>
> I'm changing nothing this turn.
>
> - My partner's fix is right. My last closing message had been copied into the pair notes and still quoted the wording that trips the "cited schema slots" check, so the `meta` gate failed again. Their reword fixes it.
> - `just gate meta` passes now, all 95 steps.
> - Since my last turn, only the issue file has changed, so I didn't re-run `python-seed`. Its last run passed, including `mutants`.
> - I kept the problem wording out of this message so it can't be copied back into the notes.
