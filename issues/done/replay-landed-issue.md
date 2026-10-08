---
difficulty: medium
parent: pair-versus-single-seat
waits_on:
  - single-seat-mode
---

# Replay a landed Issue in a scratch clone

One part of `pair-versus-single-seat`. A replay runs an Issue that has
already landed again, from the commit it started from, in either mode, so
that the two modes are compared on the same Issue and the same code.

## Wanted

A recipe, `just pair-replay <slug> --mode single|pair`, that:

- Finds the Issue's start commit: the parent of the commit on `main` whose
  subject is exactly `Start <slug>` (the loop writes it in `move_underway` in
  `pair/loop.py`; two older commits begin with `Start ` but are not loop starts, so a
  prefix match is wrong). A slug with no such commit, or a Flight's slug
  (its work landed in its parts), is refused with a message naming it.
- Makes a scratch clone of the repository under
  `.pair/replays/<slug>-<mode>/` (inside the ignored `.pair/` runtime
  directory), with no remote, whose `main` is reset to the start commit and
  whose `issues/backlog/` holds only that Issue, as its file stood at the
  start commit, committed on the clone's `main`. Every other Issue file
  in a stage directory under `issues/` other than `done/` and `roadmap/` at
  that commit (the set of stage directories has changed over history; today
  it includes `todo/`, `underway/`, `in-progress/` and `desk-check/`) is
  removed in the same commit, keeping each directory's `README.md`.
