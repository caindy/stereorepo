# Cut the git traffic the pair tests make outside the board

`pair-board-reads-per-tick` halved the board's own git calls, but a run of
`pair/test_pair.py` still starts about 6,500 git processes, at about 6 ms
each in a seat's sandbox. The board is now about 1,000 of them. Its
`## Measurements` lists the rest: 883 `status`, 859 `commit`, 713 `diff`,
567 `add`, 600 `rev-parse HEAD` and 172 `rev-parse --git-path index.lock`.
Much of it is the tests' own setup through `sh()`, such as one `add` and one
`commit` per `Bench.issue`, and some is the loop's per-turn bookkeeping.

## Wanted

Find which of those calls are repeated work, in the tests' setup or in the
loop, and remove them without changing what any test asserts, until a run of
`pair/test_pair.py` makes at most half the 6,539 calls it made after
`pair-board-reads-per-tick`.
