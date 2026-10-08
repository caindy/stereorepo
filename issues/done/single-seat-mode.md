---
difficulty: medium
parent: pair-versus-single-seat
---

# Run the pair loop with one seat

One part of `pair-versus-single-seat`. To compare one seat against two, the
loop needs a mode in which only the primary seat takes turns, with nothing
else changed.

Today every stage alternates `ROLES` (`primary`, `secondary`) in
`pair/loop.py`: `decide` hands the next turn to `other(role)`, and a stage
closes through `close_stage` only once `st.approvals` holds both roles.

## Wanted

- A flag on `just pair`, `--single-seat`, passed through to `pair.py run`.
  With it, every turn in every stage of an Issue's run, from its first
  (`backlog`) stage to landing, is taken by the primary seat, with the same
  prompts, models, stages, gates, round caps and desk checks.
- A stage closes when the primary seat leaves it as it stands (a quiet turn)
  and the stage's requirement (`requirement` in `pair/loop.py`) is met, as it
  closes today when both seats have. A turn that changes something never
  closes the stage, even though the primary seat is then the only role in
  `st.approvals`: `decide` must not read a non-quiet `[role]` as every seat
  having approved. An unmet requirement or a failed gate becomes the
  note for the primary seat's next turn, as now.
- The secondary seat is never started: the seat factory is never called for
  `secondary`.
- The round cap stays at `2 * cap` turns of a stage (`decide`), so the single
  seat gets as many turns as the pair does in total, not half.
- The mode is chosen when an Issue starts and kept in its `State` until the
  Issue lands or goes back to `backlog/`. A resumed or re-executed loop
  (`reexec`), a `just pair-resume` and a `just pair-accept` keep the stored
  mode whatever flag they are given; an Issue kicked back to `backlog/` and
  started again takes the mode of the run that starts it.
- Each row `turn` appends to `turns.jsonl` and each `started` event carries
  `"mode": "single"` or `"mode": "pair"`. Rows and events written before this
  change have no `mode` and are read as `pair`.
- Without the flag the loop behaves exactly as it does today.

## How anyone will know it is done

Tests in `pair/test_pair.py`, with the fake seats the suite already uses:

- With `--single-seat`, an Issue runs from `backlog/` to `main`, and every
  row in `turns.jsonl` has `"role": "primary"` and `"mode": "single"`, and
  no `secondary` seat was built.
- A primary turn that changes something does not close the stage, and the
  next turn is the primary seat's again.
- One quiet primary turn closes a stage whose requirement is met; a quiet
  turn on a stage whose requirement is unmet (for example a failed gate)
  does not close it, and the note reaches the primary seat's next turn.
- Without the flag, rows and the `started` event say `"mode": "pair"`, and
  the existing tests pass unchanged.
- A single seat that never goes quiet is kicked back after `2 * cap` turns
  of the stage, as the pair is.
- A loop stopped mid-Issue in single-seat mode and run again without the
  flag continues in single-seat mode, and a pair-mode Issue resumed with the
  flag continues as a pair.

## Out of scope

- Any change to the prompts, the loop's notes (such as "Both of you left this
  stage as it stands" in `close_stage`) or stage requirements for one seat.
- Showing the mode in `just pair-status`.
- The backlog grooming pass (`just groom`, the `GROOMING` state in
  `pair/loop.py`); it keeps two seats.
- Making single-seat the default; that is `pair-mode-decision`.

## The plan

The mode lives in two places: the `Loop` holds the mode the current run was
asked for, and the `State` holds the mode the Issue started in. Only a new
`State` reads the `Loop`'s; everything after that reads the `State`'s.

1. **`State` in `pair/loop.py`.** Add `mode: str = "pair"`. `load` builds
   `State(**json)`, so a `state.json` written before this change, with no
   `mode`, loads as `pair` without further code.
2. **`Loop.__init__`.** Add a keyword `mode: str = "pair"`, kept as
   `self.mode`. Pass `mode=self.mode` at the two places that make the `State`
   of a newly started Issue: the `State(slug=..., stage=...)` in `run` and the
   one in `adopt`. The grooming pass's `State` (slug `GROOMING`) keeps the
   default, and the `groom` loop is never given a mode. A kicked-back Issue's
   state is cleared, so a later start reads the new run's `self.mode`.
