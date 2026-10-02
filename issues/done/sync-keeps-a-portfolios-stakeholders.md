---
parent: onboard-fitch-mvp
difficulty: medium
---

# A sync keeps a portfolio's own stakeholders

`stakeholders/` is a managed directory item in `.meta/bundle.yaml`, but it
holds product-side material: a portfolio adds its own Personas under
`stakeholders/customers/` and its Roles under `stakeholders/internal/`.
`just sync` (DR-315) mirrors a managed directory, so it deletes every tracked
file there that the stereorepo checkout lacks, which is every Persona and Role
the portfolio wrote. Git can recover them, and the sync prints each one as
`removed`, but a sync should not remove the portfolio's product material.

## Wanted

A sync never removes or overwrites a file under `stakeholders/` that the
portfolio wrote, and still brings the scaffold's three READMEs
(`stakeholders/README.md`, `stakeholders/customers/README.md`,
`stakeholders/internal/README.md`), which say what the directory is for.

- Replace the `stakeholders/` directory item with managed file items for those
  three READMEs.
- `stakeholders/internal/architect/README.md` is the scaffold's own example
  Role. It stops being managed. Specialization copies only what its *Copy
  what is inherited* step names and never clones, so a new portfolio no longer
  gets it. That is intended, because a portfolio's Roles are its own. A sync
  leaves it alone wherever a portfolio already has it.
- **The first sync after the change is the trap.** `plan` in
  `.meta/lib/bundle/sync.py` removes a tracked path that the portfolio's *old*
  bundle managed (`old.manages(path)`), and every portfolio's old bundle lists
  `stakeholders/` as a managed directory. Swapping the item alone therefore
  still deletes the portfolio's Personas and Roles on that sync. The fix must
  stop that. One way is to make the removal of a dropped item's files skip
  any path that a new item still claims for the portfolio. That item can be a
  new ownership kind, kept the way template and symlink items already are
  (`kept` in `plan`). The plan seat picks the mechanism and records it as a
  DR.
- The Specialization Discipline's *Copy what is inherited* step
  (`.meta/assertions/disciplines.yaml`) names `stakeholders/` and says
  `.meta/bundle.yaml` "is the same list". Change it to name the three READMEs
  so it still matches the bundle, and re-render `SPECIALIZE.md`.

## Out of scope

- `wiki/stereorepo/` and `.meta/assertions/imported/` are not affected. Each
  one is stereorepo's own by design: a portfolio writes its wiki pages under
  `wiki/<its-context>/` (`wiki/README.md`), and its own assertions one level
  above `imported/` (`.meta/assertions/imported/README.md`). Both stay managed
  directories.
- Changing how a sync treats any other managed directory.

## Done when

The tests beside the existing sync tests in
`.meta/checks/probes/tools/sync.py` show these behaviours:

- A portfolio whose bundle lists the three READMEs as file items, and that
  tracks `stakeholders/customers/<persona>.md` and
  `stakeholders/internal/<role>/README.md`, keeps both files byte for byte
  after a sync. Neither one appears in `removed`.
- A portfolio whose *old* bundle still lists `stakeholders/` as a managed
  directory keeps the same files after a sync from a checkout with the new
  bundle.
- A sync updates a stale `stakeholders/README.md` from the checkout, and
  restores one that has been deleted.
- The scaffold's `.meta/bundle.yaml` no longer lists `stakeholders/` as a
  managed directory, and the bundle still loads and validates.
- `SPECIALIZE.md`'s copy step lists the three READMEs, not `stakeholders/`.

## The plan

**Mechanism: a fourth ownership kind, `portfolio`.** A `portfolio` item names
a path whose content belongs to the portfolio. No copy brings it, and a sync
never removes anything under it. The bundle lists `stakeholders/` as a
`portfolio` dir item, and the three READMEs as `managed` file items inside it.
`plan` in `.meta/lib/bundle/sync.py` already keeps every path under a
template or symlink item (`kept`), even where the old bundle managed it. That
is how a template item that replaced a managed one survives. Adding
`portfolio` items to `kept` covers the transition sync for free: the old
bundle's `stakeholders/` directory is matched by `old.manages`, but `kept`
wins. The READMEs are in `copies`, so `kept` never blocks them. I rejected an
implicit rule ("a new managed item inside an old managed dir narrows it")
because it is invisible in the bundle, and it would also keep files that a
deliberate narrowing meant to drop.

