---
difficulty: medium
parent: pair-versus-single-seat
---

# Keep a replay's tree as the replayed Issue's own era would have it

A replay (`pair/replay.py`) runs today's loop against a clone reset to the
commit a landed Issue started from. Wherever today's loop writes into the
clone's tree, or calls into the clone's operator surface, in a form that the
clone's older code or checks do not accept, the replay fails for that reason
and not for anything the seats did. The first round of
`pair-versus-single-seat` (8 October 2026) hit it twice:

- **The state file, reached through the gate's call.** The loop keeps its
  runtime state in `.pair/state.json` inside the clone, now with the fields
  `models` and `mode`. In `squash-reverts-commits-on-main` (single), the
  supervisor gated with `just gate meta pair` (`gate` in `pair/pair.py`
  passes every target in one call). The clone's own `gate` recipe, from before
  `gate-takes-several-targets`, took one target, so `just` ran `gate meta` and
  then the `pair` recipe: the clone's old loop itself, which read the
  supervisor's `.pair/state.json`, met the `models` field its `State` lacks,
  and crashed before any pair test ran. The kick-back commit in the kept clone
  (`.pair/replays/squash-reverts-commits-on-main-single/`) records it.
  `squash-reverts-commits-on-main` and `fresh-seat-after-refusal` were sent
  back in both modes for this reason alone; the seats' note said "This needs
  you; another turn won't change it."
- **The notes.** Today's loop keeps a seat's own note in the Issue file and
  puts it back if a seat edits it (`Loop.keep_note`, `Loop.restore_notes`).
  The clone's older `.meta` checks predate `notes-rewrite-refused-citations`,
  so they do not skip quoted Pair notes. In `bootstrap-render-step` (two
  seats), a note quoted a class-and-slot citation the old check refuses, the
  seats could not remove it, and every gate failed on that one line until the
  round cap sent it back.

Either clash can strike any replay in either mode, so it adds noise to both
sides of the comparison and makes some results meaningless. The round was
stopped after 16 of its 20 replays.

## To reproduce

`just pair-replay squash-reverts-commits-on-main --mode single` from today's
`main`: the Issue changes `meta` and `pair`, the supervisor's gate fails in
the `pair` recipe on `.pair/state.json`, and the outcome is `sent-back`.
`just pair-replay bootstrap-render-step --mode pair` fails the same way on its
notes when a seat quotes a citation, which depends on what the seats write.

## Wanted

- **Every clash found and named.** Find each place today's loop writes into
  the clone or calls into it for its own purposes, not only the two above: at
  least its runtime state (`.pair/`), the turn notes and restored notes, the
  supervisor's gate lines (`Loop.keep_gate`), and its calls to the clone's
  recipes (`just gate`, `just setup`, `just deliver`, `just --summary` in
  `pair/pair.py`). The module docstring of `pair/replay.py` says, for each,
  how a replay keeps it out of the old code's way, or why it cannot reach it.
- **The gate is called in a form any era accepts.** A replay's gate (the
  `gate` seam the loop gets from `build_loop`, through `make_loop` in
  `run_replay` in `pair/pair.py`) runs `just gate
  <target>` once for each target and joins the results, so an older
  single-target recipe never runs a second recipe as a target. With no
  targets (the whole gate), it runs `just gate` once, as now. The gate passes
  only if every call passes, and its output is each call's output in turn,
  headed by the target it ran.
- **The notes stay where the seats see them, and out of the old checks.**
  Recommended: the replay's gate runs against a copy of the worktree in which
  the Issue file has the loop's own additions taken out (the `Pair notes`
  section and the supervisor's gate lines), so the clone's checks see the
  Issue file as its era wrote it, and the seats still read and write the notes
  as they do outside a replay. The other way, keeping the notes outside the
  Issue file during a replay, changes what the seats see and so what the
  comparison measures. The seats may choose otherwise if the code shows a
  reason; either way, record the choice in the docstring.
- **The runtime state is not read by the clone's code.** With the gate called
  one target at a time, nothing in the clone's era runs its loop, so moving
  `.pair/` out of the clone is not required; if a remaining path reads it,
  move the replay's runtime directory outside the clone.
- **The replayed Issue's own files** are otherwise exactly as they stood at
  its start commit, and the seats still see each other's notes in two-seat
  mode.