3. **A helper `roles(st)`** returning `("primary",)` when `st.mode ==
   "single"` and `ROLES` otherwise.
4. **`decide`.** Hand the next turn to `role` itself in single mode and to
   `other(role)` in pair mode. Close the stage only when
   `quiet and set(st.approvals) >= set(roles(st))`. The added `quiet` changes
   nothing for the pair: a non-quiet turn leaves `[role]`, which never holds
   both roles. The round cap (`2 * cap`) is untouched. `close_stage` needs no
   change: on an unmet requirement other than a failed gate it keeps
   `st.next_role`, which `decide` has already set to `primary`.
5. **`record` and `start`.** Add `"mode": st.mode` to the `turns.jsonl` row,
   and `mode=st.mode` to the `started` event. Nothing in the code reads
   either field yet (`status` reads rows, but not the mode), so "read as
   `pair`" is only a promise to future readers; the plan writes no reader.
6. **`pair/pair.py`.** Add `--single-seat` (`store_true`) to the `run`
   parser only, and pass `mode="single" if getattr(args, "single_seat",
   False) else "pair"` to `Loop`. `accept` and `resume` take no flag; they
   load the stored `State`. `reexec` re-runs the same argv, and the stored
   mode wins over it anyway. Mention the flag in the module docstring's usage
   line and in the `justfile` comment on the `pair` recipe.

The secondary seat is never built because `seat` builds a seat only for the
role whose turn it is, and in single mode that is always `primary`. The loops
over `ROLES` in `start` (removing session files) and in `move_underway`
(stopping stray seat processes) stay as they are: they clean up after seats,
and finding no secondary seat there is harmless.

### Tests

In `pair/test_pair.py`, set `b.loop.mode = "single"` on a `Bench`, as
existing tests set `b.loop.model`, and queue fake turns as usual:

- `test_single_seat_runs_an_issue_to_main_with_the_primary_alone`: every
  `turns.jsonl` row has `role` `primary` and `mode` `single`, the `started`
  event has `mode` `single`, and `b.opened` holds no `secondary`.
- `test_a_single_seat_turn_that_changes_something_does_not_close_the_stage`:
  after one changing turn the stage is the same and `next_role` is
  `primary`.
- `test_a_quiet_single_seat_turn_closes_a_stage_whose_requirement_is_met`,
  and a variant where the gate fails (`b.gates = [False]`): the stage stays,
  and the failure is in the message sent to the primary seat's next turn.
- `test_a_single_seat_that_never_goes_quiet_is_kicked_back_at_twice_the_cap`
  with `round_cap=1`: kicked back after two turns.
- `test_pair_mode_rows_and_started_event_say_pair`.
- `test_an_issue_keeps_the_mode_it_started_in`: start in single mode, stop
  mid-stage, run again with `mode = "pair"`, and the next turn is the
  primary's with `mode` `single`; and the reverse.
- Beside the existing `arguments()` tests (the per-stage model flags):
  `run --single-seat` parses, and `groom --single-seat` is refused.

### Risks

- **A stage closing on a changing turn** is the one way this could quietly
  break the comparison it exists for. The `quiet and` guard in `decide` and
  its test are what prevent it.
- **The prompts** tell each seat it has a partner. That is out of scope, but
  it will colour single-seat turns, and `pair-versus-single-seat` should know
  it.
- **The single seat sees no diff of its own work.** `message` shows each
  seat `git diff` from `st.seen[role]`, which `settle` and `keep_note` move
  to the seat's own last commit. In pair mode that diff is the partner's
  turn; in single mode it is empty unless the developer edited, so every
  turn after a changing one reads "Nothing has changed since your last
  turn" followed by "If you would change nothing, change nothing". That
  nudges the seat towards an early quiet turn, with no second look at its
  own change. The plan keeps it, since prompts are out of scope, but the
  full-run test should queue a changing turn followed by a quiet one and
  check that second message, so the behaviour is pinned and
  `pair-versus-single-seat` can weigh it.

## Implementation notes

The plan held as written. What landed, beyond its steps:

- `roles` in `pair/loop.py` is the one place that says which seats a mode
  has; the module docstring of `pair/loop.py` describes the mode, and
  `pair/README.md` documents `just pair --single-seat`, including that the
  grooming pass always runs two seats.
