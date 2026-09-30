---
difficulty: medium
parent: backlog-grooming-and-ranking
waits_on: backlog-running-order
---

# Groom the whole backlog before taking the next Issue

The loop grooms an Issue only when it picks it up. Nothing looks at the
backlog as a whole, which is the only place priority can be judged. This part
adds a grooming pass to the loop that grooms every backlog Issue and writes
the ranking below the marker in `issues/backlog/ORDER` (the format
`backlog-running-order` defines).

## Wanted

- **When it runs.** Before `run` starts the next Issue, the supervisor
  compares each `issues/backlog/*.md` file on `main` (not `README.md`) with
  what the last pass left, recorded in `.pair/` as path to blob id. If any
  file is new or its content differs, a pass runs first. A file that only
  left the backlog does not trigger one, and neither does an edit to `ORDER`
  alone. With no record, a pass runs if the backlog holds any file. The record is written from `main` when
  the pass has landed, so the pass's own edits do not start another. The loop's
  own send-back (`kick_back`) also updates the record for the file it writes,
  so a send-back waits for the next pass something else starts, or for the
  developer's edit. Otherwise a round-cap overrun could be groomed and taken
  straight back up, over and over.
- **What the seats do.** A new prompt, `pair/prompts/stage-grooming.md`, asks
  the seats to groom every Issue in `issues/backlog/` as `stage-backlog.md`
  asks for one: precise enough to plan, with a `difficulty`, split if `hard`,
  a `# Needs elaboration` section if it cannot be done as written, and for a
  bug report, how to reproduce it. They may remove a `Needs elaboration`
  section they have answered. Unlike in a stage, a `Needs elaboration`
  section written during the pass does not end it or send anything back; the
  Issue simply sits out of `next_ripe`. They rank the backlog below the
  `# groomed below` marker, judged across the whole backlog, and leave the
  lines above it alone. They do not delete a backlog Issue, move one out of
  `backlog/`, or touch `issues/roadmap/`. Children that a per-Issue backlog
  stage writes are new backlog files, so they start a pass before the next
  Issue; that is intended.
- **How it ends.** The same agreement rule as a stage, on its own branch in the
  shared worktree. The supervisor holds the result, and hands anything missing
  back to the seats as it does for a stage: every backlog Issue has a valid
  `difficulty`; every `hard` Issue has children in `backlog/`; below the
  marker, every backlog slug not named above it appears exactly once, and
  nothing else does; the lines above the marker are `main`'s; every backlog
  file on `main` is still in `backlog/`; nothing under `issues/roadmap/` or
  outside `issues/` changed. With no `ORDER` on `main`, the pass writes one
  that starts with the marker. With an `ORDER` that has no marker, which is
  all the developer's, the pass keeps its lines and adds the marker after
  them. Once the pass settles, the supervisor moves each `hard` Issue to
  `done/`, as the backlog stage does now, and removes its lines from `ORDER`
  (above the marker too) with `board.without`. The pass lands on `main` as
  one squash commit, with the landing path Issues use.
- **Past the round cap.** The pass's cap is the `medium` cap in `ROUND_CAP`,
  and the loop's `round_cap` override applies to it as it does to a stage. A
  pass that does not settle within it pauses the loop for the developer rather
  than sending anything back.
- **Restarts.** A pass in flight is kept in `.pair/state.json` and resumes
  after a restart, as an Issue does.
- **Status.** `just pair-status` says when a grooming pass is in flight.

## Out of scope

- Removing or shortening the per-Issue backlog stage.
- A different model for the pass (`seat-models-per-stage`).

## Done when

- Pair tests with scripted seats show: a new backlog file causes one pass
  before the next Issue is taken; an unchanged backlog, or one that only lost
  a file, causes none; a send-back by the loop causes none; a pass that
  changes a line above the marker, or deletes a backlog Issue, is not
  accepted; a pass over a board with no `ORDER` writes one with the marker; a
  `hard` Issue split in the pass lands in `done/` with its children ranked and
  its own slug gone from `ORDER`; a pass that writes `Needs elaboration` into
  an Issue lands, and that Issue stays in `backlog/`; a pass past its cap
  pauses; a pass interrupted by a restart resumes; and a settled pass lands as
  one commit and records the backlog.
- `just gate` passes.

## The plan

The pass reuses the Issue machinery: one `State`, the same turn loop, the same
rebase, squash and land. It differs only where the pass has no Issue file.

### Steps

