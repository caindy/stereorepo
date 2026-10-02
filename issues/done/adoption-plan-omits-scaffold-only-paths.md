---
difficulty: easy
parent: onboard-fitch-mvp
---

# Leave scaffold-only paths out of a brownfield adoption plan

`.meta/lib/adapt/plan.py` plans each `dir` item of `.meta/bundle.yaml` as a
whole (`_classify_dir` never looks inside). `.meta/lib/` and `.meta/checks/`
are such items, so a repository adopted from the plan gets `.meta/lib/adapt/`
and `.meta/checks/probes/tools/test_brownfield.py`. Neither has a subject
there: its `brownfield adoption probes` step reports `?` for good, which
fails the run wherever `CI` is set (DR-261).

`portfolio-steps-without-subject` makes these nested paths entries of
`SCAFFOLD_ONLY` and leaves them out of a specialized portfolio. The adoption
plan should leave out the same paths, and the `test_brownfield.py`
could-not-run branch can then go.

## Wanted

- `build_adoption_plan` adds one action per `SCAFFOLD_ONLY` path that lies
  strictly inside a `dir` item it plans, with a new classification
  `PathClassification.OMIT` and a reason naming DR-305. Today that is
  `.meta/lib/adapt` and `.meta/checks/probes/tools/test_brownfield.py`. The
  action is `omit` whatever the target holds at that path, and a planned
  directory is to be copied without its omitted paths. The text, JSON and
  YAML formats and `summary` show the new classification; an `omit` action is
  not a conflict.
- The planner takes the paths from an existing list (`SCAFFOLD_ONLY` in
  `.meta/checks/files/scaffold.py` or `SCAFFOLD_ONLY_PATHS` in
  `.meta/test_specialization.py`), or moves the list somewhere both can
  import. A third hand-kept copy is not acceptable unless the lockstep probe
  in `.meta/checks/probes/files/scaffold.py` compares it too.
- `test_brownfield_probes` loses its could-not-run branch: `NO_TEMPLATE`,
  `_check_without_template`, the `template/` test at the top of the step,
  case 7 of its docstring and the paragraph explaining it. The guarded import
  in `checks/probes/tools/__init__.py` stays, since an adopted repository no
  longer has the probe.

## Out of scope

- Applying the plan, and removing these paths from fitch-mvp, which got them
  from the first pass's hand copy. Both belong to `onboard-fitch-mvp`.
- Top-level scaffold-only paths (`pair/`, `template/`, `.meta/adapt.py`, …):
  none is a bundle item, so the plan already leaves them out.

## Done when

- A new case in `test_brownfield.py` plans an empty target and finds an
  `omit` action for each of the two paths above, and no action of any other
  classification at or below either one. The empty-target case still expects
  one `create` per bundle item.
- A target that already holds `.meta/lib/adapt/` still gets `omit` there, and
  the plan has no conflicts on its account.
- `just adapt plan` against an empty directory lists both paths as `omit` in
  each output format.
- `test_brownfield.py` no longer mentions `template/` as a reason it could
  not run.

## The plan

1. **One list, in `lib.bundle`.** Move `SCAFFOLD_ONLY_PATHS` and its docstring
   from `.meta/test_specialization.py` into `.meta/lib/bundle/__init__.py`,
   beside `VALID_KINDS`. `test_specialization.py` already imports
   `lib.bundle`. It imports the name from there, so `runner.SCAFFOLD_ONLY_PATHS`
   still resolves and the lockstep probe in
   `.meta/checks/probes/files/scaffold.py` (`_lists_agree`) still compares it
   with `SCAFFOLD_ONLY` without any change. `lib` never imports `checks`, and
   this keeps it that way. A portfolio inherits `lib/bundle`, but the
   `scaffold-only paths` step scans only `.md` and `.yaml` files, so the
   constant does not trip it.