- The plan was wrong on one point: the `justfile` comment on the `pair`
  recipe is rendered from `CONDITIONAL_RECIPES` in
  `.meta/lib/render/writers.py`, so the flag is added there and rendered.
- The tests are `SingleSeatTest` in `pair/test_pair.py`. Each starts from an
  `easy` Issue in `backlog/`; `again` runs the loop until its scripted turns
  are spent and then stops it, which stands in for a developer's Ctrl-C and a
  later `just pair`. Beyond the plan, `test_a_state_file_without_a_mode_loads_as_a_pair`
  pins the default for a `state.json` written before this change, and
  `test_only_run_takes_the_flag` checks that `groom`, `accept` and `resume`
  refuse `--single-seat`.
- `test_single_seat_runs_an_issue_to_main_with_the_primary_alone` asserts
  that the turn after a changing one is told "Nothing has changed since your
  last turn.", pinning the risk above. A change to how a single seat sees its
  own work should change that assertion on purpose.
- The wiki entries for the two concepts the mode changes, `seat` and
  `quiet-turn` in `wiki/stereorepo/`, now say that a single-seat Issue has
  the primary seat alone and that its own quiet turn advances a stage.

## Pair notes

> **primary, backlog turn 1**
>
> I made two small edits to `issues/underway/single-seat-mode.md`. The rest was already precise enough to plan, and `difficulty: medium` still fits.
>
> I checked every code reference in the Issue against `pair/loop.py`, `pair/pair.py` and the `justfile`. They all match what the Issue says: `ROLES`, `other`, `decide` (which hands the next turn to the other seat and closes the stage once both seats have approved), `close_stage`, `requirement`, the `2 * cap` turn limit, `reexec`, `turns.jsonl` and the `started` event.
>
> - **Clarified scope:** "every stage, grooming included" was ambiguous. In the code, "grooming" means the backlog grooming pass that `just groom` runs, which is a different command from `just pair`. The Issue now says the `--single-seat` flag covers every stage of one Issue's run under `just pair`, from its first (`backlog`) stage to landing.
> - **Added to Out of scope:** the backlog grooming pass (`just groom`, the `GROOMING` state in `pair/loop.py`) keeps two seats.

> **secondary, backlog turn 2**
>
> I checked the Issue against `decide`, `close_stage` and `record` in `pair/loop.py`. My partner's version was mostly sound, and I kept `difficulty: medium`. I committed five changes to `issues/underway/single-seat-mode.md`:
>
> - **Round cap:** The old wording suggested the cap needed changing. It doesn't: `decide` already counts every turn of a stage, so the limit is `2 * cap` turns either way. The Issue now says the cap stays as it is.
> - **How long the mode lasts:** The Issue now says what happens to the mode in each case:
>   - A stopped or re-executed loop, `just pair-resume` and `just pair-accept` all keep the Issue's stored mode, whatever flag they get.
>   - An Issue that goes back to `backlog/` and starts again takes the mode of the new run.
>   - The reverse case is covered too: a pair-mode Issue resumed with `--single-seat` continues as a pair.
> - **Secondary seat:** It must never be started. The full-run test now checks that no secondary seat was built.
> - **Two new tests:**
>   - A single seat that never goes quiet is sent back to `backlog/` after `2 * cap` turns, as the pair would be.
>   - A pair-mode Issue resumed with the flag continues as a pair.
> - **Out of scope:**
>   - The loop's own notes keep their two-seat wording, such as "Both of you left this stage as it stands" in `close_stage`.
>   - `just pair-status` won't show the mode.

> **primary, backlog turn 3**
>
> I'm leaving the Issue as it stands. I checked my partner's changes against `pair/loop.py` and they're right:
>
> - **Round cap:** `decide` counts every turn of a stage in `st.turn` and stops the stage at `2 * cap`, so the cap needs no change to give one seat as many turns as the pair gets in total.
> - **How long the mode lasts:** keeping the mode in the Issue's `State`, with explicit rules for resume, accept and kick-back, settles what my wording left open.
> - **The rest:** the check that no secondary seat is built, the two new tests and the new out-of-scope items are all sound.
>
> `difficulty: medium` still fits.

