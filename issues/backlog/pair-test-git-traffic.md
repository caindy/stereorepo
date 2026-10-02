---
difficulty: medium
---

# Cut the git traffic the pair tests make outside the board

`pair-board-reads-per-tick` halved the board's own git calls, but a run of
`pair/test_pair.py` still starts about 6,500 git processes, at about 6 ms
each in a seat's sandbox. The board is now about 1,000 of them. Its
`## Measurements` (in `issues/done/pair-board-reads-per-tick.md`) lists the
rest: 883 `status`, 859 `commit`, 713 `diff`, 567 `add`, 600 `rev-parse HEAD`
and 172 `rev-parse --git-path index.lock`. Much of it is the tests' own setup
through `sh()`, such as one `add` and one `commit` per `Bench.issue`, and
some is the loop's per-turn bookkeeping.

## Wanted

Find which of those calls are repeated work, in the tests' setup or in the
loop, and remove them without changing what any test asserts, until a run of
`pair/test_pair.py` makes at most half the 6,539 calls it made after
`pair-board-reads-per-tick`, so at most 3,269.

Likely places to look, none of them required:

- Test setup that writes several files and commits each one separately, where
  one commit would do: a shared fixture repository built once
  (`board_repository()`), and helpers such as `Bench.issue` called in a row.
- The loop asking git again for something it already knows in the same tick,
  such as `rev-parse HEAD` after a commit it just made, or the lock paths
  `land` resolves with `rev-parse --git-path` on every call, which do not
  change for a checkout.

## Out of scope

- The board's reads (`pair/board.py`), which `pair-board-reads-per-tick`
  already cut.
- Changing what a test asserts, or dropping a test.
- Changing what the loop writes: in `pair/loop.py` only repeated reads may
  go (a second `status`, `diff` or `rev-parse` whose answer the loop
  already holds). Every commit, ref update and file it writes stays as it
  is, and a cached answer must not outlive a write that could change it.
- Tests outside `pair/test_pair.py`.

## Done when

- The count is measured once before any change and once after, the same way
  `pair-board-reads-per-tick` measured it (a shim `git` first on `PATH` that
  logs its argv and execs the real git, over one run of `pair/test_pair.py`
  in a seat's sandbox), and both counts, their split by subcommand, and the
  run's wall time are recorded under `## Measurements` here.
- The after count is at most 3,269.
- Every test in `pair/test_pair.py` still passes, and no assertion in it has
  changed.

## The plan

The baseline is already taken (see `## Measurements`): 8,760 calls over 209
tests, not 6,539, because 44 tests have been added since
`pair-board-reads-per-tick`. It was counted with each call tagged by the
Python frame that started it, which shows where the calls come from:

| Where | Reads | Writes |
|---|---:|---:|
| The loop (`loop.py`, `board.py`, `seats.py`) | 5,411 | 2,097 |
| The tests' own setup (`test_pair.py`) | 172 | 1,080 |

The loop's writes stay (out of scope). Of its reads, 1,004 are
`board.head_and_dirty`'s `status` (509 before each turn in
`absorb_developer`, 493 after it in `settle`), and 651 more are
`board.resolve`; both are in `pair/board.py`, and each answers a question
the loop does not yet know the answer to (has the developer or the seat
changed the worktree; where does a ref point now). What the loop asks
twice is smaller. Each step below drops one such repeated read and nothing
else, so the tests that already cover each method show it still behaves.

1. **`land`'s lock paths only when it pauses** (`pair/loop.py`, `land`).
   The two `rev-parse --git-path` calls run on every landing (418 calls)
   but `locks` is read only to name a held lock in the pause reason.
   Resolve them after the try loop, only when `land` is about to pause.
   Covered by the existing tests that pause on a held `index.lock` or
   `main.lock` and assert the lock's path in the reason. About −410.
2. **`settle`'s second diff after its own commit** (`settle`). When
   `head_and_dirty` reported `head == st.head` and `settle` then committed
   staged changes (its `diff --cached` was non-empty), the new `HEAD`
   differs from `st.head` by exactly those changes, so the turn is not
   quiet without asking `git diff st.head HEAD`. Skip that diff in that
   case only; when the seat committed itself, the diff still runs. The
   existing quiet-turn tests cover a seat that writes nothing; add one where
   a seat commits an edit and leaves its revert uncommitted, which must
   still read as quiet. At most −198.
3. **`message`'s diff when nothing can have changed** (`work`,
   `message`). After `absorb_developer` runs (the turn was not
   interrupted), `st.head` is `HEAD`; a role whose `st.seen[role]` equals
   it gets "Nothing has changed since your last turn." without
   `git diff`. Pass that knowledge from `work` rather than assuming it in
   `message`, since an interrupted turn skips `absorb_developer`. No test
   asserts that sentence yet: add one where a seat's second turn follows
   two quiet turns and its message says it, and one where the other seat
   wrote in between and its message carries the diff. At most −257.
4. **Measure** once more the same way and record it.

Expected after: about 7,900–8,000, a cut of under 10%. Nothing in the
tests' setup is planned: the 616 calls from `Bench.issue` are one `add` and
one `commit` per Issue, and folding a test's several `issue` calls into one
commit changes `main`'s history, which tests read back (`main~1`, log
lengths, `rev-parse main`); that is changing what they assert in all but
name.

### Risks

- Step 2 must not skip the diff when the seat made its own commit in the
  turn as well as leaving edits; the condition is the pre-commit `head`
  being `st.head`, not "`settle` committed".
- Step 3 must not skip on the interrupted path (`st.in_turn == role`),
  where `absorb_developer` did not run and `st.head` may lag `HEAD`.

# Needs elaboration

The target cannot be met as scoped. Even counted against today's larger
suite, half is 4,380, and the loop's writes alone (2,097) plus the tests'
setup writes (1,080) plus the per-turn `status` reads (1,004) come to
4,181 before any `diff`, `rev-parse`, `merge-base` or board read the loop
needs. The repeated reads the plan finds are worth under 900. The
developer needs to choose one of:

- **Lower the target** to what the plan reaches, for example "at most
  8,000 calls over the current 209 tests", and keep the scope as it is.
- **Widen the scope** to let the loop stop asking `status` before each
  turn, or stop committing its own bookkeeping as separate commits; both
  change what the loop writes or when it notices the developer's edits,
  which the scope now forbids.
- **Aim at wall time instead.** The run took 96 s in a seat's sandbox with
  the shim; running the test classes in several processes would cut wall
  time far more than any count of git calls here, and is a separate Issue.

## Measurements

Counted with a shim `git` first on `PATH` that logs its argv and execs
Xcode's git, plus a tag naming the Python caller of each call, on one run
of `pair/test_pair.py` (209 tests, 7 skipped) in a seat's sandbox on
2026-10-02.

| | Before | After |
|---|---:|---:|
| All git calls | 8,760 | |
| `status` | 1,164 | |
| `commit` | 1,062 | |
| `diff` | 1,020 | |
| `rev-parse HEAD` | 760 | |
| `add` | 679 | |
| `rev-parse --verify` | 653 | |
| `rev-parse --git-path` | 418 | |
| `merge-base` | 405 | |
| `ls-tree` | 366 | |
| `checkout` | 338 | |
| `mv` | 317 | |
| `rev-parse main` | 251 | |
| `symbolic-ref` | 223 | |
| `merge` | 221 | |
| `cat-file` | 194 | |
| `worktree` | 154 | |
| everything else | 535 | |
| Wall time, with the shim | 96 s | |
