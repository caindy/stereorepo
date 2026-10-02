---
difficulty: medium
parent: onboard-fitch-mvp
---

# A sync never overwrites a portfolio's ratchet baselines

The five ratchet baselines, `.meta/checks/{comments,suppressions,types,lines,file_sizes}.baseline.yaml`,
sit in `.meta/checks/`, a managed directory of `.meta/bundle.yaml`. Each sync
of fitch-mvp overwrote its comment baseline (418 existing comments across 27
files) with stereorepo's. The developer had to restore it from git each time.

A portfolio's baseline holds two kinds of entry. Some are for managed files,
which stereorepo writes. The rest are for the portfolio's own files, which
only the portfolio writes. Stereorepo's baselines today hold only the first
kind: every path-keyed entry is under `.meta/`. So keeping the portfolio's
file whole is no fix either. Its entries for managed files would go stale as
soon as stereorepo changes those files, and its ratchet would fail them.

## Wanted

Copying the bundle's managed items into a portfolio replaces the baseline
entries for managed files and keeps every other entry. The suggested shape is
to split each baseline in two. A managed baseline ships with the bundle and
holds stereorepo's entries. A portfolio baseline sits outside any managed
path, and the bundle never lists it. Each ratchet reads both. Any other shape
that gives the same behaviour will do.

`suppressions.baseline.yaml` holds two kinds of key. The `suppression causes`
step reads path keys, which behave like every other baseline. The
`repeated suppressions` step reads group keys (a rule and a reason, written
with ` — `). A group can have sites in both managed and portfolio files, so
its allowed count is the sum of the two baselines' entries.

A path entry belongs in exactly one baseline. The managed baseline holds the
paths under a managed item of `.meta/bundle.yaml`, and the portfolio baseline
holds every other path. A scaffold-only path (`lib.bundle.SCAFFOLD_ONLY_PATHS`)
is never copied, so even inside a managed directory it belongs in
stereorepo's portfolio baseline. A path in the wrong baseline fails the ratchet and
names the baseline it belongs in. Without this, a stale portfolio entry for a
managed file would add to stereorepo's count rather than being replaced by it.

## Out of scope

- The sync recipe itself (`sync-portfolio-recipe`, which waits on this).
- Moving fitch-mvp's existing entries into the new shape. The developer does
  that at the next sync.

## Done when

- A test copies `managed_items()` over a portfolio whose baselines carry an
  entry for a portfolio-only file and a stale count for a managed file. After
  the copy, the portfolio-only entry is unchanged and the managed file's entry
  is stereorepo's.
- A test shows a ratchet accepting a tree whose counts come from both
  baselines: one path from each, and one suppression reason that both hold,
  allowed the sum.
- The ratchet still fails when a count rises or falls. For a path, the
  failure names the baseline that holds the path. For a group, it names both
  baselines.
- A test shows a ratchet failing a portfolio baseline that holds a path
  under a managed item.
- `.meta/test_specialization.py` still passes. A fresh portfolio starts with
  an empty or absent portfolio baseline, and its ratchets accept it.

## The plan

The portfolio baselines go in a new directory, `.meta/baselines/`, which no
item of `.meta/bundle.yaml` lists or contains. A copy of `managed_items()`
therefore never touches them. The managed baselines stay where they are, in
`.meta/checks/`.

1. **Decide which baseline owns a path.** Add `Bundle.manages(relative)` to
   `.meta/lib/bundle/__init__.py`. It is true when a managed item's
   `dest_path()` is the path or one of its parent directories, and the path
   is not under `SCAFFOLD_ONLY_PATHS`.
2. **Read and compare a pair of baselines.** In `.meta/checks/collect.py`,
   a frozen `Baselines(managed, portfolio)` replaces the single path.
   - `recorded_baseline` reads each file of the pair into its own map, and a
     missing file reads as empty. The maps stay separate as far as
     `against_baseline`, because only they say which file an entry came from.
     For group keys (which contain ` — `) a merge sums the two counts.
   - `against_baseline(counts, sites, baselines, noun, manages=None)` takes a
     `Baselines`. For a path that is over or under its count, the failure
     names the file the path belongs in. A path entry in the wrong file is a
     failure of its own, naming the right file. `manages` is a predicate on a
     relative path. It defaults to `Bundle.manages` over the real bundle,
     loaded lazily the way `sources.inherited()` loads it. The probes pass
     their own predicate so that they do not depend on what the real bundle
     lists.
   - The special case for `SPECIALIZE.md` and `.meta/test_specialization.py`
     in a portfolio is deleted. Those entries now live in stereorepo's
     portfolio baseline, which no copy brings, so the case no longer arises.
3. **Point every step at the pair.**
   - `.meta/checks/comments.py` reads `BASELINE` and `SUPPRESSIONS_BASELINE`
     as pairs.
   - `against_repeats` reads the summed group counts. Its failure names both
     files.
   - `.meta/checks/files/python.py` does the same for `LINES_BASELINE`,
     `FILE_SIZES_BASELINE` and `TYPES_BASELINE`. No step reads
     `TYPES_BASELINE`, but `_type_errors` and `_ruff_findings` in
     `.meta/checks/probes/tools/comments.py` pass `TYPES_BASELINE` and
     `LINES_BASELINE` straight to `against_baseline`, so they follow too.
   - Each step's `CouldNotRun` for a missing file applies only to the managed
     file. A missing portfolio file is normal.
   - The re-exports in `.meta/checks/files/__init__.py` follow.