> **primary, todo turn 1**
>
> I added `## The plan` to `issues/todo/single-seat-mode.md`. The Issue can be done as written, so there's no `# Needs elaboration`.
>
> **Where the mode lives:**
> - The `Loop` gets a `mode` keyword holding what the current run asked for.
> - The Issue's `State` (saved in `.pair/state.json`) gets a `mode` field that defaults to `"pair"`, so state files written before this change still load as pair.
> - Only a new `State` copies the `Loop`'s mode. That happens at the two places that start an Issue: in `run` and in `adopt`. From then on everything reads the `State`'s mode. So a resumed loop, a re-executed loop, `pair-resume` and `pair-accept` all keep the mode the Issue started in. A kicked-back Issue's state is cleared, so its next start takes the new run's mode.
>
> **What changes in `decide`:**
> - A small helper, `roles(st)`, gives `("primary",)` in single mode and both roles otherwise.
> - In single mode the next turn goes back to the primary seat instead of to the other seat.
> - A stage closes only when the turn was quiet and every role in `roles(st)` has approved. The added "quiet" check changes nothing for the pair, because a turn that changes something always leaves only one role approved.
> - The round cap and `close_stage` need no change.
>
> **Other changes:**
> - The `turns.jsonl` row and the `started` event each gain a `mode` field.
> - `--single-seat` goes on the `run` command in `pair/pair.py` only. `groom` doesn't get the flag.
>
> The secondary seat is never built: `seat` in `pair/loop.py` builds a seat only for the role whose turn it is, and in single mode that's always the primary.
>
> **Tests:** the plan names one test in `pair/test_pair.py` for each behaviour in the Issue. They set `b.loop.mode = "single"`, the same way existing tests set `b.loop.model`. One addition goes beside the existing argument tests: `run` accepts `--single-seat` and `groom` refuses it.
>
> **Risks:**
> - The main one is a stage closing on a turn that changed something. The "quiet" check and its test guard against that.
> - The seats' prompts still tell each seat it has a partner. Changing them is out of scope, but it will affect single-seat turns, and `pair-versus-single-seat` should know that.

> **secondary, todo turn 2**
>
> I checked my partner's plan against the code, and its design holds. I added one risk and a check that pins it, and committed that to `issues/todo/single-seat-mode.md`. The Issue can be done as written, so it needs no `# Needs elaboration` section.
>
> **What I confirmed in the code:**
> - **Old state files:** `load` rebuilds the state with `State(**json)`, so adding a `mode` field that defaults to `"pair"` is enough for older files to load as pair.
> - **Where an Issue starts:** a new Issue's `State` is created in only two places, `run` and `adopt`, which matches the plan.
> - **Who takes the next turn:** apart from `decide`, every place that sets `next_role` (`close_stage`, `advance` and the merge failure path) sets it to `primary`. That works for one seat without change.
> - **Building the `Loop`:** `pair.py` builds it once, in `main`, for every command. Reading the flag with `getattr(args, "single_seat", False)` therefore works even for `accept` and `resume`, which don't define the flag.
> - **Test helpers:** `Bench.opened` and the existing `arguments()` tests are there for the plan's tests to use.
>
> **The risk I added:** a single seat never sees a diff of its own work. Each turn's message shows the seat what changed since its last turn, measured from `st.seen[role]`, and the loop moves that marker to the seat's own last commit. In pair mode that diff is the partner's turn. In single mode it is empty unless the developer edited something. So every turn after a changing one reads "Nothing has changed since your last turn", followed by "If you would change nothing, change nothing". That pushes the seat to go quiet at once, without a second look at its own change.
>
> The plan leaves this as it is, because prompts are out of scope. But the full-run test now also has to queue a changing turn followed by a quiet one and check the second turn's message. That fixes the behaviour in a test, and `pair-versus-single-seat` can take it into account when comparing the modes.

> **primary, todo turn 3**
>
> I'm leaving the plan as it stands. I checked the risk my partner added against `pair/loop.py`, and it's accurate:
>
> - After each turn, `settle` and `keep_note` record the seat's own last commit as the point it has already seen (`st.seen[role]`).
> - `message` then shows the seat only what changed after that point.
> - With one seat, there's nothing new after its own commit unless the developer edited something. So the next turn's message says "Nothing has changed since your last turn."
>
> The plan is right to keep that behaviour, since prompts are out of scope, and to pin it with a test so `pair-versus-single-seat` can account for it. The rest of the plan is unchanged and still matches the code.

