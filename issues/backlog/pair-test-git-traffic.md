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
