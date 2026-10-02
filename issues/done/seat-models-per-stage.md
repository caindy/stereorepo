---
difficulty: medium
waits_on:
  - seat-cache-write-per-session
---

# Let each stage name the model its seats run

Both seats run one model for the whole Issue (`--model` on `just pair`,
passed to `ClaudeSeat` through the seat factory in `pair/pair.py`). The
stages ask different things of them: an Issue's own grooming in `backlog`
reads the code, and `todo` and `in-progress` plan, write and check it. A
different model may suit each.

A seat's session is kept for the whole Issue so its prompt cache stays warm,
so changing model between stages starts fresh sessions. The measurement that
`seat-cache-write-per-session` (now in `done/`) made puts the price at about
10,500 cache-write tokens per fresh seat session against a warm cache. A fresh
session also loses its conversation, so the seat knows the Issue only from
the Issue file and the branch.

## Wanted

- One flag per stage an Issue passes through on `just pair`:
  `--backlog-model`, `--flight-check-model`, `--todo-model` and
  `--in-progress-model`. Each defaults to `--model`, which keeps its meaning.
  A value is a model id, an atomic identifier. They go on the `run` parser
  only, not on the `seats` parent that `groom` shares.
- When a seat's next turn is in a stage whose model differs from the model
  of its current session, the loop stops that seat and starts a fresh
  session on the new model. It drops the old session id from the state and
  from `<role>.session`. When the model is the same, the session carries on.
  The seat factory in `pair/pair.py` takes the model as an argument instead
  of closing over `--model`, and `State` records the model each role's
  session was started on, so that a loop restarted mid-stage resumes a saved
  session only when it was started on that stage's model, and otherwise
  starts fresh on it. A state file written before this change, which has no
  recorded model, counts as matching `--model`.
- `pair/README.md` says what a model change costs: at least the measured
  ~10,500 cache-write tokens per seat (more when the new model's cache is
  cold, since the prompt cache is per model), and the lost conversation.
- Primary and secondary still mean only which seat takes the first turn in a
  stage.

## Out of scope

- `just groom`, which already has its own `--model`.
- Different models for the two seats within one stage, and choosing a model
  automatically.

## Done when

- With no stage flag, every seat's `claude` command line is unchanged.
  Existing `SeatCommandTest` cases still hold.
- In `pair/test_pair.py`, a loop with a fake seat factory that records the
  model and resume id of each seat it builds shows these behaviours:
  - When `todo` and `in-progress` name different models, both seats start
    fresh (no resume id) on the `in-progress` model.
  - When a stage keeps the previous stage's model, both seats resume their
    sessions.
  - After the loop restarts in a stage with its own model, the seat is built
    on that model; it resumes its saved session when that session was
    started on the stage's model, and starts fresh when it was started on
    the previous stage's.
  - A `flight-check` stage with its own model builds its seats on it.
- `pair.py run --help` lists the four flags, and `pair.py groom --help` does
  not.

## The plan

The stage is known only to the loop, and the model is known only to the
factory that `pair/pair.py` builds. So the model moves into the `Loop`, and
the factory takes it as an argument.

1. **`pair/loop.py`**
   - `SeatFactory` becomes `Callable[[str, Path, str | None, str | None], Seat]`:
     role, cwd, resume, model.
   - `Loop.__init__` gains `model: str | None = None` (the `--model` value)
     and `stage_models: Mapping[str, str | None] = {}`. A new
     `model_for(stage)` returns `stage_models.get(stage) or self.model`. The
     grooming loop passes no stage models, so it always runs on `--model`.
   - `State` gains `models: dict[str, str | None]`, the model each role's
     session was started on. A role with no entry, which is every role in a
     state file written before this change, counts as `self.model`.
     `State(**json)` already fills a missing field with its default.
   - A new `Loop.align_model(st, role)` does the switch:
     - `want = self.model_for(st.stage)`, and
       `had = st.models.get(role, self.model)`.
     - If `had != want`, it stops and drops any live seat for the role
       (`seat = self.seats.pop(role, None)`, then `seat.stop()` if there
       was one), calls `forget_session(st, role)`, sets
       `st.models[role] = want`, and logs a `seat-model` event with `role`,
       `from` and `to`. Otherwise it does nothing, so calling it twice is
       harmless.
   - `work()` calls `align_model(st, role)` right after
     `role = st.next_role`, before it computes
     `restarted=interrupted and self.has_session(st, role)` and before the
     existing `self.save(st)` that follows `st.in_turn = role`. That save
     persists the recorded model with the dropped session, so no new save is
     needed. Called any later, `has_session` would still see the old
     session, and a seat interrupted mid-turn and then switched model would
     be sent `RESTARTED` in a fresh session that was never interrupted.
   - `Loop.seat(st, role)` also calls `align_model` first, so every path
     to a seat, including the restarts in `turn()`, gets the stage's model.
     Then it builds the seat as now, passing `self.model_for(st.stage)`.
   - `move()` does not change. The switch happens lazily, on the first turn
     of a seat in the new stage. That covers a restart mid-stage too, since
     `work()` clears `self.seats` when it exits and `seat()` rebuilds from
     `st.sessions` or `<role>.session`.