1. **`pair/board.py`: the record and the rules.**
   - `backlog_blobs(repo, ref) -> dict[str, str]` maps each
     `issues/backlog/*.md` path at `ref` (not `README.md`) to its blob id, read
     with `git ls-tree`.
   - `stale(blobs, record) -> bool` is true when there is no record, or when
     any path in `blobs` is missing from `record` or has a different blob.
     Paths only in `record` do not count.
   - `grooming_faults(tree, repo, ref) -> list[str]` holds the rules for
     *How it ends*, one sentence per fault, and an empty list means the pass
     is finished. It compares the worktree with `ref`, which is `st.base`, the
     `main` commit the pass started from, and not `main` itself. If the
     developer edits `ORDER` or adds a backlog file on `main` mid-pass, a
     comparison with `main` would report faults the seats cannot see or fix
     (lines above the marker that differ, a backlog file missing from the
     tree), and the pass could never settle. `main`'s changes arrive at the
     rebase in `merge`, and step 5 keeps them out of the record:
     - every backlog Issue in `tree` has a valid `difficulty`;
     - every `hard` Issue has `children`;
     - every backlog `.md` at `ref` is still in `backlog/` in `tree`;
     - `git diff --name-only <ref> HEAD` in the tree touches only `issues/`,
       and nothing under `issues/roadmap/`;
     - the lines above the marker are `ref`'s, or all of `ref`'s lines when
       `ref` has an `ORDER` with no marker, or none when it has no `ORDER`;
     - `ORDER` has the marker;
     - below the marker, each backlog slug not placed above it appears once,
       and nothing else does.

     `order` stays as it is. A small `split_order(text) -> (above, below)`
     helper serves the faults.
2. **`pair/loop.py`: state.** Add the constant `GROOMING = "grooming"`. A pass
   is `State(slug=GROOMING, stage=GROOMING)`. Add `base: str = ""` to `State`
   (the `main` commit the pass started from). Defaults keep old `state.json`
   files loadable. `Loop.__init__` takes `groom: bool = True`. The record lives
   in `.pair/groomed.json`, and `record_groomed` / `load_groomed` read and
   write it.
3. **`run`.** When there is no state, check `self.groom` and
   `board.stale(board.backlog_blobs(repo, main), load_groomed())`. If both
   hold, call `start_grooming()`. Otherwise call `next_ripe` as now.
   `start_grooming` shares the clean-worktree check, the checkout of
   `pair/grooming` from `main`, and the session reset with `start_issue`. The
   shared part becomes one `start(st)` helper. It also sets `st.base`. The
   outcome `"groomed"` does not end a `--once` run, because `--once` counts
   Issues.
4. **The turn loop, where a pass differs.**
   - `settle` skips the issue-file relocation when `st.stage == GROOMING`.
   - `decide` skips the `issue is None or needs_elaboration -> kick_back`
     check for a pass. Its cap is `self.round_cap or ROUND_CAP["medium"]`.
     Past the cap it calls `pause(..., retry="grooming")` and never
     `kick_back`.
   - In `work`, `retry == "grooming"` resets `st.turn` to 0 and carries on.
     The developer's edits are absorbed as usual, so `just pair` after the
     pause gives the pass another cap's worth of turns.
   - `decide` reads no Issue for a pass (`board.read` gives `None` for the
     slug `grooming`), so `requirement` and `advance` take the pass branch
     before they touch `issue`.
   - `requirement` for a pass joins `grooming_faults(self.wt, self.wt,
     st.base)` into one note. When there
     are no faults, it runs `self.gate(self.wt)` as the in-progress stage
     does. The pass touches only `issues/`, so `merge` would skip the gate,
     but the board checks (`board front matter`, `board order`) live in it.
5. **`advance` and landing for a pass.** For each `hard` backlog Issue in the
   worktree, `git mv` it to `done/` and rewrite `ORDER` with `board.without`.
   Make one `Seat: loop` commit, then call `merge`. In `merge`, skip the
   `move(st, "done")` for a pass. `squash` gives a pass the title
   `Groom the backlog`, no `Issue:` trailer, and no `ORDER` removal. After
   `land`:
   - Write the record from `backlog_blobs` at the landed commit, but leave out
     every path that changed on `main` between `st.base` and the `main` the
     pass was rebased onto (`git diff --name-only`). An edit the developer
     made during the pass was never groomed, so it must start the next pass.
     `merge` takes the rebase target, `onto`, before `squash` and passes it
     to `groomed`. `sha^` would be wrong for a pass that changed nothing:
     both seats accept the backlog as it stands, the index is empty after
     `reset --soft`, and `squash` makes no commit (`git commit` would fail).
     Nothing lands, and the backlog is still recorded.
   - Delete `pair/grooming` and return `"groomed"` from `merge`. This happens
     inside `merge` rather than after it, so a pass paused with
     `retry="merge"` still writes the record when it lands.
6. **`kick_back`.** After a successful `land`, if a record exists, set its
   entry for the file just written to that file's blob on `main`. With no
   record, a pass runs anyway.
7. **`message`.** `stage-grooming.md` is formatted with
   `path="issues/backlog/"`. The "first turn on this issue" wording becomes
   "first turn here", so it reads right for both.
