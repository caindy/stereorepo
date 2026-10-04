---
difficulty: medium
---
# Record each gate the loop runs, where a reader of the Issue can find it

The supervisor runs the gate outside the seats' sandbox (`run_gate` in
`pair/loop.py`) when it closes `in-progress/` (`requirement`), a Flight check
(`flight_checked`) or a grooming pass, and again in `land` when a rebase
moved the branch. Nothing records what that gate ran or what it found.
`events.jsonl` has no entry for it, the Issue file does not mention it, and the
seats cannot see it from their sandbox.

fitch-mvp showed what that costs. On `inverse-pairs-follow-the-record`, the
seats' last note said the four rewritten Neo4j queries "have never been run
against Neo4j", because no Neo4j was reachable in their sandbox. In fact the
supervisor's gate had run them, with Docker, before the Issue moved to
`desk-check/`: a step that could not run would have paused the loop
instead. The desk check showed the seats' note and nothing of the gate, so
the developer was told something false, and the session supervising the
loop repeated it and re-ran the gate by hand.

## Wanted

- **An event per gate run.** Each time `run_gate` actually runs the gate (not
  when the branch changes nothing and it passes without running), the event
  log gets one `gated` event with the slug the loop's other events carry
  (`st.slug`, which a grooming pass has too) and these fields:
  `stage` (`in-progress`, `flight-check`, `grooming`, or `landing` for the
  gate in `land`); `targets` (the list `touched.select` chose, or null for
  the whole gate); `outcome` (`passed`, `failed` or `could-not-run`, the
  last for a `GateUnrunnable`, including one from unwritable pages);
  `steps`, the count of step lines (`ok`, `x`, `?`) in the gate's output;
  and `failed` and `could_not_run`, the names of those steps (`FAILED_STEP`,
  `COULD_NOT`). The event table in `pair/README.md` lists it.
- **A line in the Issue file.** The gate that closes `in-progress/` appends
  one line to the end of the Issue file on its branch, whatever the outcome,
  and commits it, such as "Gated by the supervisor at 11:58: `meta`,
  `fitch`; 96 steps passed." The time is the `gated` event's own, and a
  null `targets` reads as "the whole gate". A failure names the failed steps, a step that
  could not run is named with why. A `developer` Issue's desk check, and a
  done child that a Flight's brief summarizes, then show what the supervisor
  checked beside what the seats could. Other gates write only the event.
- **The last gate in the status.** `status_view` gives each `underway` entry
  a `gate` field: the last `gated` event's `stage`, `outcome` and time for
  that Issue, or null; `just pair-status` prints it in one line.
- **The seats know the gate is not theirs.** `pair/prompts/stage-in-progress.md`
  (or `primary.md` and `secondary.md`, wherever it reads best) says that the
  supervisor's gate, run outside the sandbox before the Issue leaves
  `in-progress/`, is where a step the sandbox cannot run is checked, so a
  note says such a step is left to that gate, not that it is unchecked.

## How anyone will know it is done

Tests in `pair/test_pair.py`, with a fake gate:

- Closing `in-progress/` with a passing, a failing and a could-not-run gate
  each writes one `gated` event with the right `outcome`, `steps`, `failed`
  and `could_not_run`, and one committed line at the end of the Issue file.
- A branch that changes nothing writes no `gated` event.
- A landing whose rebase moved the branch writes a `gated` event with
  `stage: landing` and adds no line to the Issue file.
- `pair-status --json` shows the last gate's outcome under the Issue
  underway.

## Out of scope

- What the gate runs, or how its targets are selected (DR-303).
- Showing the gate's output itself; the pause reason and the note already
  carry it when it fails.

## The plan

All of it is in `pair/`: `loop.py`, `test_pair.py`, `README.md` and one
prompt.