Steps, in order:

1. `.meta/lib/bundle/__init__.py`: add `"portfolio"` to `VALID_OWNERSHIPS`,
   add `Bundle.portfolio_items()` beside `template_items()`, and widen the
   `ownership` attribute docstring. `manages` is unchanged, because it reads
   only managed items, so the ratchet's baseline split (DR-314) is unaffected.
   `_validate_item` needs nothing new: the source must exist, and
   `stakeholders/` does.
2. `.meta/lib/bundle/sync.py`: add `*new.portfolio_items()` to `kept`, and
   say so in the module docstring and in `plan`'s.
3. `.meta/bundle.py`: add `portfolio` to the `--ownership` choices (line 175).
4. `.meta/lib/adapt/plan.py`: `_classify_bundle_item` would show a
   `portfolio` dir as CREATE when it is absent, and an adoption would then
   copy the scaffold's example Role. In `build_adoption_plan`'s loop over
   `active_bundle.items`, skip a `portfolio` item before it reaches
   `seen_destinations`, `dir_dests` or `_classify_bundle_item`, whether or
   not the target has it. The READMEs' own CREATE actions bring the
   directory, and the target's files under it fall to the existing "existing
   product artifact retained untouched" pass. A RETAIN action for the
   directory itself would add nothing that pass does not already give.
5. `.meta/bundle.yaml`: replace the `stakeholders/` managed dir item with a
   `portfolio` dir item for `stakeholders/` (in a new `# Portfolio-owned`
   section), plus three managed file items for `stakeholders/README.md`,
   `stakeholders/customers/README.md` and `stakeholders/internal/README.md`.
   `test_specialization`'s floor of 25 managed items still holds (+2).
   `.meta/test_specialization.py` step 2 copies `managed_items()` only, so a
   specialized portfolio gets the three READMEs and not
   `internal/architect/`.
6. `.meta/assertions/disciplines.yaml` line 33: replace `stakeholders/` with
   the three README paths. `read_inherited_paths` takes every backticked
   token, so the lockstep with the bundle holds. Add a clause saying that a
   portfolio's own Personas and Roles are its own and no sync touches them.
   Re-render, which updates `SPECIALIZE.md`.
