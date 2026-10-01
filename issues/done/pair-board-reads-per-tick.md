---
difficulty: medium
---

# Read the board once per tick of the loop

`fast-pair-tests` made the pair tests about 2.5 times faster, not the third
it aimed for. What remains is about 7,000 git processes in a run of
`pair/test_pair.py`, at about 6 ms each in a seat's sandbox, and most of
them are the loop reading the same board at the same ref several times in
one tick of `Loop.run`.

A count with a logging shim on `PATH`, after `fast-pair-tests`, found 517
`ls-tree --name-only` calls (one per stage per caller of `board.listed`),
394 `grep -l` calls (one per call of `board.families`), and hundreds of
`show <ref>:issues/...` calls re-reading the same Issue files and `ORDER`.
`board.next_ripe`, `board.running_tree`, `board.families`, `board.to_groom`
and the loop's `adopt` and Flight checks each read them again.

## Wanted

The loop reads the board at a given commit once, and every reader in the same
tick uses that reading. A commit is immutable, so a reading keyed by the
commit SHA (not the ref name) cannot go stale. The production loop then makes
fewer git calls too, not only the tests.

Concretely, in `pair/board.py`:

- The readers that take `(repo, ref)` (`listed`, `listed_by_stage`, `show`,
  `at_ref`, `order`, `families` and those built on them) resolve `ref` to a
  commit SHA and draw on one reading of `issues/` at that SHA: the stage
  listing, every Issue file's text, and `ORDER`. One way is a single
  `ls-tree -r` plus one `git cat-file --batch` per SHA; the cache, if
  module-level, is keyed by `(repo, sha)` and bounded.
- Resolving a ref costs one `rev-parse` at most; a reader given a full SHA
  needs none. Where a tick resolves the same ref many times, the loop may
  resolve it once and pass the SHA instead.
- Readers of a working tree (`read`, `locations`, `order_keeps`) stay as they
  are: a working tree is not immutable.
- `families` reads parents from the cached Issue texts rather than
  `git grep`.
- What a reader returns does not change: a ref that does not resolve (a
  branch not yet made) still reads as an empty board, a missing file as `''`
  or `None`, and nothing is cached for it. `show` of a path outside `issues/`
  may go straight to git. Moving refs such as `HEAD` are resolved on every
  call; only the reading behind the SHA is reused.

## Out of scope

Changing what the loop decides from the board, or any existing test's
assertions. Other git traffic in the loop (worktree status, commits, merges,
the gate) is left for its own Issue if it still dominates.

## Done when

- A run of `pair/test_pair.py` makes at most half the board-reading git
  calls it made before, counted with a logging shim on `PATH`; both counts
  are recorded here, and every existing test passes unchanged. (This read
  "half the git calls" of the whole run until the baseline showed board
  reads were only 28% of them; see `## Measurements`.)
- A new test shows that a second set of reads (`listed_by_stage`,
  `at_ref`, `order`, `families`) at an already-read SHA spawns no git
  process, and that after a new commit moves the same ref, the next read
  sees the new commit's board, not the old one.
- A new test shows a ref that does not resolve reads as an empty board,
  and once the ref is created, a read sees its board.
- The run's wall time in a seat's sandbox is recorded here, before and after.

## The plan

All of it is in `pair/board.py`, plus new tests in `pair/test_pair.py`;
`pair/loop.py` changes only if step 5 needs it. The board at `HEAD` here is
about 70 files and 500 KB, so reading all of `issues/` at once is cheap.

1. **Baseline.** Before touching code, run `pair/test_pair.py` once with a
   shim `git` first on `PATH` that appends its argv to a log and execs the
   real git (the one `skip_git_trampoline` picks). Record the call count, the
   split by subcommand and the wall time under `## Measurements` here.