- Runs the current loop from the stereorepo checkout against the clone, as a
  portfolio's loop is run (`uv run --script <stereorepo>/pair/pair.py run
  --once`, from the clone), with `--single-seat` for `--mode single`. For an
  Issue that changes `pair/`, the seats edit the clone's own old `pair/`, not
  the loop that runs them.
- Answers a desk check by accepting it (the equivalent of `just
  pair-accept` in the clone), so a `developer` Issue completes.
- Keeps, under the replay's directory: the clone's `.pair/turns.jsonl` and
  `.pair/events.jsonl`, the landed diff (the clone's `Replay <slug>` commit,
  which sits on the start commit, to the clone's final `main`, so that the
  board's pruning is not in it) as `landed.diff`, and an `outcome.json` with the outcome (`landed`,
  `sent-back` or `paused`), the mode, the start commit and the wall-clock.
  The outcome maps what the last of `Loop.run(once=True)` and `Loop.accept`
  answers: `landed` is `landed`, `kicked` (the loop's answer when it sends an
  Issue back for elaboration, logged as a `sent-back` event) is `sent-back`,
  and anything else (`paused`, `stopped`, a second `desk-check`) is `paused`.
- Leaves stereorepo's `main`, its working tree and the developer's checkout
  unchanged, and can be run again over an earlier replay of the same slug and
  mode only with `--force`, which deletes the earlier one first.

The tests below need fake seats, which `pair/test_pair.py` injects in-process
through the loop's seat factory (`FakeSeat`), and a `uv run` subprocess
cannot take them. So the replay is a function (in `pair/pair.py` or a new
`pair/replay.py`) that builds the clone and then runs the current loop
in-process against it, as `run --once` would from the clone, followed by
`accept` if the run stops at a desk check, with the seat factory as a
parameter. The recipe calls that function through a `replay` subcommand of
`pair/pair.py`. The `Loop` it builds is the one `main` in `pair/pair.py`
builds for `run`, with the clone as its repository and `mode` from
`--mode`, except that it never pushes (`push=False`) and never restarts
(`restart=None`, `code_changed=None`), since the clone has no remote and a
restart would re-execute `pair.py` without the replay. Running the loop in-process from the stereorepo checkout is
still "the current loop", and the clone's `pair/` is still only the seats'
work.

## How anyone will know it is done

Tests in `pair/test_pair.py`, on a small throwaway repository with fake
seats:

- A replay of a landed Issue in each mode produces `turns.jsonl`,
  `events.jsonl`, `landed.diff` and `outcome.json` with the right outcome and
  mode, and only the primary seat's turns in single mode.
- After the replay, the source repository's `main` ref, `git status` and
  remotes are as they were, and the clone has no remote.
- The clone's backlog at the start of the run holds only the replayed Issue.
- A `developer` Issue's replay reaches `landed` through the accepted desk
  check.
- A replay whose fake seat sends the Issue back for elaboration records
  `sent-back` in `outcome.json`.
- A slug with no `Start <slug>` commit is refused, as is a Flight's slug, and
  each refusal names the slug; a commit whose subject only begins with
  `Start <slug>` is not taken as the start; a second replay without
  `--force` is refused, and with `--force` replaces the first.

## Out of scope

- Replaying another portfolio's Issues.
- The report over replays; that is `replay-report`.

## The plan

### A new module, `pair/replay.py`

It holds everything but the command line, so the tests import it as they
import `loop` and `board`.

- `start_commit(source, slug) -> str`: walks `git log main --format=%H%x00%s`
  in `source`, takes the commits whose subject equals `Start <slug>`, and
  returns the first parent of the most recent one. It takes the most recent
  because an Issue that was sent back and started again has more than one
  such commit, and only the last of them led to the landing. It raises
  `RefusalError` (its messages are templates in `REFUSALS`, keyed by reason,
  as ruff's TRY003 asks) when none matches, and
  when `board.children(source, "main", slug)` is not empty, because the slug
  is then a Flight. It reads the children at `main`, not at the start
  commit: a `hard` Issue is split during its own backlog stage, after its
  `Start` commit, so at the start commit a Flight has no children yet.
- `prepare(source, start, slug, clone)`: runs `git clone -q --no-checkout
  <source> <clone>`, then `git remote remove origin` and `git checkout -q -B
  main <start>`. It copies `user.name`, `user.email` and `commit.gpgsign`
  from the source's local config where set, so the clone commits as the
  source does. It writes `.pair/` and `worktrees/` into the clone's
  `.git/info/exclude`, because an old start commit's `.gitignore` may not
  ignore them, and the loop would then see the clone's checkout as dirty. On
  the clone's `main` it then:
  - finds the Issue's file under whichever stage directory held it at
    `start` (`board.locations`) and `git mv`s it into `issues/backlog/`
    when it is not already there;
  - `git rm`s every other `*.md` other than `README.md` in each stage
    directory except `done/` and `roadmap/`;
  - drops every line of `issues/backlog/ORDER` that names a removed slug,
    with `board.without`;
  - commits all of this as one commit, `Replay <slug>`, and returns it.

  An Issue file found in no stage but `done/` or `roadmap/` at the start
  commit is refused (`absent`). The loop's own history cannot produce one,
  but the check costs a line and leaves a clear message. `replay` deletes
  a clone that `prepare` refuses or fails to finish, so it is not taken
  for an earlier replay the next time.
- `replay(source, slug, mode, make_loop, *, force=False) -> dict`:
  1. Calls `start_commit`, so that a refused slug deletes nothing even with
     `--force`.
  2. Refuses when `.pair/replays/<slug>-<mode>/` exists and `force` is
     unset, and otherwise removes the earlier replay. It then calls
     `prepare`, the clone going to
     `.pair/replays/<slug>-<mode>/replay-<slug>-<mode>/`. `publish` names a
     loop's cockpit entry after its checkout's directory, so this name makes
     each replay's entry its own and unlike any real portfolio's.
  3. Builds the loop with `make_loop(clone, mode)`. That parameter is the
     seam the tests use to supply fake seats.
  4. Runs `loop.run(once=True)`, and then `loop.accept()` when the run
     answered `desk-check`, both inside one `supervise`, so the clone's
     event log ends with one `ended`. `supervise` moves from `pair/pair.py` into
     `pair/loop.py`, beside `append_event`, and `pair.py` imports it from
     there, since `pair.py` will import `replay` and the import must not go
     the other way.
  5. Maps the last answer to the outcome as the Issue says: `landed` stays
     `landed`, `kicked` becomes `sent-back`, and anything else becomes
     `paused`.
  6. Writes the replay's files beside the clone: copies of
     the clone's `.pair/turns.jsonl` and `.pair/events.jsonl`;
     `landed.diff`, from `git diff <Replay commit> main` in the clone (empty
     when nothing reached `main`; a send-back puts the Issue's
     `# Needs elaboration` there); and `outcome.json`, holding `slug`,
     `mode`, `outcome`, `answer` (the loop's own last answer, which tells a
     pause from a stop), `start` and `seconds`, measured with
     `time.monotonic` around step 4.
  7. Removes `<pairs_dir>/replay-<slug>-<mode>.json` (`pairs_dir` in
     `pair/loop.py`), which the clone's loop wrote through `publish` and
     which would otherwise show a replay as a portfolio in a cockpit. It
     does so in a `finally`, so that a replay that crashes or is interrupted
     leaves no entry either.

  The clone is kept, so that the developer can inspect it.

