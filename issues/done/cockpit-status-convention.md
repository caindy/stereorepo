---
difficulty: medium
---

# Publish the loop's status by a convention a cockpit can read

A cockpit, one view across every repository the developer runs a pair loop
in, comes later. What it needs from each repository now is one convention for
publishing what the loop knows: the Issue underway, its stage, its round,
whether it needs the developer, and why.

That knowledge is already derived in one place: `status_view` in
`pair/loop.py`, which `just pair-status` renders and `just pair-status --json`
prints. The published file is that same object, so it cannot disagree with
the screen.

## Wanted

- The supervisor publishes `~/.pairs/<repo>.json`, where `<repo>` is the
  basename of the developer's checkout. Its content is
  `{"repo": <absolute path of the checkout>, **status_view(repo, main)}`,
  with the loop's own `main`; the path
  lets a reader tell apart two checkouts with the same basename. The
  `waiting` and `underway` keys of `status_view` already carry the Issue, its
  stage, its turn (the round) and every reason the loop waits on the
  developer: a desk check, a `Needs elaboration` send-back, a seat that failed
  after its restart, a round cap, a refused `--ff-only`.
- It is republished whenever the loop's state changes: after `Loop.save`,
  after `Loop.clear`, after every `append_event` (both loops log there), and
  after `Loop.accept`, `resume`, `accept_flight` and `resume_flight`, which
  can move a file on `main` without logging an event. Each write goes to a
  temporary file in the same directory, named uniquely per write (the `pair`
  and `groom` loops may publish at once), and is renamed into place, so a
  reader never sees half a file and the last writer's view, which is whole,
  wins.
- The directory is `~/.pairs` unless the environment variable `PAIRS_DIR`
  names another. A failure to publish never raises out of the loop: a `Loop`
  reports it through its `say`, and the bare `append_event` call in
  `pair/pair.py` (the `ended` event) on stderr.
- The file holds nothing the board, `.pair/` and git do not. Nothing reads it
  back.