2. **`pair/pair.py`**
   - Move the parser construction out of `main()` into `arguments()`, so a
     test can read its help.
   - Add `--backlog-model`, `--flight-check-model`, `--todo-model` and
     `--in-progress-model` to `run`, `accept` and `resume` (see "Notes from
     the work"), not to `groom`. Each takes a `MODEL` metavar and has
     the help "model for both seats in this stage (default: --model)".
   - The factory becomes
     `lambda role, cwd, resume, model: ClaudeSeat(..., resume=resume, model=model)`.
     `Loop(...)` gets `model=` and `stage_models=` (keyed `"backlog"`,
     `FLIGHT_CHECK`, `"todo"`, `"in-progress"`). The `just pair` recipe
     comment in `justfile` names the new flags.
3. **`pair/README.md`**: a short paragraph next to the existing note on
   `CONTEXT` and the cache. It names the flags, says a change of model
   between stages starts both seats fresh, and gives the cost: at least
   ~10,500 cache-write tokens per seat (`seat-cache-write-per-session`),
   more when the new model's cache is cold, and the lost conversation.
4. **Tests** in `pair/test_pair.py`:
   - The bench's `factory` takes `model` too, and appends it to a new
     `b.models: list[tuple[str, str | None]]` (role, model). `b.opened`
     keeps its `(role, resume)` shape, so the seven assertions on it stand.
     A test sets `b.loop.model` and `b.loop.stage_models` before `run`,
     since both are plain attributes.
   - In a new `SeatModelTest`:
     - **Change between stages.** `in-progress` names model B and every
       other stage `--model` A. An easy issue lands. The first two seats are
       built on A with no resume. In `in-progress`, both are rebuilt on B
       with resume `None`.
     - **Same model.** `todo` and `in-progress` both name B, and `backlog`
       names A. Seats are rebuilt once, entering `todo`. Entering
       `in-progress`, no seat is rebuilt.
     - **Restart mid-stage.** Run with `stop_when_empty` until after the
       first `todo` turn, with no stage models. Then set `todo` to B and run
       again. The primary seat is built on B with resume `None`. A second run
       with the stage model unchanged resumes `primary-session`.
     - **Interrupted, then switched.** A state with `in_turn: primary`, a
       saved `primary.session` started on A, and `todo` now naming B:
       the primary seat is built on B with resume `None`, and the first
       message it is sent does not start with `RESTARTED`.
     - **Old state file.** A saved state with no `models` key, restarted
       under the same `--model`, resumes its session.
     - **Flight check.** In `FlightCheckTest`'s setup, a `flight-check`
       model builds the seats for that stage on it.
   - `SeatCommandTest` is unchanged. A test asserts that
     `arguments().parse_args(["run", "--todo-model", "x"])` gives
     `todo_model == "x"` for each of the four flags, and that
     `["groom", "--todo-model", "x"]` exits with a usage error
     (`SystemExit`). This reads the flags without parsing help text.

**Risks.**
- Ordering in `work()`: the switch must happen before `has_session` is
  read, as step 1 says; the interrupted-then-switched test pins it.
- `turn()`'s refusal path pops the seat and calls `seat()` again in the same
  stage. With `models` recorded, `had == want`, so this path behaves as today.
- `forget_session` also deletes `<role>.session`, which a live seat
  rewrites. The live seat is stopped first, so it cannot write the file
  back afterwards.
- The bench's `factory(kind)` closure signature changes, and nothing else
  calls it.

## Notes from the work

- **The flags are on `accept` and `resume` as well as `run`.** Both
  continue the Issue with `Loop.work` after a desk check, so the developer
  would otherwise have no way to keep a stage's model there. A loop run
  without the same stage flags counts every stage as running `--model`, and
  switches seats back to it with fresh sessions. `pair/README.md` says so.
  `groom` still rejects them, which the issue's out of scope asks for.
- **Where the switch happens.** `Loop.align_model` in `pair/loop.py` is
  called from `work()`, before `has_session`, and from `seat()`. It records
  the model in `State.models`, drops the old session from the state and
  from `<role>.session`, and logs a `seat-model` event. That event is now in
  the README's event table.
- **`seat()` records the model it builds each seat on** in `State.models`,
  not only on a switch. Recorded only on a switch, a loop restarted with
  another `--model` and no stage flags would count its old session as
  already on the new model and resume it. `SeatModelTest`'s
  `test_a_loop_restarted_with_another_model_starts_fresh_on_it` pins this.
- **`pair.py`'s parser** moved into `arguments()`, and `STAGE_MODELS` lists
  the four stages. The `just pair` recipe comment names `--STAGE-model`.
- **Tests.** The tests are `SeatModelTest`, two `LoopTest` cases (an
  interrupted seat switched to a new model is not sent `RESTARTED`, and a
  state file without `models` resumes) and a `FlightCheckTest` case. A test
  that runs the loop twice in one bench must clear `loop.stop_requested`
  between the runs, because `stop_when_empty` sets it and `run()` does not
  reset it.
- **The justfile is generated.** The `just pair` comment comes from
  `.meta/lib/render/writers.py`, which this change edits along with
  `justfile`. `just render` could not run from the seat's sandbox, which
  refuses writes under `.claude/skills/`. The new comment was checked
  against `render.rendered` directly, and the `rendered prose` check passes.
- **A line citation outside this issue.**
  `issues/done/land-leaves-a-half-landed-checkout.md` cited the callers of
  `land` by line number in `pair/loop.py`. Those lines moved with
  this change, and the `path and line claims` check failed. It now names
  them (`move_underway`, `merge`, `kick_back`), so later edits cannot break
  it.