1. **Read a run from the gate's output.** A pure function in `loop.py`,
   `gate_record(out, targets, ok) -> dict`, returns the event's fields
   (`targets`, `outcome`, `steps`, `failed`, `could_not_run`). The step lines
   are the `ok`, `x` and `?` lines in `.meta/gate`'s shape. `FAILED_STEP` and
   `COULD_NOT` exist already. Add an `OK_STEP` beside them, copied from
   `.meta/gate`'s `OK`, with the same note that the script is not a module.
   The closing line of `.meta/gate` (`main` there), `ok <label> — N steps
   across …` or `x  <label> (n)`, is not a step: its label is the targets
   joined by spaces, or `portfolio`. It is left out by counting only the
   steps `.meta/gate` prefixed with a Project (see "Step lines that are not
   the gate's" under Risks), not by position. The
   `?  steps that could not run (n)` summary does not match `COULD_NOT`. `outcome` is `passed` when `ok` holds and nothing could not
   run, `could-not-run` for any result `run_gate` returns as a
   `GateUnrunnable`, and `failed` otherwise. Because of that, it is derived
   from `run_gate`'s result, not from the output alone.
2. **Log it in `run_gate`.** `run_gate(self, slug, stage)` builds the record
   after `redact` (step names may carry a declared value), stamps it with
   `at` taken once, and logs `self.event("gated", slug, at=at, **record)`.
   `append_event` lets a field override `at`, so the event and the line share
   the time. The early `return None` for an empty diff stays before any of
   this, so it logs nothing. As built, the work is in `gate_run(slug,
   stage)`, which returns the result and the event's row (None when nothing
   ran); `run_gate` keeps its return type and returns only the first, and
   the one caller that writes a line calls `gate_run`. There is no
   `self.last_gate`. Callers:
   - `requirement`: for a grooming pass `(st.slug, GROOMING)`, for
     `in-progress/` `(st.slug, "in-progress")`.
   - `flight_checked`: `(st.slug, FLIGHT_CHECK)`, both calls.
   - `merge`: `(st.slug, "landing")`. That also covers `accept`'s
     `force_gate`.
3. **The line in the Issue file.** A `Loop.keep_gate(st, row)`, modelled on
   `keep_note`, runs in `requirement`'s `in-progress` branch right after the
   gate and before the result goes back to `close_stage`. It appends
   `Gated by the supervisor at HH:MM: <targets or "the whole gate">; …` to
   the Issue file, preceded by a blank line, and commits it with
   `Seat: loop`. It moves `st.head`, so `absorb_developer` does not take the
   commit for the developer's, and leaves `st.seen` alone, so both seats see
   the line in their next diff. The wording after the semicolon:
   - for a pass, `N steps passed.`;
   - for a failure, `N steps; failed: a, b.`;
   - for a step that could not run, `N steps; could not run: a (why), …`.

   As built, `could_not_run` in the event is a mapping from step to why,
   not a list of names, so the line can name the why. "1 step" is singular.
   Backticks are stripped from a why, so it cannot open a code span.
4. **Status.** `status_view` reads `event_log(repo)` once (a missing file
   means no events) and gives each `underway` entry `gate`: `{stage,
   outcome, at}` of the last `gated` event whose `loop` and `slug` match
   that state, or null. `status` adds one line under each underway entry,
   such as `last gate: in-progress, passed at 11:58`. Update the
   `status_view` docstring's `underway` item, and the `--json` keys in the
   README if they list fields.
5. **README and prompt.** Add a `gated` row to the event table in
   `pair/README.md`, with fields `stage`, `targets`, `outcome`, `steps`,
   `failed`, `could_not_run`. Add a sentence to
   `pair/prompts/stage-in-progress.md`: the supervisor runs the gate outside
   the sandbox before the Issue leaves `in-progress/`, and a step the sandbox
   cannot run is checked there, so a note says such a step is left to that
   gate, not that it is unchecked.

### Tests (`pair/test_pair.py`)

- `gate_record` unit tests on literal outputs in `.meta/gate`'s shape:
  - a pass with `ok a/x`, `ok a/y` and the closing line counts 2 steps;
  - a failure names `a/x` and not the closing `x  portfolio (1)`;
  - a `?` step is named in `could_not_run`, and the summary line is not.
- Through the bench's fake `gate`, using `implemented` as the existing
  in-progress tests do:
  - pass, failure (`b.gates = [(False, …), True]`) and `UNRUNNABLE` each log
    one `gated` event with `stage: in-progress` and the right outcome, and
    leave one `Gated by the supervisor` line in the Issue file at that
    commit;
  - a branch that changes nothing logs no `gated` event (call `run_gate` on
    a fresh worktree, as `gate_on_branch` sets one up);
  - a landing whose rebase moved the branch (the `during_gate`/commit-on-main
    pattern of `test_a_gate_step_that_could_not_run_while_landing_pauses_the_landing`)
    logs a `gated` event with `stage: landing`, and the Issue file gains no
    second line;
  - `status_view` after a gated close shows `gate.outcome` under the
    `underway` entry, and null before any gate.