4. **Split stereorepo's own baselines.** Each entry moves by
   `Bundle.manages`. Entries for paths a copy brings stay in
   `.meta/checks/*.baseline.yaml`. The rest move to
   `.meta/baselines/*.baseline.yaml`, for example
   `.meta/test_specialization.py`'s entries in `file_sizes` (120) and
   `lines` (0). Group keys stay in the
   managed file. Their sites all lie in managed files today: `.meta/check.py`
   and the `__init__.py` of `checks/{citations,graph,probes,probes/tools,files}`,
   none of them scaffold-only.
   The new files and a `.meta/baselines/README.md` are registered as
   artifacts in `.meta/assertions/structure.yaml`.
5. **Record the decision.** Add a new DR naming the two-file split and where
   each kind of entry goes, and re-render. Update the header comment of each
   baseline file and the docstrings of `comments.py` and `collect.py` that
   name a single baseline file.

### Tests

- `.meta/checks/probes/tools/comments.py`
  - `_ratchet` and `_repeat_ratchet` move to `Baselines` pairs written in a
    temporary directory.
  - New cases: one path counted from each file passes; a group that both
    files hold is allowed the sum; a portfolio entry for a managed path fails
    and names `.meta/checks/…`; a managed entry for a portfolio path fails
    and names `.meta/baselines/…`; an absent portfolio file over a clean tree
    passes; an over-count failure names the owning file for a path and both
    files for a group.
- `.meta/checks/probes/tools/test_specialization.py`, beside
  `_check_scaffold_only`: a temporary scaffold and a temporary portfolio,
  using `runner._copy_item` over `managed_items()`. The portfolio's
  `.meta/baselines/comments.baseline.yaml` names a portfolio-only file, and
  its `.meta/checks/comments.baseline.yaml` holds a stale count for a managed
  file. After the copy, the first is byte-for-byte unchanged and the second
  is the scaffold's. A second assertion checks that no managed item of the
  real bundle contains `.meta/baselines/`.
- `.meta/test_specialization.py` runs end to end. The fresh portfolio has no
  `.meta/baselines/`, and its ratchets pass.

### Where the work departed from the plan

- `manages` is a field of `Baselines`, not a sixth argument of
  `against_baseline`. Ruff's argument limit (PLR0913) refuses six, and the
  pair is what knows which file owns a path. `Baselines.owner()` falls back
  to `collect.bundle_manages()`, and the probes pass a fake bundle through
  `dataclasses.replace`.
- `against_baseline` takes what `Baselines.recorded()` returns, the
  `collect.Recorded` pair of maps, not a pair of files. The probes therefore
  build dicts in memory and write no files, except one case that reads an
  absent portfolio file.
- Group keys are summed by `collect.summed(recorded, groups=True)`, not by a
  function in `comments.py`. That file sits at its size ceiling, and
  `against_baseline` uses the same function for paths
  (`groups=False`), which also drops the group keys `suppression causes` used
  to filter out by hand.
- `.meta/baselines/` has no README. It holds `file_sizes.baseline.yaml`,
  whose header explains the directory, and a fresh portfolio has no
  directory at all.
- `lines.baseline.yaml`'s `.meta/test_specialization.py: 0` was dropped
  rather than moved. A zero entry allows nothing an absent one does not.

## Notes

- Stereorepo's split came to one moved entry:
  `.meta/test_specialization.py: 120` in `file_sizes`. Every other path
  entry is for a managed file.
- The new probes were checked against broken code. With `misplaced`
  returning nothing, `_two_baselines` reported 2 problems. With group counts
  taken from the managed file alone, `_repeat_ratchet` reported 1.
  `just test-specialization` passes all 9 steps, with no `.meta/baselines/`
  in the fresh portfolio.
- `comments.py` fell by one line against both its file-size and line-length
  baselines, and both were lowered to match.
- `just render` updated `.meta/decisions.md` for DR-314, then stopped when
  the seat's sandbox refused it write access to `.claude/skills/`. That is
  `render-in-seat-sandbox` in the backlog. The meta gate's `rendered prose`
  step passes, so nothing it checks is stale.
- A stale entry (a path whose file is gone) names the baseline that holds
  it and says to delete the entry. Before, it said only "baseline holds a
  file that does not exist", which left the reader to guess between two
  files. `_two_baselines` probes the portfolio case.
- fitch-mvp must move its own entries into `.meta/baselines/` at its next
  sync. That sync replaces its `.meta/checks/*.baseline.yaml` once more, and
  each of its own files then fails with "write N in
  .meta/baselines/<name>.baseline.yaml", so the failures say what to write.
  After that, no sync touches those entries.

### Risks

- **Import graph.** `collect.py` importing `lib.bundle` must not trip the
  import-graph check (DR-150). Use the same deferred import as
  `sources.inherited()`, and fall back to "everything is managed" when the
  bundle cannot load.
- **Whether the portfolio directory gets copied.** A fresh portfolio must not
  get stereorepo's `.meta/baselines/`. Confirm that step 2 of
  `test_specialization.py` copies only bundle items, and that `.meta/` itself
  is not an item.
- **Merge order of group keys.** The `repeated suppressions` step filters
  group keys out of the merged map. Summing has to happen before that
  filter, or a group held in both files would be counted once.