### `pair/pair.py` and the `justfile`

- A `replay` subcommand: `replay SLUG --mode {single,pair} [--force]`, with
  the `seats` and `stages` parents so that models can be named. The `Loop`
  that `main` built inline moves into `build_loop(repo, args, **settings)`,
  which both use. `run_replay`'s
  `make_loop` builds the `Loop` that `main` builds for `run`, on the clone,
  with `mode` from `--mode`, `push=False`, `code_changed=None` and
  `restart=None`. It installs `stopper` for SIGINT, prints `pair: <outcome>`
  and the replay's directory, and exits 0 for any outcome, since a replay
  that ends `sent-back` or `paused` has still done what it was asked. On
  `RefusalError` it prints the message and exits with `EXIT["refused"]`.
  `main` handles `replay` before the `Loop` it builds for the other
  commands, because the loop's repository is the clone and not
  `repo_root()`.
- The module docstring gains the `replay` line, and the `justfile` gains
  `pair-replay *args:`, whose comment names `--mode` and `--force`.
- `pair/README.md` gets a short paragraph on replays.

### Tests

A `ReplayTest` class in `pair/test_pair.py`. Its `landed` commits on
`Bench.repo` the history a landing leaves: `x` with a second backlog Issue
named in `ORDER`, a `todo/` Issue and a `done/` Issue; then `Start x`; then
the landing; then `Start x-and-more`. Writing that history directly is
faster than running the loop for it, and `start_commit` reads only commit
subjects. Its `make_loop` builds a plain `Loop` on the clone
whose seat factory hands out `FakeSeat`s fed from the same `Bench` script,
using `Bench`'s gate. `Bench` already points `PAIRS_DIR` at a temporary
directory. The tests are the ones under "How anyone will know it is done":

- one replay in each mode, checking the four files, the outcome and the mode,
  and that single mode logs only `primary` turns;
- that the source's `main`, `git status --porcelain` and `git remote` are
  unchanged, and that the clone has no remote;
- that the clone's backlog, read at its `Replay x` commit, holds only `x`,
  and that `done/` is kept;
- that a `developer` Issue reaches `landed` through `accept`;
- that a seat sending the Issue back for elaboration gives `sent-back`;
- the refusals: an unknown slug; a Flight whose child names it in
  `parent:` only in a commit after its `Start` commit; a commit with the subject
  `Start x-and-more` when the slug is `x`, and a second replay without
  `--force`. With `--force`, a second replay replaces the first, and an
  earlier replay is left in place when a `--force` replay of the same slug
  is refused (there, because a child naming it was committed since);
- that an Issue off the board at its start is refused (`absent`), twice
  in a row, with no replay directory left behind;
- that no `replay-x-<mode>.json` is left in `PAIRS_DIR` after a replay.

### Order

1. `start_commit` and `prepare`, with their tests.
2. `replay`, with the tests in each mode, for the source being unchanged,
   for the developer Issue and for the send-back.