- **A clash shows in the outcome.** When a replay ends other than `landed` and
  its last `gated` event has the outcome `failed` or `could-not-run`, the
  replay gates the clone's `Replay <slug>` commit once more, with no seat's
  work, on that event's `targets` (the whole gate where they are `null`),
  through the same era-safe gate as above. It checks that commit out in a
  separate tree, so the kept clone stays as the seats left it. If that also fails, the failure is not the seats':
  `outcome.json` says `clashed` instead of `sent-back` or `paused`, and the
  replay keeps that gate's output as `clash.txt` beside it. `pair/report.py`
  leaves `clashed` replays out of both modes' columns and counts them.

## How anyone will know it is done

Tests in `pair/test_pair.py`, over temporary repositories:

- A replay of an Issue that changes `pair/`, from a start commit whose
  `justfile` has a single-target `gate` recipe and a `pair` recipe that fails
  when it runs, gates each target on its own, never runs the `pair` recipe,
  and lands.
- A replay of an Issue whose seat writes a Pair note quoting text that the
  start commit's check refuses (a stub check failing on that text anywhere in
  the Issue file) gates past the note and lands, and the landed Issue file
  still holds the note.
- A replay whose seats' work fails a gate that the `Replay <slug>` commit also
  fails ends `clashed` with `clash.txt`; one whose work fails a gate the
  `Replay <slug>` commit passes ends `sent-back` as before.
- `pair/report.py` leaves a `clashed` replay out of the measures and reports
  how many there were per mode.
- `pair/README.md` says what a replay keeps outside the clone's tree and
  what `clashed` means.

## Out of scope

- Re-running the round, which the developer starts once this lands.
- Replaying another portfolio's Issues.
- Changing how the loop gates outside a replay: `gate` in `pair/pair.py`
  keeps passing every target in one call.

## The plan

The replay owns every change. `replay` in `pair/replay.py` wraps the gate of
the loop `make_loop` returns (`loop.gate`, the `Gate` seam in `pair/loop.py`),
so the real `gate` in `pair/pair.py` and the tests' fake gates both pass
through it, and `build_loop` and `Loop` are not changed.