- The existing direct callers of `run_gate` in the tests (`gate_on_branch`
  and the two around it) pass a slug and stage.

### Risks

- **Existing tests that pin exact events, bodies or commit counts.** Every
  test that closes `in-progress/` now gets an extra commit and a line in the
  Issue file, and the default fake gate passes with empty output (0 steps).
  Expect to update assertions on event lists (the event-log tests that read
  `event_log`), on note diffs shown to seats (`b.sent` indices), and on
  Issue bodies. Fix these assertions; don't special-case the code.
- **Blockquote absorption.** The Issue file usually ends in a `## Pair
  notes` blockquote, and a plain line directly after `> …` is read as part
  of the quote. Hence the blank line before. Check that `board.with_note`
  still appends the next note under the same `## Pair notes` heading after
  a gate line.
- **Step lines that are not the gate's.** `gate` in `pair/pair.py` returns
  `stdout + stderr`, and `.meta/gate` passes every line a Project's gate
  prints that is not in A21's shape to stderr, while the Project's own
  stderr goes straight through. A test runner's `ok …` line there would be
  counted. `.meta/gate` prefixes every step it forwards with its Project
  (`ok meta/rendered prose`, `x  fitch/tests (2)`), and the only unprefixed
  one is `?  <project>: no gate asserted`. So `gate_record` counts an `ok`
  or `x` line only when its step holds a `/`, and a `?` line when its step
  holds a `/` or is a Project with no gate; the closing line then drops out
  without the last-line rule, since its label is Project names joined by
  spaces or `portfolio`. Pin this with a test whose output carries a stray
  `ok something` line.
- **`status_view` runs on every event**, since `append_event` calls
  `publish`. Read `events.jsonl` once and keep the last `gated` row per
  `(loop, slug)`; do not re-read it per underway entry.
- **A resumed could-not-run gate** adds a second line, which is accurate (it
  ran twice) and is accepted as is.
- **`self.last_gate` is a side channel.** Settled while building: the
  wrapper (`gate_run`) was used instead.
- **Found while building: a squash diff loses rename detection.** The line
  makes a small Issue file differ enough from its `underway/` copy that
  `git diff --name-only` no longer pairs the two as a rename.
  `test_a_commit_on_main_while_merge_gates_is_not_reverted` now asks with
  `--no-renames` and expects both paths, which does not depend on git's
  similarity threshold.

## What the next reader should know

- The work is in `pair/loop.py`: `gate_record` and `gate_line` (pure),
  `Loop.gate_run` and `Loop.keep_gate`, `last_gates` and `last_gate_lines`
  for `status_view` and `status`. `last_gate_lines` exists only to keep
  `status` under ruff's branch limit.
- The event's `at` is taken just before the gate starts, not when the event
  is written, and the line in the Issue file uses the same `at`.
- `pair/README.md` describes the line in the Issue file in step 2 of the
  loop, beside the gate's pauses, and the `watch` row names the last gate.
- A `GateUnrunnable` from unwritable pages has outcome `could-not-run` and
  still lists its `rendered prose` steps under `failed`, which is what the
  gate printed.
- The default fake gate in the test bench passes with empty output, so the
  `gated` events in older tests record 0 steps. That is expected.
- Run directly, `python -m unittest` fails the two `GateLintTest` tests
  inside the seats' sandbox (ruff's binary is not found in uv's build
  cache). They pass under the `pair` Project's gate, so it is the sandbox,
  not this change.

## Pair notes