3. The subcommand, the recipe and the README.

### Risks

- **The loop on old code.** The clone's landing gate runs the old
  `just gate`, and `provision` the old `just setup`, in the clone's
  worktree. A start commit whose gate no longer runs, for example because a
  tool it needs has changed, pauses the replay. That is recorded as
  `paused` and is the report's business; the replay does not work around
  it.
- **Old board layouts.** Stage directories that `board.STAGES` does not
  name are still cleared, because `prepare` clears by directory under
  `issues/` and not by `STAGES`. The loop itself, though, reads only
  `STAGES`. Every `Start <slug>` commit was written by a loop that had
  `issues/backlog/`, so `prepare` needs no refusal for a board without it.
- **Size.** Each replay is a full clone, made with hardlinked objects
  because it is local, plus a provisioned worktree. A sample of tens of
  replays costs disk space but nothing more.

## For the next reader

- The code is in `pair/replay.py`. The subcommand is `run_replay` in
  `pair/pair.py`, which builds its `Loop` with `build_loop`, now also used by
  `main`. The tests are in `ReplayTest` in `pair/test_pair.py`.
- The `justfile` is rendered: `pair-replay` is declared in
  `CONDITIONAL_RECIPES` in `.meta/lib/render/writers.py` and in `CONTRACT`
  in `.meta/checks/files/justfile.py`, not only in the `justfile`.
- No replay has been run with real Claude Code seats: each one costs a whole
  Issue's turns. The first real run is part of `pair-mode-decision`. It
  will show whether old start commits' `just setup` and `just gate` still run
  in a clone; when one does not, the replay ends `paused`, and the gate's
  output is in the clone's `.pair/`.
- The clone copies only the source's *local* `user.*` and `commit.gpgsign`.
  A developer whose identity and signing are global, as in stereorepo, needs
  nothing more.

## Pair notes

> **primary, backlog turn 1**
>
> The Issue was already well specified, so I made two small additions and left `difficulty: medium` as it was.
>
> **Fact check:** the Issue's claims about the code hold:
> - The loop's `Start <slug>` commit is written in `move_underway` in `pair/loop.py`.
> - Exactly two older commits on `main` have subjects that begin with `Start ` but aren't loop starts.
> - `--single-seat` and `--once` both exist.
> - `.pair/` is ignored.
> - `run --once` stops at a desk check, so the replay has to accept afterwards, which the Issue already says.
>
> **Additions:**
> 1. **A way to test with fake seats.** As written, the tests couldn't work. They use fake seats (`FakeSeat` in `pair/test_pair.py`), which can only be passed to a loop running in the same process. A replay that starts the loop as a separate `uv run --script pair.py run` process can't take them. I wrote in that the replay is a function that:
>    - builds the clone;
>    - runs the current loop in the same process against the clone, then calls `accept` if the run stops at a desk check;
>    - takes the factory that makes the seats as a parameter.
>
>    The `just pair-replay` recipe calls it through a new `replay` subcommand of `pair/pair.py`.
> 2. **More tests for refusals and `--force`.** The list of tests now also covers:
>    - refusing a Flight's slug, with the message naming the slug;
>    - not taking a commit whose subject only begins with `Start <slug>` as the start;
>    - `--force` replacing an earlier replay of the same slug and mode.

> **secondary, backlog turn 2**
>
> I made three small fixes to `issues/underway/replay-landed-issue.md` and left `difficulty: medium` as it was. Your partner's version was mostly sound; the gaps were in how the replay drives the loop. The changes are committed as `fde64e5e`.
>
> 1. **Outcome names.** The Issue lists the outcomes as `landed`, `sent-back` or `paused`, but the loop never answers `sent-back`. When it sends an Issue back for elaboration it answers `kicked`, and `sent-back` is only the name of the event it logs. The Issue now says how to turn what the loop answers into the recorded outcome:
>    - `landed` stays `landed`.
>    - `kicked` becomes `sent-back`.
>    - Anything else, such as `paused`, `stopped` or a second desk check, becomes `paused`.
> 2. **Loop settings for the replay.** The replay should build the same `Loop` that `main` in `pair/pair.py` builds for `run`, with three settings turned off:
>    - **No pushing** (`push=False`), because the clone has no remote.
>    - **No restarting** (`restart=None`, `code_changed=None`). A restart re-executes `pair.py` itself, which would drop the replay.
> 3. **A new test.** No test covered the `sent-back` outcome. One now has a fake seat send the Issue back for elaboration and checks that `outcome.json` records `sent-back`.