1. **Strip the loop's additions (`pair/board.py`).** Add `without_notes(text,
   stops)`: an Issue file without its `Pair notes` sections (`_note_spans`,
   with `NOTE_STOPS` from `pair/loop.py`) and without any line that `gate_line`
   writes (a line that starts `Gated by the supervisor at `), with the blank
   lines that separated them collapsed. Unit tests: a file with notes, gate
   lines after the notes, and a section after them, such as `The plan`, comes
   back as it was before the loop wrote anything; a file with none comes back
   unchanged.
2. **The era-safe gate (`pair/replay.py`).** Add `era_gate(gate, slug) ->
   Gate`. For `None` targets it calls `gate(tree, None, env)` once. Otherwise
   it calls `gate(tree, [target], env)` for each target in turn. Each call's
   output goes under a heading line, `=== just gate <target> ===`, and the
   result passes only if every call passed. The outputs are joined in target
   order, except that a failed call's output goes after every passed one:
   `gate_fails` in `pair/loop.py` hands the seats only the last `GATE_TAIL`
   characters, so a failure under the first target followed by a long
   passing second target would otherwise reach the seats as a passing tail.
   The docstring says so. Around the calls, it rewrites the
   replayed Issue file in `tree` (`board.read(tree, slug)`) to
   `without_notes`, and in a `finally` writes back the exact bytes it read.
   - **Where the gate runs: in place, not a copy.** The Issue recommends a
     copy of the worktree. Rewriting the file in place and restoring it gives
     the clone's checks the same view, and the supervisor gates between turns,
     when no seat is writing. A copy (`git worktree add`) would lack the
     environment that `provision` (`just setup`) built in `worktrees/pair`, so
     each gate would provision again or gate unprovisioned. The module
     docstring records this choice.
3. **The rest of the clone's operator surface (`replay`).** After
   `make_loop`, set `loop.gate = era_gate(loop.gate, slug)` and `loop.deliver
   = None`, so a replay never runs the clone's `just deliver`. `just setup`
   is the clone's own era provisioning its own tree, and `just --summary` only
   reads, so both stay. `.pair/` and `worktrees/` are already kept out of
   git's view by `IGNORED`. Once the gate runs one target at a time, nothing
   in the clone's era runs the clone's loop, so `.pair/` stays in the clone.
4. **Clash detection (`replay`).** Run this after `supervise` and before
   writing `outcome.json`, only when `outcome_of(answer) != "landed"`. Read the
   clone's `events.jsonl` and take the last `gated` event for `slug`. If its
   `outcome` is `failed` or `could-not-run`, gate the `Replay <slug>` commit
   (`base`) in a detached worktree of the clone in a temporary directory
   outside it. Run `loop.provision` there first when it is set; `provision`
   in `pair/pair.py` runs `just setup` with `check=True`, so catch its
   `CalledProcessError` and count it as the base failing (`clashed`, with
   the error in `clash.txt`) rather than let it crash the replay before
   `outcome.json` is written. Use the
   wrapped gate and `loop.gate_env()` on the event's `targets`. The gate
   clashes if it returned false or its output has a step that could not run
   (`gate_unrunnable`). If it clashes, the outcome becomes `clashed` and its
   output is written to `clash.txt` in the replay's directory. Remove the
   worktree in a `finally`, with `git worktree remove --force` and then
   `prune`, so the kept clone has no stray worktree. Extend the module
   docstring's file list and the outcomes it names.
5. **Report (`pair/report.py`).** In `report`, leave a `clashed` replay out of
   `by_slug`, and count clashed replays by mode. Each slug's block, and the
   end of the report, gains a line such as `clashed: single 1, pair 0`. A slug
   whose replays all clashed still gets a block, so its count shows. Its mode
   columns read `missing`. The original column is still shown.
6. **Docs.** In the `pair/replay.py` module docstring, add one paragraph per
   clash point: `.pair/`, `worktrees/`, the notes and gate lines, the gate
   call, `setup`, `deliver` and `--summary`, each saying how the replay keeps
   it out of the old code's way. In `pair/README.md`'s replay section, say
   what a replay keeps outside the clone's tree and what `clashed` means.

### Tests (`pair/test_pair.py`, in `ReplayTest` and `ReplayReportTest`)

- **One target per call.** The fake gate records the targets of each call, and
  a branch touches two Projects. Every call has at most one target, and the
  replay lands. A second test, `skipUnless(shutil.which("just"))`, uses the
  real `gate` from `pair/pair.py`. Its start commit has a single-target `gate
  *target` recipe and a `pair` recipe that writes a marker file and fails. The
  replay lands and the marker is absent.
- **Notes stripped.** In a two-seat replay, the fake gate fails whenever the
  Issue file it is handed contains a marker string, and a seat's note quotes
  that marker. The replay lands, the landed Issue file on the clone's `main`
  still holds the note, and the working file is unchanged after each gate.
- **Clash.** Seats whose work the fake gate fails, at a `base` the fake gate
  also fails (it fails in any tree), end `clashed`, with `clash.txt` holding
  that gate's output. If the fake gate fails only when the seats' file is
  present, the replay ends `sent-back` and has no `clash.txt`. After either,
  `git worktree list` in the clone names no tree outside the clone (the
  loop's own `worktrees/pair` stays, since the loop never removes it).
  *As built:* the fake gate reports a step that could not run rather than a
  failure, so the loop pauses at once instead of handing the failure back to
  scripted seats until the round cap. The replay ends `clashed` when the base
  reports it too, and `paused` when only the seats' `a.txt` brings it on.
  `last_gate` and `clash` treat `failed` and `could-not-run` the same way, so
  the `sent-back` path runs the same code.
- **Report.** A kept `clashed` replay is absent from the mode columns, and the
  `clashed` count line names it.

### Risks

- **Joined output.** The joined output feeds `gate_record`, `gate_fails` and
  `gate_unrunnable`. The heading lines must not match `FAILED_STEP` or
  `COULD_NOT`, and a step that failed under the second target must still
  appear in the `gated` event's `failed` list. Assert both in the
  one-target-per-call test.
- **Several closing blocks.** `unwritable_pages` in `pair/loop.py` reads
  the last failed step as `.meta/gate`'s one closing block. With two failing
  targets the joined output has two, so the first closing block is read as
  a step, is not `rendered prose`, and the function returns `None`: a
  failure on pages the seats cannot write goes to the seats instead of
  pausing. That errs toward the seats and needs no change, but the
  one-target-per-call test should not depend on it.
- **The command the seats are told.** `gate_fails` names the command as
  `just gate <every target>`. A seat that reruns that line in an old era
  runs the clash itself. The replay cannot change that text without
  changing `Loop`, so the heading lines, which name each single-target
  command, are what a seat should rerun; the docstring names this as a
  clash the replay narrows but does not remove.
- **Restoring the file.** If the in-place rewrite were not restored, the seats
  would lose their notes and `restore_notes` would see a change. The
  `finally` and the "working file unchanged" assertion cover it.
- **Clash gate cost.** The clash gate provisions and gates a fresh tree once
  per unlanded replay, which costs minutes. It runs only when the last gate
  failed.
- **A seat's own failure.** If the base fails a target for its own reasons
  and the seats also break it, the replay counts as clashed and the seats'
  failure is hidden. The Issue's rule accepts this, and `clash.txt` keeps the
  evidence.

## Pair notes

> **primary, backlog turn 1**
>
> The Issue was already precise enough to plan, so I made one small change and kept `difficulty: medium`.
>
> It already says what is wanted, what is out of scope, and how anyone will know it is done, through tests in `pair/test_pair.py` and a `pair/README.md` change, without naming a gate. I checked the functions it cites against the code, and they all exist: `gate`, `make_loop` and `run_replay` in `pair/pair.py`; `keep_note`, `restore_notes` and `keep_gate` on `Loop`; `outcome_of` in `pair/replay.py`; and the outcome tally in `pair/report.py`.
>
> **The change:** the Issue said the replay's `gate` seam comes from `make_loop`. In the code, the loop gets it from `build_loop`, which `make_loop` calls inside `run_replay`. I reworded that sentence to match.
>
> **Why it isn't `developer` or `hard`:**
> - **Not `developer`:** where the notes go during a replay is the one open question, but the Issue already recommends an answer. It lets the seats choose otherwise if the code gives a reason, as long as they record the choice in the `pair/replay.py` docstring. Nothing waits on the developer.
> - **Not `hard`:** the work is three connected changes to the replay code: gate one target at a time, gate against a copy of the Issue file with the loop's notes and gate lines taken out, and report a `clashed` outcome. They fit in one piece, so I didn't split them into backlog files.

> **secondary, backlog turn 2**
>
> I made one small change to the Issue and kept `difficulty: medium`. Your partner's assessment holds up. I checked the code this time too: `gate` in `pair/pair.py` passes every target in one `just gate` call, `build_loop` hands that function to the loop, and the loop's `gated` event already records `targets` and an `outcome` of `passed`, `failed` or `could-not-run`.
>
> The change is to the "A clash shows in the outcome" bullet, which left three things open that a planner would have had to guess:
>
> - **Which events count:** it now names the event outcomes exactly, `failed` or `could-not-run`, instead of "failed or could not run".
> - **Which targets:** the check reuses the last `gated` event's `targets`, and runs the whole gate when that field is `null`.
> - **How it gates:** it uses the same one-target-at-a-time gate the replay uses everywhere else. It checks out the `Replay <slug>` commit in a separate tree, so the kept clone stays exactly as the seats left it.
>
> It's committed as `87ccf44a`.

> **primary, backlog turn 3**
>
> I'm leaving the Issue as it stands, and it stays `difficulty: medium`.
>
> Your change to the "A clash shows in the outcome" bullet holds up against the code. It now names the exact event outcomes, `failed` and `could-not-run`, which is what the loop's `gated` event records. It reuses that event's `targets`, and runs the whole gate when they are `null`. It gates the `Replay <slug>` commit in a separate tree, so the kept clone stays as the seats left it. Those were the gaps a planner would have had to guess at, and nothing else needs grooming.

> **primary, todo turn 1**
>
> I've written the plan under `## The plan` in `issues/todo/replay-in-the-era-it-replays.md`, ahead of the Pair notes. Nothing is implemented yet, and planning found nothing that stops the Issue being done as written.
>
> All the changes sit in `pair/replay.py`, `pair/board.py` and `pair/report.py`. The replay wraps the gate of the loop it builds, so `build_loop` and `Loop` don't change. The steps, in order:
>
> 1. **Strip the loop's additions.** A new `without_notes` in `pair/board.py` returns the Issue file without its `Pair notes` sections and without the supervisor's "Gated by the supervisor at …" lines.
> 2. **Gate one target at a time.** A new `era_gate` in `pair/replay.py` calls `just gate <target>` once per target and joins the outputs, each under a heading naming its target. With no targets it calls `just gate` once, as now. Around the calls it strips the Issue file and then writes the exact original back, even if the gate errors.
> 3. **Keep the clone's other recipes out of the way.** The replay wraps the loop's gate, and sets its `deliver` to nothing so a replay never runs the clone's `just deliver`. `just setup` and `just --summary` stay as they are. `.pair/` stays inside the clone, because once the gate runs one target at a time nothing in the clone's era runs the clone's old loop.
> 4. **Detect a clash.** When a replay doesn't land and its last `gated` event failed or could not run, the replay gates the `Replay <slug>` commit in a temporary separate worktree on that event's targets. If that gate also fails, the outcome is `clashed` and the output goes in `clash.txt`. The temporary worktree is removed afterwards.
> 5. **Report.** `pair/report.py` leaves `clashed` replays out of the mode columns and adds a count line per mode.
> 6. **Docs.** The `pair/replay.py` docstring gets a paragraph for each place a replay could clash with the clone, and `pair/README.md` says what `clashed` means.
>
> **Where I departed from the Issue:** it recommends gating against a copy of the worktree. I planned to strip the Issue file in place, gate, and restore it instead. A copy would lack the environment that `just setup` built in the loop's worktree, so every gate would either set up again or run without that environment. The supervisor only gates between turns, so no seat is writing the file at the time. The choice goes in the module docstring, as the Issue asks.
>
> **Tests.** There are tests for each of the Issue's done conditions. One limit: the test suite doesn't run `just` today. The tests that always run use a fake gate that records the targets of each call. The test with a real single-target `gate` recipe, which checks that the `pair` recipe never runs, is skipped wherever `just` isn't installed.
>
> **Risks the plan names:**
> - **Joined output:** the joined output must still be read correctly by the code that turns gate output into the `gated` event. In particular, a step that fails under the second target must still be counted.
> - **Restoring the file:** the stripped Issue file must always be put back exactly, or the seats lose their notes.
> - **Cost:** the clash gate sets up a fresh tree and gates it, which costs minutes per replay that doesn't land.
> - **Hidden failures:** when the start commit fails a target for its own reasons, any failure the seats added on that target is hidden behind `clashed`. The Issue's rule accepts this, and `clash.txt` keeps the output.