> **primary, backlog turn 1**
>
> I've groomed `issues/underway/record-each-gate-run.md` and set it to `difficulty: medium`. It's one piece of work in `pair/` (an event, a line in the Issue file, a status field, a prompt sentence and tests), so it doesn't need splitting. Nothing in the result needs the developer to check it by hand.
>
> I checked the issue against `run_gate`, `requirement`, `flight_checked` and `land` in `pair/loop.py`, and `select` in `pair/touched.py`. The main changes:
>
> - **Every place the gate runs is now listed.** As well as closing `in-progress/` and landing, the supervisor gates a Flight check and a grooming pass. Each one gets a `gated` event with stage `in-progress`, `flight-check`, `grooming` or `landing`.
> - **When there's an event is now defined.** The landing gate only runs when a rebase moved the branch. A branch that changes nothing passes without running the gate, so it gets no event.
> - **The event's fields are spelled out:**
>   - `targets` (null means the whole gate ran)
>   - `outcome` (`passed`, `failed` or `could-not-run`)
>   - `steps`, a count of the gate's `ok`/`x`/`?` lines
>   - the names of the steps that failed or could not run, taken with the existing `FAILED_STEP` and `COULD_NOT` patterns
> - **The line in the Issue file is narrowed.** Only the gate that closes `in-progress/` appends and commits it, whatever the outcome. I dropped the "including 24 Neo4j tests" example because nothing can get that from the gate's output.
> - **The status field is defined.** Each entry under `underway` in `status_view` gets a `gate` field: the stage, outcome and time of the last gate run for that Issue.
> - **The tests are in behaviour only:** a pass, a failure and a could-not-run on closing `in-progress/`; no event for a branch that changes nothing; a landing event with no line in the Issue file; and the field in `pair-status --json`.
> - **One more item is out of scope:** showing the gate's full output, which the note and the pause reason already carry when it fails.

> **secondary, backlog turn 2**
>
> I checked my partner's grooming of `issues/underway/record-each-gate-run.md` against `pair/loop.py` and it holds up. The issue now lists all four places the supervisor runs the gate: closing `in-progress/` (`requirement`), a Flight check (`flight_checked`), a grooming pass, and `land` when a rebase moves the branch. It also gets right that nothing is logged when the branch changes nothing, since `run_gate` then passes without running the gate. `medium` is the right difficulty: it's one piece of work in `pair/`, with no split and no check by hand needed.
>
> I made two small changes to the issue file:
> - **Which slug the event carries.** The issue said each `gated` event carries "the Issue's slug", but a grooming pass has no Issue. It now says the event carries `st.slug`, the same slug the loop's other events use; a grooming pass has one too.
> - **What the line in the Issue file shows.** The time in the line is the `gated` event's own time, and when the gate ran in full (`targets` is null) the line reads "the whole gate".

> **primary, backlog turn 3**
>
> I'm leaving the issue as it is: both of my partner's changes match the code.
>
> - **The slug:** a grooming pass has no Issue, but it does have a slug in the loop's state (`st.slug`), and the loop's other events already carry it. So "the slug the loop's other events carry" is the accurate wording.
> - **The line in the Issue file:** taking the time from the `gated` event, and writing "the whole gate" when no targets were selected, settles the two details I had left open.
>
> `difficulty: medium` still fits. It's one piece of work in `pair/`, so there's nothing to split, and nothing in it needs the developer to check by hand.

> **primary, todo turn 1**
>
> I've written `## The plan` in `issues/todo/record-each-gate-run.md`. Planning didn't turn up anything that stops the issue being done as written, so there is no `# Needs elaboration` section. Nothing is implemented yet.
>
> The work is all in `pair/`, in five steps:
>
> 1. **Read a run from the gate's output.** A new function, `gate_record`, turns the gate's output into the event's fields. It counts the step lines and names the steps that failed or could not run. The step counts and names come from parsing `.meta/gate`'s line formats, using the existing `FAILED_STEP` and `COULD_NOT` patterns plus a new `OK_STEP`. It doesn't count the gate's closing summary line as a step; `unwritable_pages` already treats that line this way.
> 2. **Log the event in `run_gate`.** `run_gate` takes the slug and stage, logs one `gated` event once the declared values have been redacted from the output, and logs nothing when the branch changes nothing. Its callers pass `grooming`, `in-progress`, `flight-check` or `landing`. `landing` also covers `accept`, which lands through the same path. The time is taken once, so the event and the line in the Issue file show the same time.
> 3. **Add the line in the Issue file.** A new `keep_gate`, modelled on `keep_note`, appends and commits the line only when closing `in-progress/`. It moves `st.head`, the loop's record of the last commit it knows about, so the commit isn't mistaken for the developer's. Both seats see the line in their next diff.
> 4. **Show it in the status.** `status_view` gives each Issue underway a `gate` field from the last `gated` event, and `pair-status` prints it as one line.
> 5. **Update the README and the prompt.** The event table in `pair/README.md` gets a `gated` row, and `pair/prompts/stage-in-progress.md` tells the seats that the supervisor's gate is where a step their sandbox can't run gets checked.
>
> The tests cover `gate_record` on sample outputs, and, through the test bench's fake gate:
> - a pass, a failure and a step that could not run when closing `in-progress/`;
> - no event when the branch changes nothing;
> - a landing event that adds no line to the Issue file;
> - the new `gate` field in `status_view`.
>
> The risks the plan records:
>
> - **Existing tests will need updating.** Every test that closes `in-progress/` now gets an extra commit and a line in the Issue file, so assertions that pin exact events, Issue bodies or the messages sent to the seats will change.
> - **The line could be swallowed by the notes above it.** An Issue file usually ends with the pair's quoted notes, and a plain line straight after a quote is read as part of it. The line needs a blank line before it, and the next note should still land under the same `## Pair notes` heading.
> - **A resumed gate that still can't run a step adds a second line.** That's accurate, since the gate did run twice, and the plan accepts it.
> - **`self.last_gate` is a side channel.** Step 2 stores the event on the loop so step 3 can write the line from it. The plan allows a small wrapper that returns both instead.