> **primary, backlog turn 3**
>
> I'm changing nothing this turn, and `difficulty: medium` stays. I checked your partner's three changes against the code and all of them hold:
>
> - **`kicked`:** when the loop sends an Issue back for elaboration, it logs a `sent-back` event and answers `kicked` (in `pair/loop.py`). So the Issue's rule for turning the loop's answer into the outcome recorded in `outcome.json` is right.
> - **No pushing or restarting:** `Loop` takes `code_changed` and `restart` and allows both to be `None`. `main` in `pair/pair.py` only sets them for `run`, so a replay that turns off pushing and restarting is consistent with how the loop is built today.
> - **The new test:** the test for a replay that ends `sent-back` covers an outcome no other test did.

> **primary, todo turn 1**
>
> I've written the plan under `## The plan` in `issues/todo/replay-landed-issue.md`. Nothing is implemented yet, and the Issue can be done as written, so it needs no `# Needs elaboration` section.
>
> **The new code** goes in a new module, `pair/replay.py`, in three functions:
> - **`start_commit`** finds the parent of the most recent commit whose subject is exactly `Start <slug>`. It takes the most recent because an Issue that was sent back and started again has more than one such commit, and only the last led to the landing. It refuses a slug with no such commit, and a Flight's slug.
> - **`prepare`** makes the scratch clone and removes its remote. It resets the clone's `main` to the start commit and leaves only the replayed Issue in `issues/backlog/`, in one `Replay <slug>` commit.
> - **`replay`** runs the current loop in the same process against the clone, then accepts if the run stopped at a desk check. It writes `turns.jsonl`, `events.jsonl`, `landed.diff` and `outcome.json` beside the clone. It takes the function that builds the loop as a parameter, which is how the tests supply fake seats.
>
> **On the command line**, `pair/pair.py` gets a `replay` subcommand that builds the production loop without pushing or restarting. The `justfile` gets a `pair-replay` recipe.
>
> **Tests:** a `ReplayTest` class in `pair/test_pair.py` covers every case in the Issue's done list. It first lands an Issue in a throwaway repository with fake seats, which leaves a real `Start <slug>` commit to replay from.
>
> **Things the code made me add** that the Issue didn't say:
> - **Ignore rules in the clone:** `.pair/` and `worktrees/` are written into the clone's `.git/info/exclude`. An old start commit's `.gitignore` may not ignore them, and the loop would then see the clone as having uncommitted changes.
> - **The running order:** `issues/backlog/ORDER` drops the lines for the Issues it removes.
> - **Moving `supervise`:** it moves from `pair/pair.py` into `pair/loop.py`. `pair.py` will import the new `replay` module, so `replay` can't import from `pair.py` without a circular import.
> - **The cockpit entry:** each clone's loop publishes a status file to the directory a cockpit reads. The replay deletes it afterwards, so a cockpit doesn't show a replay as a real portfolio.
>
> **Risks:**
> - **Old gate:** in the clone, the landing gate is the old `just gate` from the start commit. If that no longer runs, the replay is recorded as `paused`.
> - **Refused old commits:** if `issues/backlog/` doesn't exist at the start commit, I chose to refuse the replay. The Issue doesn't ask for this, and none of the planned tests covers it.
> - **Disk space:** every replay keeps a full clone, which takes disk space.
> - **Concurrent replays:** two replays run at once would clash over that shared cockpit entry. That is acceptable with one developer.

