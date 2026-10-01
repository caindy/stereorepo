---
difficulty: medium
---
# Make the pair tests fast

The `pair/test_pair.py` tests (141 when measured; 153 at grooming) took 136
seconds on `main`, of which only
about 109 seconds is CPU time, most of it system time. No single test
dominates: `LoopTest` takes 59 seconds and `FlightCheckTest` 41, at 1 to 5
seconds a test, and the slowest,
`test_reap_stops_only_an_orphaned_seat_in_this_worktree`, takes 10.6 seconds.

## Why it matters

The seats run the pair tests two or three times per in-progress turn on any
Issue that touches `pair/`, and the loop runs them again before landing. On
2026-10-01, between 10:59 and 13:20, the seats spent 43 of 132 minutes of turn
time on the pair tests: 35 minutes in 18 gate runs and 8 in direct `unittest`
runs. The model spent 49 minutes thinking and writing in the same turns. The
timings come from the `timestamp` of each tool call and result in
`.pair/primary.jsonl` and `.pair/secondary.jsonl`, in the developer's checkout.

## Where the time goes (measured while grooming)

- **Git process starts.** With a logging shim on `PATH`, `LoopTest` (35 tests,
  38 seconds in a seat's sandbox) made 2,320 git calls: 468 `rev-parse`, 304
  `status`, 238 `commit`, 201 `diff`, 174 `show`, and so on. At about 16 ms a
  call, those calls account for nearly all of the class's time. Each test
  spends only about 10 calls building its `Bench` (`git init`, three
  `config`, `add`, `commit`, then two per `Bench.issue`); the rest are the
  loop's own calls.
- **The macOS git trampoline.** `/usr/bin/git` is an `xcrun` shim. Fifty
  `git rev-parse --git-dir` calls take 0.52 s through it and 0.14 s through
  the binary it resolves to (`xcrun -f git`). Global config has no measurable
  effect.
- **The reap test waits out a zombie.** The test starts the "orphan"
  `sleep` as its own child, so after `Loop.reap` sends SIGTERM the process
  stays a zombie that the test has not reaped. `Loop.alive` (`os.kill(pid, 0)`)
  counts it as alive, so `reap` polls for its full 10 seconds before it sends
  SIGKILL. A real orphaned seat is not the supervisor's child, so the
  production path does not hit this wait.

## Wanted

- Cut the per-call cost of git in the tests. For example, the pair tests can
  resolve the real git binary once (for example with `xcrun -f git` where it
  exists) and put its directory first on `PATH` for the test run. Whatever
  you choose must also work where `xcrun` does not exist.
- Cut the git calls spent building fixtures. For example, build each kind of
  fixture repository once per class or module, and give each test a copy.
- Make the reap test fast without weakening it. For example, start the orphan
  so that it is not the test's child, as a real orphaned seat is not. The
  test must still check that the seat in this worktree is stopped and that
  the process elsewhere is left running.
- Optionally, cut redundant git calls in `pair/` itself where one call can
  do the work of several. This must not change behaviour.
- Keep every test and its assertions. This Issue changes how the tests run
  and how fixtures are built, not what is tested.

## Out of scope

The other Projects' tests and gates. Running tests in parallel. Changing what
any test asserts.

## Done when

- `pair/test_pair.py` runs the same tests it ran at the start of this Issue
  (153, counted by `unittest` discovery) with the same assertions, and all
  of them pass.
- The developer accepts the saving as measured under "What was done", about
  2.5 times faster, in place of the earlier targets of a third and of under
  30 seconds (2026-10-01, 14:45). Run no more timing comparisons or
  benchmarks in this Issue: review the change for correctness, run the
  targeted gates once, and finish. Further speed-ups go in a new Issue in
  `issues/backlog/`.
- The reap test takes under 1 second.
- This file records the wall time before and after, and which changes
  produced the saving.

## The plan

All changes are in `pair/test_pair.py`, and `pair/loop.py` only if step 5
runs. Every git call, in the tests and in `pair/` (`board.git`, `seats.py`,
`loop.py`), runs `"git"` by name through `PATH`, and `pair/gate.py` imports
the test module. So one change at module level reaches both the gate and a
direct `unittest` run.

1. **Baseline.** Before any change, run
   `python3 -m unittest test_pair` from `pair/` in the seat's sandbox under
   `time`, and record the wall time, the test count and the skips here.
2. **The real git first on `PATH`.** Add a module-level function to
   `test_pair.py`, called once at import before `INSPECTS`. It acts only when
   `shutil.which("git")` is `/usr/bin/git`, the `xcrun` trampoline. It runs
   `xcrun -f git` and, when that succeeds, prepends the directory of the
   resolved git to `os.environ["PATH"]`. Where `xcrun` is missing or fails,
   or `git` already resolves elsewhere (Linux, or Homebrew git first), it does
   nothing. So a developer's chosen git is never swapped for Apple's. Child
   processes inherit `os.environ`, so the loop's calls speed up too. Measure.
3. **One template repository for `Bench`.** `Bench` is the only repository
   fixture that many tests share: nine classes and about 20 `BoardTest`
   methods construct it. Split `Bench.__init__`'s `git init`, the three
   `config` calls, the stage READMEs and the `board` commit into a function
   that builds them once per process, cached, in a module-level
   `TemporaryDirectory`. `Bench.__init__` then copies it with
   `shutil.copytree(template, self.repo, symlinks=True)` in place of its
   `mkdir`, because `copytree` requires that the destination not exist. The template has no
   worktrees, so its `.git` holds no absolute paths and a copy is a complete
   repository. Every test then starts from the same `board` commit SHA, which
   no test depends on either way. `ConfinementTest` keeps its own setup,
   because it has few tests and needs worktrees. Measure.
4. **The reap test.** Start the orphan so that it is not the test's child:
   `subprocess.run(["sh", "-c", "sleep 60 >/dev/null 2>&1 & echo $!"],
   cwd=b.loop.wt, capture_output=True, text=True)` returns the pid of a
   `sleep` that `launchd` adopts and reaps once it dies. The redirection
   matters: without it the backgrounded `sleep` holds the captured stdout
   open, and `run` waits the full 60 seconds for end of file. The `sleep`
   inherits `sh`'s working directory, so `Loop.owns` still matches it by
   command and by worktree. Clean up with `os.kill(pid, SIGKILL)`,
   suppressing `ProcessLookupError`. Replace `orphan.wait(timeout=10)` with
   a poll of `Loop.alive(pid)` for up to a few seconds, asserting that it
   turns false. A single check right after `reap` returns is not enough:
   after the SIGTERM path `alive` is already false, but after the SIGKILL
   path `reap` returns before `launchd` has reaped the process. The
   `elsewhere` process and its `assertIsNone(elsewhere.poll())` stay as
   they are. This test skips in the sandbox, so its timing (under 1 second)
   is for the developer's run.
5. **Only if steps 2 to 4 miss a third of the baseline:** count git calls by
   subcommand with a logging shim on `PATH` (as in grooming), and merge
   repeated calls in `loop.py` where one does the work of several, for
   example repeated `rev-parse` of the same ref within one transition.
   Behaviour must not change, and every existing test must still pass.
   *As done:* steps 2 to 4 missed, so this step ran. It touches
   `pair/board.py` too, which the plan did not foresee: two helpers live
   there beside `listed`. See "What was done" below.
6. **Record** the before and after times, and what each step saved, in this
   file.

**Tests that show it works:** the whole module passes with the same 153 tests
and unchanged assertions, apart from the reap test's wait on its own
child, which step 4 replaces with an equivalent poll of the orphan's pid. The sandboxed wall time is at most a third
of the baseline.

**Risks.**
- `xcrun -f git` may print a path when no Command Line Tools are installed,
  or be slow on its first call. Use the path only if it is an executable
  file, and call `xcrun` once per process.
- `copytree` gives every file a new inode, so the first git command in each
  test refreshes the index's stat data. That is a small, bounded cost, and
  it does not change any result.
- The 30-second target needs the developer's machine outside the sandbox; a
  seat can only show the sandboxed third.

## What was done

All times are wall times of `python3 -m unittest test_pair`, run from `pair/`
in a seat's sandbox on 2026-10-01, where 7 tests skip (the reap test and
`WatchTest`). The machine was under varying load: the same code ran between
42 and 79 seconds. Only the alternating runs, `main`'s `pair/` (by
`git archive`) and this branch's back to back, compare fairly.