> **secondary, todo turn 2**
>
> I checked my partner's plan in `issues/todo/record-each-gate-run.md` against `pair/loop.py`, `pair/pair.py` and `.meta/gate`. It holds up apart from one real gap, which I fixed in the plan.
>
> **The gap: miscounted gate steps.** `gate` in `pair/pair.py` returns the gate's stdout and stderr joined together. A Project's own stderr reaches that output unfiltered, so a test runner's stray `ok …` line would be counted as a gate step. The plan also told `gate_record` to skip the gate's summary line by its position, which is fragile once that noise is mixed in.
>
> I fixed it by changing the rule rather than adding a workaround:
> - **Count only the gate's own step lines.** `.meta/gate` puts the Project's name in front of every step it passes on (`meta/…`, `fitch/…`). The one exception is `?  <project>: no gate asserted`. `gate_record` will count only those lines.
> - **The summary line drops out on its own.** Its label is either the targets joined by spaces or `portfolio`, never a prefixed step, so the position rule is gone.
> - **A test pins it:** an output with a stray `ok something` line must not change the count.
>
> I updated step 1 to match and added the explanation under Risks.
>
> **A smaller risk added.** `status_view` runs on every event, because each event republishes the status. The plan now says to read `events.jsonl` once per call and keep only the last `gated` row for each loop and Issue, rather than re-reading the log for each Issue underway.
>
> The rest checks out, so I left it unchanged:
> - `append_event` lets a field override the event's time, so the event and the line in the Issue file can share one time.
> - `keep_note` is the right pattern for `keep_gate`.
> - The landing gate lives in `merge`, and `accept`'s forced gate goes through it.
>
> The plan is still not implemented, and nothing stops the issue being done as written.

> **primary, todo turn 3**
>
> I'm leaving the plan as it is. I checked my partner's change against `.meta/gate`, and the new rule for counting steps holds:
>
> - **Every step `.meta/gate` passes on carries a `/`.** The script rewrites each step as `<project>/<step>`, and the Project's name is the last part of its id, so the name itself contains no `/`.
> - **The two unprefixed lines are handled.** The closing summary's label is either Project names joined by spaces or `portfolio`, so a rule that requires a `/` leaves it out without relying on its position. The other is `?  <project>: no gate asserted`, which the rule names as its one exception.
> - **Stray output is excluded.** A test runner's own `ok …` line that reaches the gate's output through stderr no longer counts as a step.
>
> Reading `events.jsonl` once per `status_view` call is also right, since the status is republished on every event.
>
> The plan still hasn't been implemented, and nothing in it stops the issue being done as written.