7. `.meta/assertions/decisions/DR-317.yaml`: "A sync never touches a path the
   bundle marks `portfolio`". It records the reason (DR-041: `stakeholders/`
   is product material), the rejected options (the implicit narrowing rule,
   and dropping the directory from the bundle outright, which the old
   bundle's `old.manages` would still have deleted on the first sync), and
   that the example Role is no longer inherited. Re-render `decisions.md`.

**Tests**, in `.meta/checks/probes/tools/sync.py`. The fixture models the
transition directly:

- `OLD_BUNDLE` gains `{path: people/, kind: dir, ownership: managed}`.
  `NEW_BUNDLE` replaces it with `{path: people/, kind: dir, ownership:
  portfolio}` and `{path: people/README.md, kind: file, ownership: managed}`.
  The neutral `people/` keeps the probe independent of the real directory.
- `SOURCE` holds `people/README.md` (new text) and `people/example/README.md`,
  which the checkout tracks but no managed item names. `PORTFOLIO` holds
  `people/README.md` (old text), `people/customers/ada.md` and
  `people/example/README.md` with the portfolio's own edit.
- `_check_sync`: `people/README.md` holds the checkout's text and is printed
  `updated`. `_kept` adds `people/customers/ada.md` and
  `people/example/README.md`: each is byte for byte unchanged and never
  printed. This test is the old-bundle transition, the case that fails today.
- A second case, run from a portfolio already on `NEW_BUNDLE` with
  `people/README.md` deleted and committed: the sync prints `added` for it,
  restores it, and keeps `ada.md`.
- `_check_block_helpers` (or a small sibling): `validate_bundle` accepts a
  `portfolio` item, and still rejects an unknown ownership.
- `.meta/checks/probes/tools/test_specialization.py`: assert that the real
  bundle has no managed item at or above `stakeholders/customers/` (via
  `bundle.manages("stakeholders/customers/x.md")` being false), and that
  `stakeholders/` is a `portfolio` item.
- The adoption probe in `test_brownfield.py`: assert that a target holding
  `stakeholders/customers/x.md` gets RETAIN for it, CREATE for each of the
  three READMEs, and no action at all for `stakeholders` or
  `stakeholders/internal/architect/README.md`. Read the probe first. If it
  cannot express this cheaply, call `build_adoption_plan` on a small `tmp`
  target with the real bundle.

**Risks.**
- `kept` wins over every other removal rule, so a sync never removes
  anything under a `portfolio` item, not even a file a later bundle stops
  managing. If stereorepo ever drops one of the three READMEs, portfolios
  keep their copy. That is the price of the guarantee. The DR states it, and
  the `kept` comment in `plan` says it.
- `Bundle.inherited_paths()` and `checks/files/sources.inherited()` read only
  `managed_items()`, so the `portfolio` item stays out of what the gate
  treats as inherited machinery. Do not widen either one.
- Any other reader of `bundle.items` that assumes three ownerships. `grep`
  found only `bundle.py`'s choices and the adoption plan; re-grep for
  `ownership` before landing.
- A portfolio whose `stakeholders/README.md` it rewrote itself will have it
  replaced by the sync, as before. That is unchanged behaviour for a managed
  file and stays out of scope.
- The real `.meta/bundle.yaml` is itself a managed file. The first sync
  reads the old bundle from the portfolio before the copy, and the new one
  from the checkout. That ordering is what makes `kept` apply, and the
  transition test pins it.

## What was done

The work follows the plan, with these differences and notes:

- **Adoption plan.** The skip of a `portfolio` item shares the existing
  `continue` in `build_adoption_plan`. `.meta/lib/adapt/plan.py` sat at its
  500-line ceiling, so the change also tightened two calls in the same
  function rather than raise the file-size baseline.
- **Adoption probe.** `_check_empty_target` in `test_brownfield.py` expected
  one CREATE per bundle item; it now leaves out `portfolio` items. The new
  `_check_portfolio_items` checks the four expected actions and the absence
  of the two unwanted ones in one table, to keep the file at 500 lines.
- **Sync probe.** The fixture now carries the transition. `OLD_BUNDLE` has a
  managed `people/`, and `NEW_BUNDLE` narrows it to a `portfolio` item plus a
  managed `people/README.md`. `_check_sync` and `_kept` cover the first
  sync. `_check_portfolio_items` covers a portfolio already on the new
  bundle that deleted the README, and the validator accepting `portfolio`
  but rejecting an unknown ownership. With `portfolio_items()` taken out of
  `kept`, the probe reports both of the portfolio's own files as changed and
  printed, which is the bug this issue fixes.
- **Specialization probe.** `_check_bundle` asserts that `stakeholders/` is
  a `portfolio` item, and that no managed item contains
  `stakeholders/customers/`.
- **Copy step.** The new sentence in the Specialization step uses no
  backticks, because `read_inherited_paths` takes every backticked token in
  that step as an inherited path.
- **DR-317** records the decision. It answers DR-316's objection to a new
  ownership kind: that objection was that readers of the managed items
  would have to learn it, and here none does.
- **A done issue was edited.** Inserting the three README items moved the
  `.gitignore` item in `.meta/bundle.yaml` from line 81 to line 87, and the
  path-and-line check failed on the citation of it in
  `issues/done/fresh-worktree-passes-meta-gate.md`. The citation now reads
  line 87.
- **Render.** `just render` could not write
  `.claude/skills/wikisplain/SKILL.md` in this sandbox and stopped there.
  It had already written `decisions.md`, `disciplines.md` and
  `SPECIALIZE.md`. Nothing this change touches feeds that skill.
