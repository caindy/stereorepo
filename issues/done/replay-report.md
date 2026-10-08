---
difficulty: medium
parent: pair-versus-single-seat
waits_on:
  - replay-landed-issue
---

# Report the replays by mode

One part of `pair-versus-single-seat`. The report turns the replays that
`replay` in `pair/replay.py` keeps under `.pair/replays/<slug>-<mode>/`
(`turns.jsonl`, `events.jsonl`, `landed.diff`, `outcome.json` and the clone)
into the four criteria the decision rests on. It reads; it never runs a
seat.

## Wanted

A recipe, `just pair-replay-report`, calling a `report` subcommand of
`pair/pair.py` (the logic in `pair/replay.py` or a new `pair/report.py`),
that prints, for each replayed slug, one column per mode (`single`, `pair`)
and a third, `original`, and then the same columns summed over the slugs of
each difficulty. A slug's difficulty is the `difficulty:` in the front matter
of its file in the source's `issues/done/`, or `unknown`.

| Criterion | Measure, per mode | Read from |
|---|---|---|
| Quality | outcome (`landed`, `sent-back`, `paused`) | `outcome.json` |
| | gate runs and how many failed or could not run | `gated` events, `outcome` field |
| | defect check: `passed`, `failed`, `could-not-run` or `none` (see below) | the fixing Issue's tests |
| | secondary turns that changed something, of all secondary turns, and the files they changed | `turns.jsonl` rows, `role`, `quiet`, `files` |
| Autonomy | `paused` events, `sent-back` events, and `# Needs elaboration` headings in the Issue's file on the clone's final `main` | `events.jsonl`, the clone |
| Time | wall-clock seconds (the loop ran in-process, so the gate is in it); turns per stage | `outcome.json` `seconds`; `turns.jsonl` `stage` |
| Tokens | sum of `cost_usd`; sums of `cache_read` and `cache_write` tokens, shown apart | `turns.jsonl` |

A row whose field is null counts as zero and the column says how many rows
lacked it. A `single` replay has no secondary seat, so its secondary-turn
measure reads `n/a`, not `0 of 0`. With no replays under `.pair/replays/`, the
report says so and exits non-zero; otherwise it exits 0 whatever it finds.

**The files a turn changed.** A turn row today does not say which files the
turn changed, and the loop deletes `pair/<slug>` on landing, so the clone
cannot tell either. `record` in `pair/loop.py` adds a `files` field to each
row: the paths `git diff --name-only` gives between the turn's start head and
its end head, `[]` for a quiet turn. Rows written before this change have no
`files`; the report says `files not logged` for them.

**The original run.** The `original` column takes the same measures from the
source's own `.pair/turns.jsonl` and `.pair/events.jsonl` rows for the slug,
headed as run by older loop code and models. Its wall-clock runs from the
slug's first `started` event to its `landed` event; it has no defect check
and no `outcome.json`, and its outcome is `landed` if a `landed` event exists.
A slug with no rows there shows `original` as missing.

**The defect check.** A replay's fixing Issues come from a `fixed_by:` list
of slugs in its `outcome.json`, or from `--fixed-by <slug>=<fix>` (repeatable),
which wins. For each fix:

1. The fix's landing commit is the commit on the source's `main` whose
   message carries `Issue: issues/done/<fix>.md`. None found:
   `could-not-run`, saying so.
2. Its added tests are the `def test_…` lines that commit adds in files named
   `test_*.py`. None: `none`.
3. A detached worktree of the clone's `main` is added in a temporary
   directory, so the kept clone's own checkout is never written to. Each such file, as it
   stands at the fix's commit, is written over the worktree's copy, and each
   added test is run by its dotted name with
   `uv run --with pyyaml python -m unittest <module>.<Class>.<test>` from the
   file's directory. Afterwards the worktree is removed, so the clone's
   `git status --porcelain` and `git worktree list` are as they were.
4. All pass: `passed`. Any fails by assertion: `failed`, the replay has the
   defect. Any errors on import, collection or a missing name: `could-not-run`,
   since the replay may simply name things differently; the report prints
   the first line of the error.

Only Python `unittest` tests are checked; a fix whose tests are elsewhere
(Rust, shell) is `none`.