> **primary, in-progress turn 1**
>
> `just pair --single-seat` now works: the primary seat alone takes every turn, and an Issue keeps the mode it started in. `just gate pair` passes (302 tests and ruff) and `just gate meta` passes. Everything is committed as `3f4195f2`.
>
> **How it was built:**
> - **`pair/loop.py`:**
>   - The Issue's saved `State` has a `mode` field, `"pair"` by default, so state files from before this change load as pair. The `Loop` takes a `mode` too, and only an Issue it starts (in `run` or `adopt`) copies it.
>   - A new `roles` function says which seats a mode has.
>   - In `decide`, single mode gives the next turn back to the primary seat. A stage now closes only on a quiet turn, which stops a turn that changed something from closing it when the primary is the only seat that has approved. Pair mode behaves as before.
>   - Each `turns.jsonl` row and each `started` event now carries `mode`.
> - **`pair/pair.py`:** `--single-seat` exists on `run` only; `groom`, `accept` and `resume` refuse it.
> - **Docs:** the flag is described in `pair/README.md`, the docstrings of `pair/loop.py` and `pair/pair.py`, and the `justfile` comment.
>
> **Where the plan was wrong:** the `justfile` is generated. I added the flag to its source, `CONDITIONAL_RECIPES` in `.meta/lib/render/writers.py`, and re-rendered, and I recorded this in the Issue's new `## Implementation notes` section.
>
> **Tests:** `SingleSeatTest` in `pair/test_pair.py` has ten tests, one for each behaviour the Issue lists. They include a stage that a changing turn doesn't close, a failed gate whose message reaches the primary seat's next turn, and the kick-back after `2 * cap` turns. They also cover the mode surviving a restart under the opposite flag, both ways, and a state file with no `mode` loading as pair. The full-run test also checks the risk my partner added: the turn after a changing one is told "Nothing has changed since your last turn."
>
> Nothing here needs Docker or anything else the sandbox can't run, and I found no work outside this Issue.

> **secondary, in-progress turn 2**
>
> I reviewed my partner's implementation and the code holds up. The only change I made fills a documentation gap. `just gate pair` passes (302 tests and ruff), and `just gate meta` passes.
>
> **What I checked in the code:**
> - **Pair mode is unchanged.** `decide` now closes a stage only after a quiet turn, but in pair mode a turn that changes something already left only one seat approved, so nothing closed on it before either.
> - **The mode is chosen in two places only:** `run` and `adopt`, when an Issue starts. After that, everything reads the mode stored with the Issue.
> - **The tests in `SingleSeatTest` (in `pair/test_pair.py`) cover every behaviour the Issue lists.**
>   - A full run with the primary seat alone, which also pins the "Nothing has changed since your last turn" risk.
>   - A failed gate whose message reaches the primary seat's next turn.
>   - The kick-back after `2 * cap` turns.
>   - An Issue keeping its mode when restarted with the opposite flag, both ways.
>   - A state file with no `mode` loading as pair.
>   - Only the `run` command accepting the flag.
>
> **What I added:** the AGENTS.md rules say every concept in the shared vocabulary has a wiki entry. Two of those entries no longer described the loop fully, so I updated them:
> - **`wiki/stereorepo/seat.md`** now says that in single-seat mode the primary seat takes every turn and the secondary is never started.
> - **`wiki/stereorepo/quiet-turn.md`** now says that in that mode the seat's own quiet turn advances a stage, and that a turn that changes something never does.
>
> I recorded both under `## Implementation notes` in the Issue file. Nothing needed Docker or anything else the sandbox couldn't run, and I found no work outside this Issue.

> **primary, in-progress turn 3**
>
> I'm leaving the implementation as it stands. My partner's only change was to two wiki pages in `wiki/stereorepo/`, and both match the code:
>
> - **`seat.md`** now says that in single-seat mode the primary seat takes every turn and the secondary is never started. That holds because a seat is only ever built for the role whose turn it is.
> - **`quiet-turn.md`** now says the single seat's own quiet turn advances a stage, but a turn that changes something never does. That is the quiet-turn check now in `decide` in `pair/loop.py`.
>
> My partner reported that `just gate pair` and `just gate meta` both pass with these edits. I made no changes this turn, so I didn't re-run them.

Gated by the supervisor at 07:55: `meta`, `pair`, `specialization`; 99 steps passed.