- `pair/README.md` documents the path, the `PAIRS_DIR` override, when it is
  written, and its keys (`repo` plus those of `status --json`, pointing to
  `status_view`'s docstring rather than copying it).

## Out of scope

- The cockpit itself, notifications, taking over a seat
  (`why-fork-harness-survey` writes up their requirements).
- Changing what `status_view` derives.
- Removing a repository's file when its loop ends; the last state stays
  published.

## Done when

- `Bench` in `pair/test_pair.py` sets `PAIRS_DIR` to a scratch directory, so
  no test writes to the real `~/.pairs`.
- A test drives the loop through a run that saves state, logs events and
  reaches a desk check or pause, and after it asserts that
  `json.loads` of `<PAIRS_DIR>/developer.json` equals
  `{"repo": str(repo.resolve()), **status_view(repo)}` (resolved, since a
  temporary directory on macOS sits behind the `/var` symlink and a checkout
  given as `.` has no basename), with the Issue in `underway`
  and the reason in `waiting`.
- A test that `append_event` alone republishes the file, and one that
  `accept_flight` on a Flight at its desk check leaves a file in which that
  Flight no longer waits.
- A test that only `developer.json` is left in `PAIRS_DIR` after a run (no
  temporary file), and that with `PAIRS_DIR` pointing at a path that cannot
  be a directory (a regular file) the loop still reaches the same outcome and
  `say` reports the failure.
- `pair/README.md` documents the convention.

## The plan

### Seams (all in `pair/loop.py`, beside `status_json`)

- `pairs_dir() -> Path`: `Path(os.environ["PAIRS_DIR"])` when set, else
  `Path.home() / ".pairs"`. Read at each call, not at import, so a test's
  environment applies.
- `publish(repo, main="main") -> str | None`: builds
  `{"repo": str(repo.resolve()), **status_view(repo, main)}`, writes it with
  `tempfile.NamedTemporaryFile(dir=pairs_dir(), prefix=f".{repo.name}.",
  suffix=".tmp", delete=False)` (unique per write, so `pair` and `groom`
  never share a temporary file), then `os.replace` onto
  `pairs_dir() / f"{repo.resolve().name}.json"`. It creates the directory
  first. On any exception it removes its temporary file if one was made and
  returns a one-line message naming the path and the error; otherwise
  `None`. It never raises (see Risks).
- `append_event` gains two keyword-only parameters, `main: str = "main"`
  and `report: Callable[[str], None]` (default: print to `sys.stderr`).
  After appending the row it calls `publish(repo, main)` and passes any
  message to `report`. No event field today is named `main` or `report`, so
  `**fields` does not collide. `supervise` in `pair/pair.py` keeps its bare
  call, which reports on stderr by the default.
- `Loop.publish()`: `publish(self.repo, self.main)`, sending a message to
  `self.say`. Called at the end of `save` and `clear`, and at the end of
  `accept_flight` and `resume_flight` on their `accepted` / `resumed`
  paths. `Loop.event` passes `main=self.main, report=self.say` to
  `append_event`.
- `Loop.accept` and `Loop.resume` without a slug need nothing of their own:
  every path that changes anything goes through `save`, `clear` or `event`,
  and the `none` path changes nothing. In the CLI the `ended` event of
  `supervise` publishes after them too.

### Steps

1. **Tests' environment first.** At import, `pair/test_pair.py` sets
   `os.environ["PAIRS_DIR"]` to a directory under a module-level
   `tempfile.mkdtemp()` (removed `atexit`), so no test in any worker process
   can reach the real `~/.pairs`, including tests that call `append_event`
   without a `Bench` (`WatchTest.emit`) and subprocess runs of `pair.py`,
   which inherit it. `Bench.__init__` then points `PAIRS_DIR` at
   `<its tmp>/pairs` and exposes it as `bench.pairs`; workers run one test
   at a time per process (`pair/gate.py`), so the variable set by the
   current `Bench` is the one in force. `WatchTest.emit` calls
   `append_event` on a directory that is not a git repository, so
   `status_view` fails there on every event; `emit` passes
   `report=lambda _: None` so the suite's output stays clean.
2. Add `pairs_dir` and `publish`, then wire `append_event`, `Loop.event`,
   `save`, `clear`, `accept_flight`, `resume_flight`.
3. Write the tests below.
4. `pair/README.md`: a short `### The published status` section after
   *The event log*: the path `~/.pairs/<basename>.json`, `PAIRS_DIR`, when it
   is rewritten, that it is replaced whole by rename, that the loop never
   reads it, and the keys (`repo` plus those of `status --json`, pointing to
   `status_view`'s docstring). Add a pointer from the "watch" row of *Using
   it*. Mention it in the module docstring of `loop.py` where `.pair/` files
   are listed, if they are.

### Tests (`pair/test_pair.py`, a new `PublishTest` over `Bench`)

- `test_the_file_is_the_status_view`: a send-back and a desk check, the
  same way an existing desk-check test drives a `developer` Issue to
  `run() == "desk-check"`; then `json.loads((b.pairs / "developer.json")
  .read_text()) == {"repo": str(b.repo.resolve()), **status_view(b.repo)}`,
  with the Issue's slug in `underway` and in `waiting`.
- `test_an_event_alone_republishes`: delete the file, call
  `append_event(b.repo, "pair", "x")`, and the file is back.
- `test_accepting_a_flight_republishes`: the Flight-at-desk-check fixture
  (`FLIGHT`), `b.loop.accept_flight("big")`, and the file's `waiting` no
  longer names `big`.
- `test_only_the_file_is_left`: after a full run, `os.listdir(b.pairs) ==
  ["developer.json"]`.
- `test_a_publish_failure_does_not_stop_the_loop`: `PAIRS_DIR` pointing at
  a regular file, a `say` that records; the run returns the same outcome as
  the first test and a recorded line names the path.

### Risks

- **Cost.** `status_view` makes a few git calls and reads every backlog
  file; publishing runs it on every save and event, often twice in a row (a
  pause saves, then logs). For a loop whose turns take minutes that is
  nothing, but the pair tests drive hundreds of transitions and the suite's
  wall time matters (`pair-test-git-traffic`). If the suite gets visibly
  slower, the fix is to skip a publish whose content equals the last one
  written by this process, not to drop call sites.
- **`status_view` can raise** on a malformed board or a `main` that does not
  resolve, so catching only `OSError` would let that out of `save`.
  `publish` catches `Exception`, deliberately, with a comment saying why:
  the published file is a courtesy and must never stop the loop.
- **A torn read of the other loop's state.** `Loop.save` writes
  `state.json` in place, so a `publish` from the `pair` loop can read the
  `groom` loop's file half-written and fail with a `JSONDecodeError`. That
  is caught, reported through `say` as one line, and put right by the next
  publish; making `save` atomic is not part of this Issue.
- **Environment leaking between tests.** `Bench` sets `PAIRS_DIR` and does
  not restore it, which is safe only because the module-level default is
  always scratch. The failure test uses `mock.patch.dict`.

## Notes for the next reader

- **As built, the seams match the plan.** `pairs_dir` and `publish` sit
  after `status_json` in `pair/loop.py`. `append_event` publishes after
  every append and takes keyword-only `main` and `report`. `Loop.publish`
  runs after `save`, `clear`, and the successful paths of `accept_flight`
  and `resume_flight`. `Loop.event` passes its own `main` and `say`.
- **The module-level default for the tests** is `<TEMPLATES>/pairs`, set
  just after `TEMPLATES` in `pair/test_pair.py`, so it is removed with the
  directory that `board_repository` already uses. `Bench.pairs` is
  `<its tmp>/pairs`, and `Bench.close` puts back the `PAIRS_DIR` it found,
  so a later test that publishes without a `Bench` does not recreate a
  removed scratch directory.
- **The tests.** `PublishTest` has five tests. The plan's separate check
  that only `developer.json` is left after a run is part of
  `test_the_file_is_the_status_view`, and
  `test_resuming_a_flight_republishes` covers `resume_flight` beside
  `accept_flight`. `WatchTest.emit` passes a silent `report`, since its
  directory is not a git repository.
- **The suppression.** `publish` catches `Exception` with
  `# noqa: BLE001  # reason: ...`, in the form `.meta/check.py` uses. `pair/`
  is not linted by ruff today (`ruff check` with `.meta/ruff.toml` reports
  findings in `loop.py` that predate this change), so the suppression only
  documents the choice. The one new finding is `PLR0913` on `append_event`,
  which now has six parameters against a limit of five; `main` and `report`
  are keyword-only, so no caller can pass them by position. Linting `pair/` is
  filed as `pair-ruff-lint` in the backlog.
- **Cost.** `just gate pair` ran 213 tests in 19.5 s of wall time with
  publishing on. No measurement was taken before the change, because this
  Issue is not about speed. If the suite gets slower, the plan's fix still
  applies: skip a write whose text equals the last one this process wrote.
- **Not covered.** A supervisor already running when this lands keeps its
  old code, so `~/.pairs` appears only after the loop restarts.