2. **A reading of one commit.** Add a `Reading` (frozen dataclass)
   holding, for one commit, `listing: dict[str, list[str]]` (stage to sorted
   `.md` slugs, `README.md` excluded, as `listed_by_stage` builds it now) and
   `texts: dict[str, str]` (path under `issues/` to file text, for every blob
   directly inside a stage directory: Issue files and `ORDER`). Build it with
   one `git ls-tree -r <sha> -- issues/` (which gives each blob's id) and one
   `git cat-file --batch` fed the blob ids not already in a text cache keyed
   by blob id, so a new commit on `main` re-reads only the files it changed.
   Entries nested deeper than `issues/<stage>/<file>` and non-stage
   directories are left out, matching what `listed` sees now.
3. **Resolving and caching.** `reading(repo, ref) -> Reading | None`, with
   the resolving step public as `resolve(repo, ref)` for `Loop`: a ref
   that is already a 40-hex SHA is used as is; any other ref costs one
   `git rev-parse --verify -q <ref>^{commit}`, and a failure returns `None`
   (read as the empty board, never cached). Readings live in a module-level
   `OrderedDict` keyed by commit SHA alone, bounded to 64 with oldest
   evicted; blob texts likewise, bounded to a few thousand. A SHA fixes the
   whole tree, so keying without `repo` is safe and lets `self.repo` and
   `self.wt`, which share one object store, share readings.
4. **Rewire the readers.** `listed`, `listed_by_stage`, `at_ref`, `order`
   and `show` (for paths in the reading; any other path still runs
   `git show`) draw on `reading`. `families` walks `texts` for front matter
   naming `parent:`, skipping `roadmap`, instead of `git grep` plus one
   `git show` per hit. The composite readers (`running_tree`, `next_ripe`,
   `to_groom`, `unnamed`, `grooming_faults`) resolve `ref` once at the top and pass the SHA to the readers they call,
   so a call of `next_ripe` costs one `rev-parse` when its reading is
   cached. `holds` is always handed a SHA by its callers, and `children`,
   `descendants` and `waiting` make one `families` call each, so they need
   no resolving of their own. `grooming_faults` reads the old `ORDER` from
   the reading instead of its own `git show`. Return values and their order stay as they are.
5. **Measure.** Rerun step 1's count and wall time and record them. If the
   count has not halved, the remaining `rev-parse` calls on `self.main` in
   `Loop` are next: resolve `self.main` once where a method makes several
   board calls (`run`, `adopt`, `flight_refusal`, `nothing_ripe`, `groom`,
   `resume_flight`, `flight_at_desk`, `kick_back`, and the module-level
   `status_view`) and pass the SHA.
   `grooming_faults` still calls `children(tree, "HEAD", ...)` by name, since
   the pass may just have committed. Do not touch
   `Loop`'s non-board git calls.

### Tests

In `BoardTest`, wrapping `board.subprocess.run` with a counting
`mock.patch(..., wraps=subprocess.run)`:

- After one round of `listed_by_stage`, `at_ref`, `order` and `families` at
  `main`'s SHA, a second round at the same SHA makes zero calls; then a
  commit that moves an Issue and edits `ORDER` makes the next round at
  `main` return the new board.
- A branch that does not exist reads as an empty board (`listed_by_stage`
  all empty, `order` `[]`, `at_ref` `None`, `families` `{}`); after
  `git branch` creates it, the same calls return its board.
- `families` built from texts equals the old `git grep` answer on a board
  with parents in several stages and one in `roadmap` (the existing Flight
  tests cover this too).

### Risks

- **Stale reads through a moving ref.** Guarded by resolving every ref name
  on every top-level call; only SHA-keyed data is cached.
- **Process-wide cache across tests.** Every `Bench` copies one template
  repository, so many share commit SHAs; that is safe because equal SHAs mean
  equal trees, but a test that rewrites history with the same SHA and
  different content cannot exist. No test needs to clear the cache; if
  one does, expose a `_forget()` for it rather than weakening the key.
- **`cat-file --batch` parsing.** Read output by the byte sizes in each
  header, not by lines, since Issue texts contain newlines. `text=True` did
  more than decode: it used the locale's encoding and turned `\r\n` into
  `\n`, so decode as UTF-8 and apply the same newline translation, to keep
  what `parse` and `order` see unchanged.
- **Return shapes differ by reader.** `show` goes through `git()`, which
  strips its output, while `at_ref` and `order` read raw stdout. `show` from
  the reading must strip as before; `at_ref` and `order` must not.
- **Path quoting.** `ls-tree` without `-z` quotes unusual paths; use
  `ls-tree -r -z` so the reading's keys are the plain paths `at_ref` and
  `show` look up.
- **A 40-hex branch name** would be taken as a SHA. No branch here is named
  so; accepted.

## Measurements

Counted with a shim `git` first on `PATH` that logs its argv and execs Xcode's
git, on one run of `pair/test_pair.py` (165 tests, 7 skipped), in a seat's
sandbox on 2026-10-01.

| | Before | After |
|---|---:|---:|
| All git calls | 7,641 | 6,539 |
| Board reads: `show`, `ls-tree`, `grep`, `cat-file` | 2,110 | 489 |
| `rev-parse` resolving a ref for the board | 25 | 553 |
| Board reads and their resolving together | 2,135 | 1,042 |

Board traffic is down to 49% of what it was; the whole run is down to 86%.
The rest of the run is not the board: 883 `status`, 859 `commit`, 713
`diff`, 567 `add`, 600 `rev-parse HEAD` and 172 `rev-parse --git-path
index.lock`, much of it the tests' own setup through `sh()`. Halving the
whole run needs that traffic cut, which is out of scope here; see
`issues/backlog/pair-test-git-traffic.md`.

Wall time, plain run without the shim, two runs each: before 49 s and 62 s,
after 60 s and 60 s. The difference is inside the run-to-run noise of this
sandbox; at about 6 ms a process, the 1,100 fewer calls should save about
7 s, which two runs cannot resolve.

## Notes for the next reader

- The readings cache lives for the process and is keyed by commit SHA
  alone, with no repository in the key: one SHA always names one tree, and
  the developer's checkout and `worktrees/pair` share an object store. A
  ref that names no commit is never cached.
- Each ref name still costs one `rev-parse` per top-level call, which is
  what keeps a moving ref fresh. A caller making several board calls in a
  row resolves once with `board.resolve` and passes the SHA, as `Loop`'s
  methods now do. The remaining name-resolving calls in the tests come
  mostly from `children(wt, "HEAD", ...)` in `retirement` and from
  `move_underway`, one per landing try; both read a ref that has just moved.
- `families` no longer runs `git grep`; it scans the cached texts for a line
  starting `parent:` before parsing front matter.
- A blob that `cat-file --batch` cannot give raises `GitError` naming it,
  where `reading` would otherwise fail later with a bare `KeyError`; either
  way no reading with a file missing from it is cached.
