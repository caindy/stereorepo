# Make the pair tests fast

`just gate pair` runs the 141 tests in `pair/test_pair.py` and takes 136
seconds on `main`, of which only about 109 seconds is CPU time, most of it
system time. Most of the cost looks like starting processes, git above all,
while each test builds its repository. No single test dominates: `LoopTest`
takes 59 seconds and `FlightCheckTest` 41, at 1 to 5 seconds a test, and the
slowest, `test_reap_stops_only_an_orphaned_seat_in_this_worktree`, takes 10.6
seconds.

## Why it matters

The seats run `just gate pair` two or three times per in-progress turn on any
Issue that touches `pair/`, and the loop runs it again inside the full
`just gate` before landing. On 2026-10-01, between 10:59 and 13:20, the seats
spent 43 of 132 minutes of turn time on the pair tests: 35 minutes in 18 runs
of `just gate pair` and 8 in direct `unittest` runs. The model spent 49
minutes thinking and writing in the same turns. The timings come from the
`timestamp` of each tool call and result in `.pair/primary.jsonl` and
`.pair/secondary.jsonl`, in the developer's checkout.

## Wanted

- Find where the time goes in a test's setup, and cut it. One likely way:
  build each kind of fixture repository once, and give each test a copy,
  instead of running `git init` and a series of commits per test.
- Make the reap test fast, without weakening what it checks.
- Keep every test's assertions as they are; this changes how fixtures are
  built, not what is tested.

## Out of scope

The other Projects' gates, and running tests in parallel.

## Done when

`just gate pair` passes on the same tests, and its wall time on the
developer's machine is under 30 seconds. The Issue file records the time
before and after.