> **secondary, todo turn 2**
>
> I checked your plan against the code and made four fixes, all in the Issue file. The plan's structure holds: wrap `loop.gate` and `loop.deliver` inside `replay`, strip the Issue file in place and put it back, then the clash re-gate and the report change.
>
> 1. **Order of the joined output (step 2).** `gate_fails` in `pair/loop.py` hands the seats only the last `GATE_TAIL` characters of the gate's output. If the first target fails and a long passing target follows it, the seats would see only passing output. The plan now puts each failed call's output after every passed one, and the docstring will say why.
> 2. **A failed setup in the clash re-gate (step 4).** `provision` runs `just setup` with `check=True`, so a start commit that can't be set up would crash the replay before `outcome.json` is written. The plan now catches that error and counts it as `clashed`, with the error kept in `clash.txt`.
> 3. **Two new risks.**
>    - **Misread page failures:** `unwritable_pages` expects one closing block from `.meta/gate`. With two failing targets it returns `None`, so a failure on pages the seats can't write goes to the seats instead of pausing for the developer. That errs toward the seats, so no change is needed.
>    - **A command that clashes again:** the failure the seats are told names `just gate <every target>`. A seat that reruns that line from an old commit hits the same clash. The replay can't change that text without changing `Loop`. The heading lines name each single-target command for the seats to run instead, and the docstring will record this as a clash the replay narrows but doesn't remove.
> 4. **One clash-test assertion.** It said `git worktree list` would show only the clone. The loop never removes its own `worktrees/pair`, so the assertion now checks only that no tree outside the clone is listed.
>
> Planning found nothing that stops the Issue being done as written. All of this is committed.