8. **`pair/prompts/stage-grooming.md`.** Say what *What the seats do* says,
   as briefly as `stage-backlog.md`: groom every Issue as `stage-backlog.md`
   asks, rank below `# groomed below` (create `ORDER` or the marker if
   missing), leave the lines above it alone, and do not delete, move or touch
   `issues/roadmap/`. Say that a `Needs elaboration` section parks an Issue
   and does not end the pass.
9. **`status`.** When the stage is `grooming`, print
   `in flight: grooming pass, turn N, ...` in place of the Issue line.
10. **Words.** Update the `pair/loop.py` module docstring, and add one
    paragraph to `pair/README.md` describing the pass. The rest of that README
    stays with `backlog-and-roadmap-words`.

### Tests (`pair/test_pair.py`)

`Bench` passes `groom=False`, so the existing tests are unchanged. A new
`GroomingTest` sets `b.loop.groom = True`. Its tests:

- A new backlog file with no record: one pass (both seats rank, then both are
  quiet) lands as one commit titled `Groom the backlog`. Then the Issue is
  taken and lands. `.pair/groomed.json` matches `main`'s backlog.
- Unchanged backlog: after a recorded pass, the next run takes the Issue with
  no pass turns. After that Issue lands (its file left `backlog/`), there is
  still no pass.
- A loop send-back (`Needs elaboration` in the todo stage) is followed by the
  next Issue, with no pass.
- A seat edits a line above the marker, then both are quiet: the pass does not
  land, and the next message names the fault. The same holds for a seat that
  deletes a backlog Issue.
- No `ORDER` on `main`: the landed `ORDER` starts with `# groomed below`. An
  `ORDER` with no marker keeps its lines, followed by the marker.
- A `hard` Issue split in the pass: it lands in `done/`, its children are
  below the marker, and its slug is gone from `ORDER`, including a line above
  the marker.
- A pass that adds `Needs elaboration` to an Issue lands. The Issue stays in
  `backlog/`, and `next_ripe` passes over it.
- `round_cap=1` with the seats disagreeing: `run` returns `"paused"`. A
  second `run` carries on with a fresh cap.
- `stop_when_empty` mid-pass, then `run` again: the pass resumes and lands.
- The developer commits a backlog edit on `main` mid-pass: the pass lands, the
  edited path is missing from the record, and the next `run` starts another
  pass. A developer edit on `main` mid-pass to a line above the marker in
  `ORDER`, and not next to it (adjacent hunks conflict at the rebase), does not stop the pass settling (the rule compares with
  `st.base`), and the edit lands with it.
- `status` shows `grooming pass` for a pass in flight.

`BoardTest` gains direct cases for `stale` and `grooming_faults`, one per
fault, plus a clean board.

### Risks

- **Cost.** Every change to the backlog costs a whole-backlog pass, and its
  diffs can be long. `DIFF_LIMIT` already truncates them. The first real run
  after this lands grooms all eleven current Issues.
- **Mid-pass edits on `main`.** The rebase in `merge` can conflict with the
  pass. It then pauses like an Issue. Leaving changed paths out of the record
  (step 5) is what stops an ungroomed edit being marked as groomed.
- **The slug `grooming`.** An Issue named `grooming` would share the branch
  name. Only one thing is ever in flight and the branch is deleted on
  landing, so nothing collides.
- **Squash title.** `squash` and `merge` read `board.read(self.wt, st.slug)`.
  With no Issue file this falls back to the slug. Step 5 makes that fallback
  explicit, so a pass never picks up a title by accident.

## Notes for the next reader

- **The first real run grooms everything.** No `.pair/groomed.json` exists
  yet, so the first `just pair` after this lands runs a pass over the whole
  backlog before it takes an Issue.
- **`Bench` passes `groom=False`.** Every `LoopTest` starts with backlog
  Issues and no record, so with grooming on, each would begin with a pass.
  `GroomingTest` turns it on. Its Issues mostly carry `waits_on: [z]`, so a
  run ends at `"empty"` after the pass instead of taking an Issue with no
  scripted turns.
- **Which rules check what.** `grooming_faults` compares with `st.base`, and
  `ORDER` completeness is checked only there. A backlog file added on `main`
  mid-pass can land missing from `ORDER`. The gate's `board order` step does
  not require completeness, `next_ripe` takes unlisted Issues after the
  listed ones, and the file is not in the record, so the next pass ranks it.
- **An empty backlog is never stale.** With no record, `stale` is true only
  when the backlog has a file. Otherwise a fresh clone, or a specialized
  portfolio with an empty board, would spend a pass writing an `ORDER` that
  holds nothing but the marker.
- **A cap pause keeps its approvals.** A pass paused at its cap resumes with
  `st.turn = 0`, and its approvals and note stay as they were. The first
  turn after the resume is told what was still missing.