> **secondary, todo turn 2**
>
> I checked my partner's plan against the code and fixed four things in `## The plan` of `issues/todo/replay-landed-issue.md`; nothing is implemented yet. The Issue can be done as written, so it needs no `# Needs elaboration` section. The fixes are committed.
>
> 1. **Finding Flights failed.** The plan checked for a Flight by looking for its children at the start commit. A `hard` Issue is only split during its own backlog stage, after its `Start` commit, so at the start commit a Flight has no children and would have been replayed. The plan now looks for children on `main`. Its test now uses a Flight whose child is committed after the `Start` commit.
> 2. **`--force` could delete a replay with nothing to replace it.** The plan deleted the earlier replay before checking the slug, so a mistyped slug with `--force` would delete it and then be refused. The slug is now checked first, and a test covers this.
> 3. **The cockpit entry.**
>    - **The problem:** a loop names its entry in the shared status directory after its checkout's folder (`publish` in `pair/loop.py`). In the plan every clone's folder was called `clone`, so all replays shared one entry. Two replays running at once would overwrite each other's entry, and the clean-up step would delete the entry of any real checkout that happened to be called `clone`.
>    - **The fix:** the clone's folder is now `replay-<slug>-<mode>/`, so each replay has an entry of its own.
>    - **Clean-up:** the replay removes the entry in a `finally`, so a replay that crashes or is interrupted leaves none behind either.
>    - **Test:** one checks that no entry is left afterwards.
> 4. **A refusal that could never happen.** The plan refused a start commit with no `issues/backlog/`, but every `Start <slug>` commit was written by a loop that had one. The Issue doesn't ask for this refusal and no test covered it, so it is gone.

> **primary, todo turn 3**
>
> I'm changing nothing this turn. I checked your partner's four fixes against the code, and all of them hold:
>
> 1. **Finding Flights:** a `hard` Issue is split into parts during its own backlog stage, after its `Start` commit. At the start commit a Flight has no children yet, so reading them from `main` is the right fix. A test now covers it.
> 2. **`--force`:** the plan now checks the slug before deleting anything. That stops a mistyped slug from destroying an earlier replay before being refused.
> 3. **The cockpit entry:** `publish` in `pair/loop.py` names a loop's status file after the folder of its checkout. Naming each clone `replay-<slug>-<mode>/` gives every replay a status file of its own and can't collide with a real portfolio's. Removing it in a `finally` also covers a replay that crashes or is interrupted.
> 4. **Dropping the refusal:** the loop writes `Start <slug>` in `move_underway`, by moving the Issue's file out of `issues/backlog/`. So every start commit already has a backlog, and the refusal for a missing one could never fire.