> **primary, todo turn 3**
>
> I'm leaving the plan as it stands; your four fixes are sound.
>
> - **Failed output last:** the seats are only handed the last part of the gate's output, so putting each failed call's output after the passing ones keeps the failure in what they see.
> - **A failed `just setup` in the clash check:** catching it and counting it as `clashed` stops the replay from crashing before `outcome.json` is written.
> - **The two new risks:** both match the code. A failure on pages the seats can't write goes to them instead of pausing for the developer, which needs no change. The failure the seats are told still names `just gate` with every target, and only a change to `Loop` could fix that.
> - **The worktree assertion:** the loop never removes its own `worktrees/pair`, so the check can only require that no tree outside the clone is listed.

> **primary, in-progress turn 1**
>
> The change is in and committed as `cfb2cb20`, and both gates I was asked to run pass: `just gate meta` (96 steps) and `just gate pair` (334 tests plus ruff). I didn't run the whole gate.
>
> **What a replay does now** (`pair/replay.py`, unless named):
> - **Gate one target at a time:** a new `era_gate` calls `just gate <target>` once per target, so an older single-target `gate` recipe never runs a second target as a recipe. With no targets it calls `just gate` once, as before. Each output sits under an `=== just gate <target> ===` heading, and failed outputs come after passing ones, so the end of the output the seats are shown holds the failure.
> - **Notes out of the gate's view:** while the gate runs, `era_gate` takes the Pair notes and the supervisor's gate lines out of the Issue file, then writes the file back byte for byte, even if the gate raises. The removal is a new `without_notes` in `pair/board.py`. The prefix of a supervisor gate line is now one constant, `board.GATED`, which `gate_line` in `pair/loop.py` uses too.
> - **No delivery:** a replay never runs the clone's `just deliver`.
> - **Clash check:** when a replay doesn't land and its last gate failed or could not run, it gates the `Replay <slug>` commit in a temporary separate worktree on the same targets. If that fails too, the outcome is `clashed` and the output is kept in `clash.txt`. A failed `just setup` there also counts as a clash, and the temporary worktree is always removed.
> - **Report:** `pair/report.py` leaves `clashed` replays out of the columns and adds a `clashed: single N, pair M` line per slug and in total.
> - **Docs:** the `pair/replay.py` docstring and `pair/README.md` say where each clash comes from, how the replay avoids it, and what `clashed` means.
>
> **Tests** in `pair/test_pair.py`:
> - one call per target;
> - a real single-target `gate` recipe whose `pair` recipe must never run (skipped where `just` isn't installed);
> - the gate never sees a note that would fail it, and the landed Issue file keeps the note;
> - a clash, and its opposite case;
> - the file is restored after a gate that raises;
> - the heading order, and that a failed step under one target is still recorded;
> - the report's handling of `clashed`.
>
> I disabled the note stripping, and separately the one-target-at-a-time wrapper, and the matching test failed each time.
>
> **One departure from the plan, now written into it:** the opposite-of-clash test ends `paused`, not `sent-back`. Its fake gate reports a step that could not run, which makes the loop pause at once. A plain failure would hand the work back to the scripted seats until the round cap. The clash check treats both kinds of failed gate the same way, so the `sent-back` case runs the same code.

> **secondary, in-progress turn 2**
>
> I changed two small things in your implementation and left the rest as you built it. `just gate pair` (334 tests plus ruff) and `just gate meta` (96 steps) both pass. Both changes are committed.
>
> 1. **A test that could pass without checking anything.** The test with the real single-target `gate` recipe only checked that the `pair` recipe never ran. If the branch had touched only one Project, the test would pass without ever checking that two targets get two calls. It now also requires the last `gated` event in the clone to name both `meta` and `pair`. I ran it on its own outside the gate, with `just` installed, and it passes.
> 2. **Where the clash check finds the event log.** `replay` in `pair/replay.py` built the path `clone/.pair/events.jsonl` by hand. It now gets it from `event_log` in `pair/loop.py`, like the rest of the loop and `pair/report.py`, so a move of the loop's runtime directory can't silently break clash detection.
>
> Everything else holds up against the code:
> - **Gating:** the one-call-per-target gate, with failed output last and the Issue file put back exactly afterwards.
> - **No delivery:** the clone's `just deliver` never runs.
> - **Clash check:** the base is gated in a temporary worktree that is always removed, and a failed `just setup` there counts as `clashed`.
> - **Report:** `clashed` replays are left out of the columns and counted.
>
> Your change to the clash test is already written into the plan. It ends `paused` rather than `sent-back`, and `last_gate` and `clash` treat both kinds of failed gate alike, so it runs the same code. I found no work outside this Issue.

> **primary, in-progress turn 3**
>
> I'm changing nothing this turn; both of your changes hold up against the code.
>
> - **The real-`just` test:** it now requires the last `gated` event to name both `meta` and `pair`. Before, it could pass on a branch that touched only one Project, without ever checking that two targets get two calls.
> - **The event log path:** `replay` now gets it from `event_log` in `pair/loop.py`, the way the loop and `pair/report.py` already do. A move of the loop's runtime directory can no longer quietly break the clash check.
>
> I didn't run either gate this turn, since there's nothing new for them to check. You reported both passing after your changes.

Gated by the supervisor at 15:31: `meta`, `pair`; 98 steps passed.