| Run | `main` | this branch |
|---|---|---|
| Baseline, alone | 130 s | |
| Alternating, round 1 | 144 s | 58 s |
| Alternating, round 2 | 109 s | 42 s |

That is about 2.5 times faster, not the third that Done asks for. The
developer's run outside the sandbox, with the reap and watch tests running,
has not been taken; a seat cannot take it.

What each change did:

- **Real git first on `PATH`** (`skip_git_trampoline` in `test_pair.py`).
  `LoopTest` went from 38 s to 21 s. This was the largest single saving.
- **One template repository** (`board_repository`, copied by `Bench`). It
  saves about 7 git processes per `Bench`, about 1,000 in the module.
- **The reap test** no longer waits 10 s for a zombie (step 4 as planned). It
  skips in the sandbox, so this branch has not timed it.
- **Fewer git calls in `pair/`.** A run of the module made 7,946 git calls,
  and makes 7,054 now.
  - `board.head_and_dirty` reads HEAD and whether the worktree is dirty from
    one `git status --porcelain=v2 --branch`. `Loop.absorb_developer` and
    `Loop.settle` used it in place of `status --porcelain` plus
    `rev-parse HEAD`, and `settle` now runs `rev-parse HEAD` only after it
    commits.
  - `board.listed_by_stage` lists every stage from one `git ls-tree -r`, in
    place of one `ls-tree` per stage in `Loop.flight_checked` and
    `status_view`.
  - Two `BoardTest` tests check that the helpers agree with what they
    replace, so the module now runs 155 tests: the 153 it started with,
    unchanged, plus those two.
- Tried and dropped: `core.fsync none` in the template made no measurable
  difference.

Where the remaining time goes: about 7,000 git processes at about 6 ms each
inside the sandbox, which is most of the 42 to 58 s. The largest remaining
sources are per tick of the loop: `next_ripe`, `running_tree`, `families` and
`adopt` each list stages and read `ORDER` again, and each `Bench.issue`
spends an `add` and a `commit` (about 680 calls). Cutting more means caching
board reads within one tick of `Loop.run`. That is a change to how the loop
reads the board, larger than this Issue's "do not change behaviour". The
developer accepted 2.5 times (see Done), and that caching is now
`issues/backlog/pair-board-reads-per-tick.md`.

A recount on the finished branch found 7,129 git calls in the module, led by
`commit` (802), `status --porcelain=v2` (713), `rev-parse HEAD` (563),
`ls-tree --name-only` (517) and `grep -l` (394, one per `board.families`).
Environment settings do not help: `GIT_CONFIG_NOSYSTEM`, an empty global
config and `GIT_OPTIONAL_LOCKS=0` each saved under 2 ms a call, within the
noise, against a floor of about 2 ms to start any process in the sandbox.
