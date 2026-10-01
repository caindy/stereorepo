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

## Out of scope

Changing what the loop decides from the board, or any test's assertions.

## Done when

- A run of `pair/test_pair.py` makes at most half the git calls it made
  before, counted with a logging shim, and all its tests pass unchanged.
- The run's wall time in a seat's sandbox is recorded here, before and after.
