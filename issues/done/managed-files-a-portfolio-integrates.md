---
difficulty: medium
parent: onboard-fitch-mvp
---

# A sync keeps what a portfolio integrated into a managed file

`.gitignore` is a managed item in `.meta/bundle.yaml`, but adopting
fitch-mvp meant integrating it by hand, keeping fitch-mvp's own lines beside
stereorepo's. Any copy of the managed items, including `just sync` (DR-315),
overwrites the file and drops those lines.

## Which files

`.gitignore` is the only managed *file* item an existing repository is likely
to hold already: every other managed file lives under `.meta/`, which an
existing repository does not have. The managed *directories* that hold a
portfolio's own material (`stakeholders/`, and possibly `wiki/stereorepo/` and
`.meta/assertions/imported/`) are `sync-keeps-a-portfolios-stakeholders`, not
this Issue.

The portfolio's lines cannot move to a file the bundle never lists: git
applies a nested `.gitignore` only below its own directory, and neither
`.git/info/exclude` nor `core.excludesFile` is tracked. Both sets of lines have
to stay in the root `.gitignore`.

## Wanted

The bundle marks `.gitignore` so that stereorepo owns one delimited block of
the file and the portfolio owns the rest, with stereorepo's `.gitignore`
wrapping its lines between a begin and an end marker comment. The plan below
makes that mark a `block` transformation on the existing `managed` item
rather than a new ownership.

- **Sync.** For such an item, `just sync` replaces only the text between the
  markers with the checkout's block and keeps every line outside them
  byte-for-byte. If the portfolio's file has no markers (a hand-integrated
  file such as fitch-mvp's, or none at all), it appends the checkout's block,
  markers included, to whatever the file holds. It prints the path as updated
  or added only when the file's bytes change. Its existing refusals still
  apply: an uncommitted change to `.gitignore` refuses the sync.
- **Transition.** A portfolio's own `.meta/bundle.yaml` still marks
  `.gitignore` `managed` until its first sync after this lands. Today
  `sync.plan` removes every tracked path the old bundle manages that the new
  bundle neither copies nor keeps (`kept` holds only template and symlink
  items), so a new ownership left out of that list would delete the
  portfolio's `.gitignore`. That sync must treat it as a block item like any
  other, never as a removal. Keeping the item `managed` meets this by
  construction.
- **Specialization.** A new portfolio receives the file as it is today,
  markers included, so the copy step and `test_specialization` still work.
- **Adoption.** `ADOPT.md`'s "Integrate the template items" step no longer
  lists `.gitignore` as integrated by hand; it says the sync appends the block
  and the product's own lines stay outside it.
- A Decision Record states the block and why a separate file and a new
  ownership were rejected.

## Out of scope

- Managed directories holding portfolio material
  (`sync-keeps-a-portfolios-stakeholders`).
- Template items (`AGENTS.md`, `README.md`): a sync leaves them alone already.
- Removing lines a hand-integrated file duplicates from the block. The
  developer tidies those once, in the diff the sync leaves uncommitted.

## Done when

- A sync test, built like the existing ones on two scratch git repositories,
  gives the portfolio a `.gitignore` with its own lines both before and after
  stereorepo's block, and the checkout a changed block. After the sync, the
  portfolio's lines are unchanged in place and the block matches the
  checkout's.
- A second case gives the portfolio a `.gitignore` with no markers. After the
  sync, its original lines come first, unchanged, followed by the checkout's
  block.
- A third case, where the portfolio's block already matches, leaves the file
  untouched and does not print it.
- A fourth case gives the portfolio a bundle that still marks `.gitignore`
  `managed` and a `.gitignore` with its own lines. The sync does not list
  `.gitignore` as removed; afterwards the file holds those lines followed by
  the checkout's block.
- A fifth case leaves `.gitignore` with an uncommitted change and the sync
  refuses, naming it.
- `validate_bundle` rejects a `block` item that is not a file, or whose
  source does not hold exactly one begin marker followed by one end marker;
  the scaffold's own bundle still validates. (`load_bundle` validates
  nothing; `validate_bundle` is where an unknown ownership is rejected.)

## The plan