> **primary, in-progress turn 1**
>
> I've implemented the plan and committed it. `just gate meta` and `just gate pair` both pass, and the `pair` gate ran all 268 tests.
>
> **What it does now:**
> - **An event for each gate run.** Every time the supervisor runs the gate it logs one `gated` event. That covers closing `in-progress/`, a Flight check, a grooming pass, and a landing after a rebase moved the branch. The event records the stage, the targets, the outcome, the step count, the steps that failed, and each step that could not run with the reason. A branch that changes nothing logs no event.
> - **A line in the Issue file.** Closing `in-progress/` also appends and commits a line to the Issue file, such as `Gated by the supervisor at 11:58: \`meta\`, \`fitch\`; 96 steps passed.` It's written whatever the outcome, and both seats see it in their next diff.
> - **The status.** `pair-status` prints a `last gate:` line under the Issue underway, and `--json` has a matching `gate` field.
> - **Docs and prompt.** `pair/README.md` lists `gated` in its event table. The in-progress prompt tells the seats that a step their sandbox can't run is checked by the supervisor's gate, so their note should say that rather than "unchecked".
>
> **Where the work departed from the plan** (recorded in the issue file):
> - **No side channel.** Instead of storing the event on the loop (`self.last_gate`), I added a wrapper, `gate_run`, that returns both the result and the event. `run_gate` keeps its old return type.
> - **Reasons kept.** `could_not_run` in the event maps each step to its reason, rather than listing names, so the line in the Issue file can give the reason.
> - **One existing test changed.** `test_a_commit_on_main_while_merge_gates_is_not_reverted` was relying on git detecting a rename. The extra line makes the small test Issue file too different for that, so the test now uses `--no-renames` and expects both paths.
>
> **Tests changed or added in `pair/test_pair.py`:**
> - **Existing tests.** Two event-log tests now expect the `gated` event.
> - **`gate_record`.** Unit tests check that a stray `ok …` line in the output isn't counted as a step.
> - **Loop tests.** Pass, failure and could-not-run on closing `in-progress/`, a landing gate that adds no second line, no event for a branch with no changes, and the status field.
> - **Notes stay together.** A check that a later note still goes under the same `## Pair notes` heading after the line.
>
> Run directly with `python -m unittest` inside the sandbox, two `GateLintTest` tests fail because the ruff binary can't be found. They pass under `just gate pair`, so the failure comes from the sandbox, not this change.

> **secondary, in-progress turn 2**
>
> My partner's implementation matches the plan and I found no bugs in it, so the only gap I filled was in the documentation. `just gate meta` passed (95 steps) and `just gate pair` passed (268 tests, plus ruff), and the change is committed.
>
> I checked these points in the code and they hold:
> - **Moving the record of the loop's last commit.** `keep_gate` moves `st.head`, the loop's record of the last commit it made, before a could-not-run pause saves the state. So resuming does not mistake the gate's commit for the developer's.
> - **Landing.** The extra commit only touches `issues/`, so landing still sees the branch as not moved and does not gate again.
> - **Squash diff.** The test now lists the deletion and the addition instead of a rename, and nothing in `pair/` relies on git spotting renames.
> - **Secrets.** Step names are counted after secrets are scrubbed from the gate's output, so a declared value cannot reach the event or the Issue file.
>
> What I added:
> - **`pair/README.md`:** a paragraph in step 2 of the loop, next to the gate's pauses, describing the `gated` event and the "Gated by the supervisor at …" line in the Issue file. Before this, only the event table mentioned it. The `watch` row now says `pair-status` shows the last gate of the Issue underway.
> - **The issue file:** two notes for the next reader. One says where the README covers this. The other covers a gate that fails only on pages the seats cannot write: it is logged as `could-not-run` but still lists its `rendered prose` steps under `failed`, because that is what the gate printed.

> **primary, in-progress turn 3**
>
> I'm changing nothing this turn. My partner only touched documentation, and it matches the code:
>
> - **README step 2:** the new paragraph is accurate. Every gate the loop runs logs a `gated` event. Only the gate that closes `in-progress/` appends and commits the line to the Issue file (`Loop.keep_gate`), and it does so whatever the outcome.
> - **README `watch` row:** "what is underway with its last gate" is what `pair-status` now prints, from the `last gate:` line in `status`.
> - **Unwritable pages:** a gate that fails only on pages the seats cannot write is logged as `could-not-run` and still lists its `rendered prose` steps under `failed`. That's what `gate_record` does, because it records the steps the gate printed and takes the outcome from what `run_gate` returns.
>
> My partner ran `just gate meta` and `just gate pair` on these changes, and both passed.