**`--diff <slug>`** prints the `single` replay's `landed.diff` and then the
`pair` one's, each under a heading naming the mode, instead of the report;
a missing mode is said to be missing.

`pair/README.md` gains a line for the recipe beside `just pair-replay`.

## How anyone will know it is done

Tests in `pair/test_pair.py`, on fixture replay directories written by the
test (no seats run, except where a turn row's `files` is checked):

- Two replays of one slug, one per mode, print all four criteria for both
  modes; cost, cache reads and cache writes are the sums of the rows' fields,
  and a null `cost_usd` row is counted as missing, not as an error.
- Two slugs of one difficulty are summed into that difficulty's line.
- A slug replayed in only one mode prints the other mode as missing, not
  dropped; a `single` replay's secondary-turn measure prints `n/a`.
- With no replays the report says so and exits non-zero.
- A source whose `.pair/` logs hold rows for the slug prints the `original`
  column from them; one whose logs do not prints it as missing.
- A turn of the loop that changes a file writes that path in its row's
  `files`, and a quiet turn writes `[]`.
- A replay whose fixing Issue's added test fails against its clone is
  reported `failed`; one where it passes, `passed`; one where the test
  imports a name the clone lacks, `could-not-run`; and the clone's working
  tree is clean afterwards.
- `--diff` prints both modes' diffs under their headings.

## Out of scope

- Running replays, and choosing the sample.
- Judging the diffs, or the decision itself; those are the developer's.
- Checking fixes whose tests are not Python `unittest`.
- Back-filling `files` into old `turns.jsonl` rows.

## The plan

### Files and seams

- `pair/loop.py`: `Loop.settle` returns, in place of `quiet`, the sorted
  `git diff --name-only st.head head` it already computed to judge
  quietness (`[]` when quiet), before it overwrites `st.head`. `Loop.work`
  derives `quiet` as `not files`. `Loop.record` takes `files` as a keyword
  in place of its `quiet` argument, and writes both `quiet` and `files` in
  the row. No other reader of `turns.jsonl` changes.
- `pair/report.py` (new), imported only by `pair/pair.py`:
  - `Measures`, a dataclass of one column: outcome, gate runs and failures,
    defect result and its error line, secondary turns changed and total (or
    `None` for `n/a`), their files (or `None` for `files not logged`),
    pauses, send-backs, `Needs elaboration` headings, seconds, turns per
    stage, cost, cache read, cache write, and how many rows lacked each
    token field. An `add` method sums two columns for the difficulty lines:
    numbers add, file lists join, and the categorical fields (outcome,
    defect result) become tallies such as `landed 2, paused 1`. An `n/a`
    secondary measure stays `n/a` only if every summed column has it.
  - `measure(turns, events, outcome, needs)`: one column from parsed rows.
    It is shared by replays and by `original`, so both are counted alike.
  - `replays(source)`: each `<slug>-<mode>` directory under
    `replays_dir(source)` with an `outcome.json`, keyed by `(slug, mode)`
    from that file's fields rather than by splitting the directory name,
    since slugs hold hyphens.
  - `elaborations(clone, slug)`: `# Needs elaboration` headings in the
    Issue's file on the clone's `main`, found with `git ls-tree` and read
    with `git show`. The clone's checkout follows `main`, because `Loop.land`
    fast-forwards it, but a paused replay may have left it dirty.
  - `original(source, slug)`: rows for the slug from the source's
    `runtime_dir(source, "pair") / "turns.jsonl"` and `event_log(source)`;
    `None` when there are no turn rows. Wall-clock from the first `started`
    event's `at` to the `landed` event's `at`. These are local
    `%Y-%m-%dT%H:%M:%S` strings from `append_event`, parsed with
    `datetime.fromisoformat` (ruff's DTZ007 flags a naive `strptime`), so
    the wall-clock is to the second.
  - `defect(source, clone, fixes, command)`: the steps of the defect check.
    The fix's commit comes from `git log main --format=%H --grep` on the
    exact `Issue:` line. The added test names come from the `+def test_`
    lines of `git show <sha> -- '*test_*.py'`, and each name's class from an
    `ast` walk of the file at that commit. The result is read from
    unittest's summary line: errors make it `could-not-run`, failures alone
    make it `failed`. `command` is the prefix before `-m unittest`. It
    defaults to `uv run --with pyyaml python`, and tests pass
    `[sys.executable]` so they need no network. The temporary worktree is
    removed in a `finally`.
  - `render(columns) -> str`: plain text. One block per slug and one per
    difficulty, a row per measure, a column per `single`, `pair`,
    `original`, with `missing` for an absent column. The `original` heading
    says it was run by older loop code and models.
  - `diffs(source, slug) -> str` for `--diff`.
- `pair/pair.py`: a `report` subparser with `--diff SLUG` and repeatable
  `--fixed-by SLUG=FIX`, a `run_report` beside `run_replay`, the usage line
  in the module docstring, and a constant `NO_REPLAYS = 14` beside
  `LOCKED`. It does not go in `EXIT`, whose docstring covers the outcomes
  of `run`, `groom`, `accept` and `resume`.
- `CONDITIONAL_RECIPES` in `.meta/lib/render/writers.py` and `CONTRACT` in
  `.meta/checks/files/justfile.py`: `pair-replay-report *args`, added the way
  `pair-replay` was. `justfile` is generated by `.meta/render.py`, so it
  is re-rendered with `just render`, not edited by hand.
- `pair/README.md`: a paragraph after the one on `just pair-replay`, a row in
  the command table, and exit 14 in the exit table.

### Order

1. Add `files` to the turn row, with its test, so later runs log it.
2. Add `report.py` with `measure`, `replays`, `original` and `render`, and
   their tests on fixture directories.
3. Add `defect` and its three tests.
4. Add `diffs`, the `report` subcommand, the recipe and the README.

### Tests (in `pair/test_pair.py`, a new `ReplayReportTest`)

A helper writes a fixture replay directory: `outcome.json`, `turns.jsonl`
and `events.jsonl` rows, a `landed.diff`, and, where a test needs one, a
clone made with `git init` whose `main` holds the Issue file and a module.
The source's `issues/done/<slug>.md` carries the difficulty. The tests are
the bullets under *How anyone will know it is done*. The `files` test goes
beside `test_a_turn_that_changed_code_keeps_it_and_its_own_note` and reuses
`notes_after` and `turn_rows`. The defect tests commit a fix in the source
with an `Issue: issues/done/fix.md` line and a `test_*.py` that adds one
test, which passes, fails, or imports a missing name against the clone's
module. Each defect test asserts that `git status --porcelain` and
`git worktree list` in the clone are unchanged afterwards.

### Risks

- Writing the fix's test files into the kept clone would change the evidence
  the developer inspects, and a run cut short would leave it changed. Hence
  the temporary worktree at `main`, removed in a `finally`.
- Telling `failed` from `could-not-run` depends on unittest's summary line
  (`FAILED (failures=N, errors=M)`). A test module that fails to import
  shows up as an error, which is the wanted reading. Anything unparsed
  counts as `could-not-run`. The converse costs something: a real defect
  that raises (a `TypeError`, say) rather than failing an assertion also
  reads as `could-not-run`. The issue accepts this, and the printed first
  line of the error lets the developer tell the two apart.
- The `original` rows for a slug that was sent back and started again span
  both runs. Summing them is what the parent asks for, and the wall-clock
  then includes the time between the runs. The report states this in the
  column's heading note instead of guessing at the runs' boundaries.
- Changing what `settle` returns touches the loop's hot path, so every
  caller is updated in the same step. A quick search shows one caller, in
  `Loop.work`.

### As built

- Where a replay ran more than one fixing Issue, its defect result is the
  worst of theirs, in the order `failed`, `could-not-run`, `passed`, `none`
  (`SEVERITY` in `pair/report.py`). Each note is printed under the block as
  `defect: <fix>: <first error line>`.
- A replay that did not land (`paused`, `sent-back`) left its change off
  the clone's `main`, so the fix's tests would run against the code it
  started from and could blame it for a defect it never landed. Its defect
  check is `could-not-run`, noted `<slug> <mode>: <outcome>, so its change
  is not on main`, and no worktree is made (`column` in `pair/report.py`).
- A run with no fixing Issue shows `none`. The `original` column has no
  defect check and shows `n/a`. An `original` run with no `landed` event
  shows `not landed`, and its wall-clock then runs to its last event.
- The defect tests run against the clone with `sys.executable`, not `uv`, so
  they need no network. The default command, `COMMAND`, is
  `uv run --quiet --with pyyaml python`.
- `just pair-replay-report` was tried against stereorepo itself. It keeps no
  replays yet, so the recipe printed `pair: no replays kept in …` and exited
  14. A malformed `--fixed-by` is a usage error and exits 2.

## Pair notes

> **primary, backlog turn 1**
>
> I've rewritten `issues/underway/replay-report.md` so it can be planned, and kept `difficulty: medium` (committed as `7adc1dc0`). I didn't split it: the reading and printing are mechanical, and only the check against the fixing Issue's tests takes real care.
>
> What changed:
>
> - **Where each measure comes from.** Each of the four criteria now names the file and field it is read from: the `outcome.json` from a replay, `gated`, `paused` and `sent-back` events, and `role`, `quiet`, `stage`, `cost_usd`, `cache_read` and `cache_write` in turn rows. It also says which way to read each: summed by difficulty taken from the Issue's file in `issues/done/`, null fields counted as missing, and the wall-clock of the original run measured from the slug's first `started` event to its `landed` event.
> - **A gap the old text didn't see.** It asked which files the secondary seat's turns changed, but a turn row doesn't record that, and the loop deletes `pair/<slug>` when it lands, so the clone can't tell either. The Issue now asks `record` in `pair/loop.py` to add a `files` field to each turn row. The report says `files not logged` for older rows, and back-filling them is out of scope.
> - **The defect check, which was vague.** It now gives these steps:
>   1. Find the fix's landing commit by its `Issue: issues/done/<fix>.md` line.
>   2. Take the `def test_…` functions that commit added in `test_*.py` files.
>   3. Write those files over the clone's copies, run each added test with `unittest`, then put the clone back.
>   4. Report `passed`, `failed` or `could-not-run`, or `none` when the fix added no such tests.
>
>   An import or missing-name error counts as `could-not-run`, not as the defect, because a replay may just name things differently. Fixes tested only outside Python `unittest` are out of scope.
> - **Tests.** The list now also covers summing by difficulty, the `original` column, the new `files` field, all three defect-check results with a clean clone afterwards, and `--diff`.

> **secondary, backlog turn 2**
>
> I checked your partner's rewrite of `issues/underway/replay-report.md` against the code and it holds up. The turn-row fields `record` in `pair/loop.py` writes, the keys `replay` in `pair/replay.py` puts in `outcome.json`, the event kinds, and the `Issue: issues/done/<slug>.md` line on landing commits all exist as the Issue says. I kept `difficulty: medium` and didn't split it.
>
> I filled three gaps (committed as `03f27cc8`):
> - **Single mode:** `single` mode has no secondary seat. The secondary-turn measure for a `single` replay now prints `n/a` rather than `0 of 0`, and there's a test for it.
> - **No replays:** with nothing under `.pair/replays/`, the report says so and exits non-zero. Otherwise it exits 0 whatever it finds. There's a test for this too.
> - **Putting the clone back:** the text only said "`git checkout`/`git clean`". It now says each overwritten file is restored, any file the check added is removed, and `git status --porcelain` in the clone must come back empty.

> **primary, backlog turn 3**
>
> I'm leaving `issues/underway/replay-report.md` as it is this turn. I checked your three additions against the code and kept them as written, with `difficulty: medium`:
>
> - **Single mode:** a `single` replay shows `n/a` for its secondary-seat turns, since that mode runs no secondary seat.
> - **No replays:** with nothing under `.pair/replays/`, the report says so and exits non-zero.
> - **Putting the clone back:** after the defect check, each overwritten file is restored and each added file removed, until `git status --porcelain` in the clone is empty again.
>
> I have nothing further to change.

> **primary, todo turn 1**
>
> I've written the plan under `## The plan` in `issues/todo/replay-report.md` and committed it as `70ce268a`. Nothing is implemented yet.
>
> **Where the change goes:**
> - **Turn rows:** `Loop.settle` in `pair/loop.py` returns the files a turn changed, and `Loop.record` writes them as a `files` field in each turn row.
> - **The report:** a new `pair/report.py`. One function, `measure`, counts both the replay columns and the `original` column from the stereorepo checkout's own logs, so they are counted the same way. It also holds the defect check, the plain-text output and the `--diff` view.
> - **The command:** a `report` subcommand in `pair/pair.py`, with a new exit code 14 for when there are no replays.
> - **The recipe:** `pair-replay-report`, added in `justfile`, `CONDITIONAL_RECIPES` and `CONTRACT`, the same way `pair-replay` was.
> - **The docs:** `pair/README.md` gets a paragraph on the report and new rows in its command and exit-code tables.
>
> **Order:** the `files` field first, so new turns start logging it; then the measures and output; then the defect check; then the command, recipe and README.
>
> **Tests:** a new `ReplayReportTest` builds fixture replay directories and covers each bullet under *How anyone will know it is done*. The `files` test sits beside the existing turn-notes test. The defect tests run the fix's tests with this machine's Python rather than `uv`, so they don't need the network. Each one checks that `git status --porcelain` and `git worktree list` in the clone are unchanged afterwards.
>
> **One change to the agreed text:** the defect check now runs the fixing Issue's tests in a temporary worktree of the clone's `main`, which it removes afterwards. Before, it wrote the test files into the kept clone and restored them, so a check cut off partway could leave the clone changed. I first claimed the clone's own checkout falls behind `main`, but that is wrong: `Loop.land` fast-forwards it. I corrected the text before committing.
>
> **Risks:**
> - The defect check tells `failed` from `could-not-run` by parsing unittest's summary line; anything it cannot parse counts as `could-not-run`.
> - For a slug that was sent back and started again, the `original` wall-clock includes the gap between the two runs.

> **secondary, todo turn 2**
>
> I checked your partner's plan in `issues/todo/replay-report.md` against the code and it works as written. `Loop.settle` has one caller, in `Loop.work`. Exit code 14 isn't used yet. `notes_after` and `turn_rows` exist in the tests, and `event_log` points at the source's `.pair/events.jsonl`. I fixed four things in the plan and committed them as `facfbced`:
>
> - **Summing by difficulty:** the plan didn't say how text measures add up. Outcome and defect result now become counts, such as `landed 2, paused 1`, while numbers add and file lists join. The secondary-turn measure stays `n/a` only if every slug being summed has `n/a`.
> - **The exit code:** "no replays" is now its own constant, `NO_REPLAYS = 14`, next to `LOCKED`. It doesn't go in `EXIT`, whose docstring covers only the outcomes of `run`, `groom`, `accept` and `resume`.
> - **The recipe:** `justfile` is generated by `.meta/render.py`, so the plan now says to add the recipe in `CONDITIONAL_RECIPES` and re-render with `just render`, not to edit `justfile` by hand.
> - **The original run's wall-clock:** event times are local timestamps to the second, so the plan says to parse them with `datetime.strptime`.
>
> I also added a risk. A real defect that raises an error, such as a `TypeError`, instead of failing an assertion will be reported as `could-not-run`. The Issue already accepts this, and the report prints the first line of the error so the developer can tell which it was.

> **primary, todo turn 3**
>
> I'm leaving the plan in `issues/todo/replay-report.md` as it stands; I've no further changes this turn. I checked your four fixes against the code and kept all of them:
>
> - **Exit code for "no replays":** `LOCKED = 11` sits in `pair/pair.py`, so the new `NO_REPLAYS = 14` belongs beside it rather than in `EXIT`.
> - **The recipe:** `justfile` says in its header that `.meta/render.py` generates it, so adding `pair-replay-report` in `CONDITIONAL_RECIPES` and re-rendering with `just render` is the right way in.
> - **Summing by difficulty:** counting outcomes and defect results (such as `landed 2, paused 1`) while adding the numbers is correct.
> - **The original run's wall-clock:** parsing the event timestamps with `datetime.strptime` is correct; they are local times to the second.
>
> The new risk is also fair to record: a real defect that raises an error, such as a `TypeError`, rather than failing an assertion will be reported as `could-not-run`. The report prints the error's first line, so the developer can tell which it was.

> **primary, in-progress turn 1**
>
> I've built `just pair-replay-report` as planned and committed it as `99e59edc`. `just gate pair` (321 tests plus ruff) and `just gate meta` both pass, and neither needed anything my sandbox couldn't run.
>
> **What it does now:**
> - **Turn rows record their files.** `Loop.settle` in `pair/loop.py` now returns the files a turn changed instead of a quiet flag; the turn counts as quiet when that list is empty. `Loop.record` writes them to each `turns.jsonl` row as `files`, next to `quiet`.
> - **The report.** A new `pair/report.py` prints, per slug and then summed by difficulty, columns for `single`, `pair` and `original`, the run that originally landed the Issue. A missing column says `missing`, and `single` shows `n/a` for secondary-seat measures. Two variants: `--fixed-by SLUG=FIX` runs the tests a later fixing Issue added, and `--diff SLUG` prints the two modes' landed diffs.
> - **The defect check.** It runs those tests in a temporary worktree of the clone's `main` and removes it afterwards, so the kept clone is never written to.
> - **The command and recipe.** `pair/pair.py` has a `report` subcommand and a new exit code, `NO_REPLAYS = 14`. The recipe is added in `CONDITIONAL_RECIPES` and `CONTRACT` and re-rendered into `justfile`, and `pair/README.md` has a paragraph plus rows in its command and exit-code tables.
>
> **Tests:** a new `ReplayReportTest` in `pair/test_pair.py` covers every bullet in the Issue. The three defect-check tests also confirm that the clone's `git status` and worktree list are unchanged afterwards. A new `files` test sits beside the turn-notes tests.
>
> **Where I departed from the plan** (the plan in the Issue file is updated to match):
> - `settle` returns the files in place of `quiet`, rather than as an extra value, since `quiet` is simply "no files".
> - Event times are parsed with `datetime.fromisoformat`, because ruff rejects a `strptime` with no time zone.
> - A new "As built" section records the remaining choices. When a replay has several fixing Issues, the worst result wins. `original` shows `n/a` for the defect check, and `not landed` when its logs have no `landed` event. The tests run the fix's tests with the test runner's own Python, so they need no network.
>
> **Tried for real:** stereorepo keeps no replays yet, so `just pair-replay-report` printed `pair: no replays kept in …` and exited 14. A malformed `--fixed-by` is a usage error and exits 2. The full report has only run on test fixtures so far, not on real replays.

> **secondary, in-progress turn 2**
>
> I reviewed your partner's build of `just pair-replay-report` and found one real bug, which I fixed and committed as `bf017a45`. `just gate pair` (322 tests plus ruff) and `just gate meta` both pass.
>
> **The bug.** A replay that paused or was sent back never landed, so its change never reached the clone's `main`. The defect check still ran the fixing Issue's tests against that `main`, which only holds the code the replay started from. It could report `failed` and blame the replay for a defect it never landed.
>
> **The fix.** In `column` in `pair/report.py`, a replay that did not land now gets `could-not-run` for its defect check, without running any tests or making a temporary worktree. Its note reads, for example, `x pair: paused, so its change is not on main`. A new test, `test_a_replay_that_did_not_land_is_not_checked_against_main`, covers it, and the "As built" section of the Issue file records it.
>
> **Also fixed:** the docstring of `ORIGINAL` said the note on the `original` column appears under every block. It actually appears once, after the last block.
>
> The rest held up when I checked it: the change to `settle` and `record`, how columns are summed, the `original` column, the exit code, and the recipe and README.
>
> Still unconfirmed: the defect check has only run in tests, with the test runner's own Python. Its default `uv run` command hasn't run against a real replay yet, because stereorepo keeps none.

> **primary, in-progress turn 3**
>
> I'm leaving this turn's code and Issue file as they are. Your fix is right: a replay that paused or was sent back never got its change onto the clone's `main`, so the fixing Issue's tests would only have checked the code it started from. Reporting `could-not-run` with a note, and skipping the worktree, is the right call. Your new test covers it, and the corrected docstring for `ORIGINAL` now matches what the report prints.
>
> As you said, the defect check's default `uv run` command still hasn't run against a real replay, because stereorepo keeps none yet.

Gated by the supervisor at 08:25: `meta`, `pair`, `specialization`; 99 steps passed.