**Design: a transformation, not an ownership.** `.gitignore` stays
`ownership: managed` and gains `transformations: [block]`. Every reader of
`managed_items()` (`inherited_paths()`, `manages()`, `checks/files/sources.py`,
both copies in `test_specialization`, `bundle.py list --ownership`) keeps
working unchanged, because the file is still something stereorepo brings. A
new ownership would have had to be threaded through each of those, and the
transition case (an old bundle marking the file `managed`) would have needed
its own rule in `sync.plan`. With a transformation, `.gitignore` is in the
sync's `copies`, so it is never removed, whatever the old bundle says. Only the
sync reads the transformation; Specialization copies the file byte-for-byte,
markers included.

1. **Markers in `.gitignore`.** Wrap the whole current file in
   `# >>> stereorepo: just sync replaces this block; add your own lines outside it`
   and `# <<< stereorepo`. Everything in it today, `.pair/` and `worktrees/`
   included, applies to a portfolio, so nothing stays outside. Mark the item
   in `.meta/bundle.yaml` with `transformations: [block]`.
2. **The merge** (`.meta/lib/bundle/__init__.py`, beside `under`, so both the
   validator and the sync use it). `BLOCK_BEGIN` and `BLOCK_END` match a line
   by prefix (`# >>> stereorepo`, `# <<< stereorepo`), so rewording the marker
   comment does not orphan an old block. Two pure functions:
   - `block_span(text) -> tuple[int, int] | None`: the character span from the
     start of the begin line to the end of the end line, `None` where neither
     marker is present, and `ValueError` where there is one without the other,
     more than one of either, or the end comes first.
   - `merge_block(current: str | None, source: str) -> str`: the source's span
     replaces the current file's span; with no span in `current`, the block is
     appended after `current`, with a newline added if `current` does not end
     in one; with `current` `None`, the result is the block alone.
3. **The sync** (`.meta/lib/bundle/sync.py`).
   - `Changes` gains `writes: tuple[tuple[str, bytes], ...]`, the merged
     content for each block destination that differs. `added`/`updated` and
     `touched()` take these paths like any copy, so the printing in
     `bundle.py` and the uncommitted-change refusal need no change.
   - In `plan`, after `_copies`, split out the destinations of items with
     `has_transformation("block")`. For each, read the source and (if
     present) the portfolio file as UTF-8, `merge_block`, and keep it in
     `writes` only when the bytes differ. A `ValueError` from a malformed
     portfolio file becomes `SyncRefusedError` naming the path and saying to
     fix its markers. They stay in the `copies` dict passed to the removal
     test, so they are never removed.
   - `apply` writes each of `writes` with `write_bytes`, keeping the portfolio
     file's mode where it exists. A portfolio `.gitignore` that is a symlink
     is refused in `plan` rather than merged, since `write_bytes` would write
     through it to whatever it points at.
   - The module docstring gains one sentence on the block.
4. **Validation** (`_validate_item`). A `block` item must be `kind: file`, and
   its source must hold one well-formed span (`block_span` returns a span).
   This catches a stereorepo edit that drops a marker, before any portfolio
   syncs it.