2. **`OMIT` in `.meta/lib/adapt/plan.py`.**
   - Add `OMIT = "omit"` to `PathClassification`, and add it to the docstring
     of `PlannedAction.classification`. `summary`, `to_dict` and `to_text`
     iterate the enum, so all three formats pick it up. The text column is
     9 characters wide, so `OMIT` fits.
   - Add a helper, `_omitted_paths(dir_dests, scaffold_dir)`. For every
     `SCAFFOLD_ONLY_PATHS` entry that starts with `<d>/` for a planned `dir`
     destination `d`, it returns a `PlannedAction(OMIT, reason="scaffold-only:
     a portfolio does not have it (stereorepo's DR-305)")`. Its `kind` is
     `dir` or `file` according to what the scaffold holds at that path.
   - In `build_adoption_plan`, after the bundle loop, append those actions.
     The target scan then skips every path at or below an omitted path. Today
     a target file such as `.meta/lib/adapt/plan.py` would otherwise be listed
     as `retain` ("existing product artifact retained untouched"), which
     would keep the very file the plan omits.
3. **Probe (`.meta/checks/probes/tools/test_brownfield.py`).**
   - Add `_check_omits_scaffold_only(scaffold_dir, tmp)`. In an empty target
     it finds exactly one `omit` action for each nested entry of
     `SCAFFOLD_ONLY_PATHS`, and no other action at or below either one. In a
     second target it writes `.meta/lib/adapt/plan.py` and checks two things:
     `.meta/lib/adapt` is still `omit`, and nothing at or below it is
     `retain` or `conflict`. The case takes the expected paths from the list
     rather than spelling them out, so a new nested entry is covered too.
   - In `_check_cli_and_formats`, assert that the JSON, YAML and text outputs
     each contain an `omit` row for `.meta/lib/adapt`.
   - `_check_empty_target` keeps its count of `create` actions per bundle
     item. `omit` is not `create`, so the count stands.
   - Delete `NO_TEMPLATE`, `_check_without_template`, its call, the
     `template/` guard at the top of `test_brownfield_probes`, docstring case
     7 and the paragraph explaining it. Then trim the `Returns:` section to
     `Found` or `Passed`, and drop `CouldNotRun` from the imports if nothing
     else uses it.
   - Renumber the docstring's cases so the new omit case takes the freed
     place, and keep the count in `Passed("8 adoption cases")` equal to the
     number of `_check_*` calls (one removed, one added: still 8).

No assertion or generated page names the classifications, so nothing needs
re-rendering. The copy under `apm_modules/` is ignored by git.

**Risks.**
- Moving the constant changes `test_specialization.py`'s import surface. A
  portfolio does not inherit that file, so only the scaffold is affected.
- Skipping target paths below an `omit` path also hides any product file a
  target keeps there. That is wanted, since the path is the scaffold's.

## As built

Where the work departed from the plan:

- The lockstep probe (`_lists_agree` in
  `.meta/checks/probes/files/scaffold.py`) now imports
  `lib.bundle.SCAFFOLD_ONLY_PATHS` directly, rather than loading
  `test_specialization.py`. It no longer skips the comparison where that
  script is absent, so it now runs in a portfolio too.
- The helpers live in a new module, `.meta/lib/adapt/omit.py`, which holds
  `OMIT_REASON`, `scaffold_only_inside(dir_dests)` and `below(path,
  prefixes)`, rather than in `plan.py`. With them `plan.py` would have passed
  its 500-line ceiling. The module returns paths, not `PlannedAction`s, to
  avoid an import cycle. `build_adoption_plan` builds the `omit` actions, and
  the probe uses `scaffold_only_inside` to pick which paths to expect. It is
  asserted as `work:artifact/meta-lib-adapt-omit` in `structure.yaml`, and it
  is scaffold-only because it sits under `.meta/lib/adapt/`.
- The reason reads "scaffold-only, which a portfolio does not have, by
  stereorepo's DR-305", without parentheses, because `to_text` already wraps
  the reason in parentheses.
- `test_specialization.py` lost five lines, so its file-size baseline drops
  from 128 to 123.

Run against an empty directory, `just adapt plan` lists `.meta/lib/adapt`
(dir) and `.meta/checks/probes/tools/test_brownfield.py` (file) as `omit`
in each of `--format text`, `json` and `yaml`. The summary counts `omit: 2`
and there are no conflicts. `brownfield adoption probes` reports 8 adoption
cases.