> **primary, in-progress turn 1**
>
> `just pair-replay <slug> --mode single|pair [--force]` now exists and is committed as `9fcfda9c`. `just gate pair` passes (310 tests and ruff), and so does `just gate meta`. No replay has been run with real Claude Code seats, since each one costs a whole Issue's turns; the first real replays belong to `pair-mode-decision`.
>
> **What it does**
> - **Finds the start:** it takes the parent of the last commit on `main` whose subject is exactly `Start <slug>`. It refuses a slug with no such commit, and a Flight, whose children it reads on `main`.
> - **Prepares the clone:** it clones the repository into `.pair/replays/<slug>-<mode>/replay-<slug>-<mode>/` with no remote and sets the clone's `main` to the start commit. One `Replay <slug>` commit then leaves that Issue alone in the backlog.
> - **Runs the Issue:** the current loop runs one Issue in that clone, in the same process, and accepts a desk check if it stops at one.
> - **Keeps the results:** beside the clone it keeps `turns.jsonl`, `events.jsonl`, `landed.diff` and `outcome.json`.
> - **Cleans up:** it deletes the status file the clone's loop publishes for a cockpit, however the replay ends.
>
> **Where it lives**
> - The code is in a new module, `pair/replay.py`.
> - `pair/pair.py` gets a `replay` subcommand, `run_replay`. The `Loop` that `main` built inline is now `build_loop`, which both use.
> - `supervise` moved from `pair/pair.py` into `pair/loop.py`, so `replay.py` doesn't have to import `pair.py`.
> - The tests are a new `ReplayTest` class in `pair/test_pair.py`, covering every case in the Issue's done list. It writes the history of a landed Issue directly instead of running the loop to make it, which is faster.
> - `pair/README.md` gets a paragraph and a row in its usage table.
>
> **Where the plan changed** (all recorded in the Issue file):
> - **`landed.diff`:** it starts from the clone's `Replay <slug>` commit, not from the start commit, so it doesn't include the other Issues the clone removed. A send-back's diff holds only the Issue's `# Needs elaboration` section.
> - **`outcome.json`:** it also records `answer`, the loop's own last answer. That tells a pause from a stop, which the outcome `paused` covers both of.
> - **Git identity:** the clone copies the source's local `user.name`, `user.email` and `commit.gpgsign`, so its commits are made the way the source's are.
> - **The exception:** the refusal exception is `RefusalError`, with its messages kept as templates in `REFUSALS`. Ruff (N818 and TRY003) asked for that.
> - **The `justfile` is generated:** the new recipe also had to be declared in `CONDITIONAL_RECIPES` in `.meta/lib/render/writers.py`. Its parameters went into `CONTRACT` in `.meta/checks/files/justfile.py`.
> - **A safety refusal:** the replay refuses (`absent`) a slug whose Issue file isn't on the board at the start commit. The loop's own history can't produce that case, and no test covers it.

> **secondary, in-progress turn 2**
>
> I reviewed my partner's implementation and fixed one bug and one test that didn't test what it claimed to. Both fixes are committed as `ea92eaef`. `just gate pair` (311 tests and ruff) and `just gate meta` both pass.
>
> 1. **A refused replay left a half-made clone behind.** If setting up the clone failed or was refused, the partial clone stayed where the replay keeps its results. The next run of that slug was then refused as already replayed, and only `--force` could clear it.
>    - **Fix:** `replay` in `pair/replay.py` now deletes that partial clone before passing the refusal or error on.
>    - **Test:** a new one asks twice to replay an Issue that wasn't on the board at its start commit. It checks that both attempts are refused and that no replay directory is left.
> 2. **The `--force` test tested nothing.** It showed that an unknown slug with `--force` leaves an earlier replay alone. But each slug has its own replay directory, so a different slug could never have touched the earlier replay.
>    - **Fix:** the test now adds a part naming `x` as its parent, so `x` counts as a Flight. A `--force` replay of `x` is then refused, and the test checks that the earlier replay of `x` is still there.
>    - **Then:** it removes the part and checks that `--force` replaces the earlier replay.
>
> I updated the Issue file's plan and test list to match. Everything else in the implementation matches the plan as revised in the Issue file.

> **primary, in-progress turn 3**
>
> I'm changing nothing this turn. I checked your partner's two fixes in `pair/replay.py` and `pair/test_pair.py`, and both are right:
>
> - **The leftover clone:** before the fix, a refused or failed clone setup stayed in the replay's directory. The next run of that slug was then refused as already replayed, and only `--force` cleared it. `replay` now deletes it, and the new test asks twice to replay an Issue that wasn't on the board at its start commit. It checks that both attempts are refused and that no directory is left. That also covers the `absent` refusal, which I had said no test covered.
> - **The `--force` test:** each slug has its own replay directory, so my version, which used an unknown slug, could never have touched the earlier replay. The new version first makes `x` a Flight, so a `--force` replay of `x` is refused, and checks that the earlier replay of `x` is still there. It then removes the part and shows `--force` replacing it.
>
> The Issue file's plan and test list match the code. I didn't re-run the gates, since nothing changed since your partner's turn, when `just gate pair` (311 tests and ruff) and `just gate meta` both passed.

Gated by the supervisor at 08:09: `meta`, `pair`, `specialization`; 99 steps passed.