5. **The adoption plan** (`.meta/lib/adapt/plan.py`, `_classify_bundle_item`).
   Today a repository's own `.gitignore` falls through to `_classify_file`
   and is reported as a `conflict` ("differs from scaffold without
   integration policy"), and ADOPT step 5 sends every conflict to be worked
   by hand. Before the `DEFAULT_INTEGRATIONS` test, a present target whose
   item has `block` is classified `integrate` with the reason "the sync
   merges stereorepo's block and keeps the product's lines (DR-316)".
   `test_brownfield`'s target already tracks a `.gitignore` (`build/`); its
   probe gains an assertion that the action is `integrate` with that reason.
6. **Prose.** New `DR-316` (the next number): context fitch-mvp's
   `.gitignore`; alternatives a portfolio-owned file (git reads no tracked
   include, and a nested `.gitignore` applies only below itself), a new
   ownership (every reader of `managed_items()` changes, and an old bundle's
   `managed` entry needs a transition rule), and the `block` transformation
   (chosen). Edit the Adoption Discipline in
   `.meta/assertions/disciplines.yaml`: the judgement paragraph and step 5
   drop `.gitignore` from what is integrated by hand; step 4 (the sync, the
   adoption's first copy) says it appends stereorepo's block to the product's
   own `.gitignore`, and step 5 says the plan's `.gitignore` entry is already
   done by then. DR-316's
   `enacted_in` names `meta-lib-bundle-sync`, `meta-lib-bundle-init` and
   `meta-bundle`, as DR-315's does. Re-render
   (`just render`) so `ADOPT.md`, `.meta/disciplines.md` and
   `.meta/decisions.md` follow.
7. **Tests** in `.meta/checks/probes/tools/sync.py`, the existing scratch-repo
   probe. Its `OLD_BUNDLE` and `NEW_BUNDLE` gain a `.gitignore` item; the new
   bundle carries `transformations: [block]`, the old one does not, so every
   case below is also the transition case (Done when, fourth bullet). Cases:
   portfolio lines before and after the block with a changed checkout block;
   no markers; already matching (not printed, bytes unchanged); `.gitignore`
   dirty (refused, named, tree unchanged; the uncommitted edit must sit
   where the merge would change bytes, because `touched()` holds only paths
   in `writes`, so a dirty file whose merge is a no-op is rightly left
   alone); a malformed portfolio file (one
   marker only: refused). Unit-level cases for `merge_block` and
   `block_span` (missing trailing newline, `None` current, reversed markers)
   go in the same probe as plain assertions. The validator cases (a `block`
   dir item, a source with no markers) go in the sync probe too: the only
   other caller, `test_specialization`, validates the real bundle, which
   covers "the scaffold's own bundle still validates".

**Risks.**

- `test_specialization`'s `.gitignore` probe (`_check_gitignore`) copies the
  file and asks git what it ignores; comment lines change nothing there, but
  confirm it still passes.
- fitch-mvp's first sync after this appends a block that repeats lines it
  already integrated. That is the accepted out-of-scope tidy-up, and the
  desk-check brief of `onboard-fitch-mvp` should say so.

## What the work changed in the plan

- **The adoption plan's reason carries no DR number.** A citation in a
  string inside an inherited file has to read "stereorepo's DR-316" and the
  probe then had to match it; the reason reads "the sync merges stereorepo's
  block and keeps the target's own lines", and `_classify_bundle_item`'s
  docstring cites DR-316 instead, which the `enacting citations` step needs
  because DR-316 names `plan.py`. The brownfield probe matches
  "stereorepo's block" in the reason.
- **`plan.py` sat at exactly its 500-line ceiling.** The block test folds
  into the existing integrate branch (`block = item.has_transformation(BLOCK)`)
  rather than adding a branch of its own, and `_classify_dir` and
  `_classify_symlink` take their signatures on one line, so the file stays at
  500 without a baseline entry.
- **The sync reads both `.gitignore` texts with `newline=""`.** A portfolio
  `.gitignore` with CRLF endings keeps them; the probe checks this through
  `merge_block`.
- **A non-UTF-8 `.gitignore` refuses the sync.** `UnicodeDecodeError` is a
  `ValueError`, which `bundle.py sync` already reports as a refusal that
  changed nothing.

## For the next reader

- The marker test is a line *prefix*, `# >>> stereorepo` and
  `# <<< stereorepo`, so the rest of the opening line is free text and can be
  reworded without orphaning the block in portfolios already synced.
- `Changes.writes` holds merged bytes; a `block` destination never appears in
  `Changes.copies`, but it stays in the `copies` dict that the removal rule
  reads, which is what keeps the transition case (an old bundle listing
  `.gitignore` as plain `managed`) from removing it. The probe's
  `OLD_BUNDLE` has no `block` mark, so every sync case there is also that
  transition case.
- fitch-mvp's next sync appends a block repeating lines it integrated by
  hand; the developer removes the repeats once, outside the block (DR-316's
  last consequence). The `onboard-fitch-mvp` Flight check should mention it
  in its desk-check brief.
- `just render` cannot finish inside a seat's sandbox (it writes
  `.claude/skills/` and fails there), but it writes `ADOPT.md`,
  `.meta/disciplines.md` and `.meta/decisions.md` first, and
  `render.py --check` reports them up to date.
- A portfolio `.gitignore` that exists but is not a regular file (a
  directory) is refused in `plan`. Before, `_blocks` read it as absent and
  `apply` then failed on `write_bytes` after the copies had already run,
  leaving the portfolio partly synced. The refusal probe has a case for it.
