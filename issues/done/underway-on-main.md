---
parent: grooming-alongside-the-loop
difficulty: medium
---

# Move the Issue being worked to `underway/` on `main`

While the loop works an Issue, its file on `main` stays in `backlog/`, and its
real stage exists only on its branch. So the board on `main` does not show what
is being worked, and anything that edits the backlog on `main` can edit the
Issue underway.

## What is wanted

- A new stage directory, `issues/underway/`, on `main`. When the loop starts
  an Issue or a Flight check, it moves the file from `backlog/` to
  `underway/` on `main`, in a commit of its own that it fast-forwards into the
  developer's checkout the way `kick_back` does, before the seats' first turn.
  If that fast-forward is refused, the loop pauses before starting, and the
  Issue stays in `backlog/`.
- The branch `pair/<slug>` starts from that commit, so on the branch the
  backlog stage and the Flight check hold the file in `underway/`: `home()` in
  `pair/loop.py` answers `underway` for both. The later stages on the branch
  (`todo/`, `in-progress/`, `desk-check/`) are unchanged.
- Landing moves the file out of `underway/` in the squashed commit, as it does
  now from `backlog/`: to `done/`, or to `desk-check/` for a Flight that passes
  its check. An Issue that leaves `underway/` without being retired goes back
  to `backlog/` in the same commit: a `hard` Issue that has just been split,
  and a Flight whose check wrote a gap as a new child. A send-back
  (`kick_back`) moves it from `underway/` to `backlog/`.
- `board.STAGES` gains `underway`. `next_ripe`, `to_groom` and `unnamed` do not
  take it up, since it is not in `backlog/`. `grooming_faults` accepts a line
  in `ORDER` that names the Issue underway, or the Flight it is a part of, and
  does not ask a pass to rank it. A part underway has no line of its own
  (`rank-flights-not-parts`), and its Flight's line stays where it is.
- Whatever looks for the Issue being worked in `backlog/` on `main` looks in
  `underway/` instead. In particular `flight_refusal` in `pair/loop.py`
  accepts a Flight whose check is underway, so `just pair --flight <slug>`
  resumes that check rather than answering that it is not a Flight in
  `issues/backlog/`.
- The `board order` check in `.meta/checks/files/board.py` accepts an `ORDER`
  line naming an Issue in `underway/`: `ORDERABLE` gains `underway`, and its
  probe in `.meta/checks/probes/files/board.py` places its underway slug in
  `underway/`. Otherwise `just gate meta` fails on `main` for as long as an
  Issue is underway.
- A restarted supervisor finds the Issue underway where it left it, and does
  not move it a second time.
- The words follow: the stage tables in `issues/README.md`,
  `template/issues/README.md` and `pair/README.md`, a README in
  `issues/underway/`, the Stage concept in
  `.meta/assertions/imported/vocabulary.yaml` and its wiki entry, and
  `just pair-status`, which counts `underway/` like the other stages.

## Out of scope

- Running `just groom` alongside `just pair` (`groom-alongside-pair`). This
  Issue only makes it safe.
- Moving an Issue that was started before this lands. The loop running when it
  lands finishes that Issue with the old code.

## Done when

- Starting an Issue commits its move to `underway/` on `main` before the first
  turn, and a refused fast-forward pauses without starting it.
- Landing an Issue leaves it in `done/`, a Flight that passes its check in
  `desk-check/`, and a split `hard` Issue, a Flight with a new gap and a sent-back
  Issue in `backlog/`, with nothing left in `underway/` in each case.
- Restarting the supervisor mid-Issue neither moves the file again nor loses
  it, and `just pair --flight <slug>` resumes a Flight check underway.
- A grooming pass whose `ORDER` still names the Issue underway, or its Flight,
  has no fault for it, and `just gate meta` passes on a `main` whose `ORDER`
  names an Issue in `underway/`.
- The pair tests cover each of these, and `just gate` passes.

## The plan

The stage names in `State.stage` stay as they are (`backlog`, `flight-check`,
`todo`, ...). What changes is the directory that holds the file for the first two
stages (`home()`), and the commits on `main` that go into and out of that
directory.

### Steps, in order

1. **`pair/board.py`.** Add `"underway"` to `STAGES`, after `"backlog"`. Then
   `families`, `children`, `waiting` and `descendants` see a child in
   `underway/`, so a Flight whose part is underway is not ripe. `listed`,
   `next_ripe`, `running_order`, `to_groom`, `unnamed`, `backlog_parents` and
   `parts` read only `backlog`, and stay as they are. In `grooming_faults`,
   read the slugs in `tree/issues/underway/` and allow them in `ORDER` on
   either side of the marker: they are neither `missing` nor `extra`. A
   Flight's line needs no change, because the Flight is still in `backlog/`
   and is not a part.
2. **`home()` in `pair/loop.py`** returns `"underway"` for `"backlog"` and
   `FLIGHT_CHECK`. `settle`, `move`, `message` and `deliver_flight` pick this
   up through `home()`. In `flight_checked`, `was` reads the Flight from
   `home(st.stage)` at `st.base`, not from `"backlog"`.
3. **`start()`.** For an Issue (not a grooming pass), after the clean-worktree
   check, check out `main` detached in the worktree. If the file is still in
   `backlog/`, create `issues/underway/` if it is missing (a test repository
   has no README there) and `git mv` it to `underway/` and commit the move (`Start <slug>`,
   `Seat: loop`). Land that commit with `land()`. `land()` takes a
   `retry` keyword (default `"merge"`), so `start` can pass `None`. If the
   landing is refused, reset the worktree to `main` with `--force` and
   `clear()` the state, so the Issue is still in `backlog/` and a rerun picks
   it up again. Then `checkout -B pair/<slug> main` as now, so `st.base` is
   the move commit. If the file is already in `underway/` on `main`, skip the
   move.
4. **Adopting an Issue left underway.** In `run`, right after `load()` and
   before `flight_refusal`, when there is no state and
   `listed(main, "underway")` is not empty, build an unstarted
   `State` for that slug: `FLIGHT_CHECK` if it has children, otherwise
   `"backlog"`. `flight_refusal` then sees it as it sees a stored `st`, so
   with `--flight` an adopted slug outside the Flight is refused. The loop
   passes an unstarted `State` (`st.base == ""`) to `start` before `work`,
   and `start` skips the move because the file is already in `underway/`.
   This covers a supervisor that dies after landing the move but before
   `save`. A supervisor that dies earlier leaves only an unlanded commit in
   the worktree, which the next `start` throws away.
5. **`flight_refusal`** accepts `flight` if it is in `backlog/` or
   `underway/` on `main` and has children.
6. **Landing.** For a waiting Flight, `retirement` returns `"backlog"` only
   while the file is in `underway/` (`board.locations(self.wt, st.slug) ==
   ["underway"]`): a `hard` Issue just split, or a Flight check that wrote a
   gap. Once `move` has put it in `backlog/`, `st.stage` is `"backlog"` but the
   file is no longer at `home("backlog")`, so the check answers `None`, and
   the three-pass loop in `merge` and a `retry: merge` do not move the file
   twice. A waiting Issue in any other stage (`todo/`, `in-progress/`,
   `desk-check/`) still answers `None`, as today. `move` then does the
   `underway → backlog` rename in the squashed commit. Its commit subject
   (`x: backlog -> backlog`) is squashed away, so it needs no special case. `squash` keeps the
   `ORDER` line, because `retired` is only `done`/`desk-check`. `kick_back`
   already removes the slug from every stage on `main`, so it covers
   `underway/` once `STAGES` includes it.
7. **`status()`** lists `underway` between `backlog` and `done`.
8. **`.meta/checks/files/board.py`**: add `underway` to `ORDERABLE` and fix
   its docstring. In `.meta/checks/probes/files/board.py`, set
   `ORDER_STAGES["underway"]` to `"underway"`, so the probe checks the new
   stage. A standalone Issue's line keeps passing. A part in `underway/`
   whose Flight is in the backlog is still reported as a part.
9. **Words.** Add a row for `underway/` to the stage tables in
   `issues/README.md` and `template/issues/README.md`. In `pair/README.md`,
   the `backlog/` and Flight check rows say the file sits in `underway/` on
   `main` and on the branch; the Flight and hard-split prose says the file
   goes back to `backlog/` when it lands. Add `issues/underway/README.md`
   (`template/issues/` holds only a README, so it gets no stage copy). Update
   the `Stage` definition in `.meta/assertions/imported/vocabulary.yaml`,
   then re-render. There is no Stage page in `wiki/` today, so write
   `wiki/stereorepo/stage.md` with `/wikisplain`. Update the module
   docstring of `pair/loop.py` (it says "whose file stays in `backlog/`"),
   the `FLIGHT_CHECK` docstring, `stage-flight-check.md` ("leave the Flight
   file where it is" still holds), and the `run` and `kick_back` docstrings.
   Grep for `stays in \`backlog/\`` and `in backlog/` to find the others.

### Tests (`pair/test_pair.py`)

- Update the existing assertions that read the file from `backlog/` on the
  branch during the backlog stage or the Flight check (for example
  `test_a_seat_that_moves_the_flight_file_is_put_back_in_backlog`).
- New, in `LoopTest`:
  - After the first turn, `main` has a `Start x` commit with
    `issues/underway/x.md` and no `backlog/x.md`, and `pair/x` descends from
    it.
  - Landing leaves `done/x.md` and an empty `underway/`.
  - A refused fast-forward at start (a developer file in the way, as in
    `test_a_refused_fast_forward_pauses_until_the_human_clears_the_way`)
    pauses, leaves `backlog/x.md` on `main` and no state, and a rerun starts
    it.
  - A split `hard` Issue lands in `backlog/`.
  - A send-back lands in `backlog/` and not in `underway/`.
  - A restart with the state file intact does not add a second `Start`
    commit.
  - With the state file deleted after the start, the run adopts the Issue
    from `underway/` and lands it.
- In `FlightCheckTest`: a brief lands the Flight in `desk-check/`, and a gap
  lands it in `backlog/`, with `underway/` empty after both.
- In `FlightRunTest`: `run(flight=…)` resumes a Flight check that is
  underway.
- In `BoardTest`: `grooming_faults` gives no fault for an `ORDER` line naming
  an Issue in `underway/`, and does not ask for one to be ranked. A Flight
  whose child is in `underway/` is not ripe.
- `just gate meta` (with the probe) and then `just gate`.

### Risks

- **Every existing test that starts an Issue now lands a commit on `main`
  first.** Tests that count commits on `main`, or that compare `main` with
  the branch base, will move. Update those tests; do not add special cases
  to the code.
- **A gate failure in `merge` after `move` has retired the file.** Today
  this happens only with `st.stage == "done"`, and it pauses. After a move
  back to `backlog`, the pair would carry on with the file in `backlog/`,
  while `home("backlog")` says `underway`. `settle` would put it back and
  the next landing would move it again, so this is self-healing, but `settle`
  would blame a seat for the move. So on a failing gate, `merge` pauses with
  `retry: merge` when `st.stage == "done"`, as now, or when the file is no
  longer at `home(st.stage)`, which is the case after a retirement to
  `backlog/`. A test covers it: a split `hard`
  Issue that touches code, `main` moving during the landing, and a failing
  gate on the second pass pause without a seat turn.
- **The loop that runs when this lands** has old code, and must finish its
  Issue with that code (see Out of scope). The first Issue after this lands
  starts with the new code.

## Notes on the implementation

- `grooming_faults` accepts an `ORDER` line only for a standalone Issue in
  `underway/`. A part in `underway/` whose Flight is in `backlog/` still gets
  a fault, which matches the `board order` gate step. Otherwise a pass could
  write a line that `just gate meta` then refuses.
- On a failing gate, `merge` pauses when `st.stage == "done"` or when the
  file is not at `home(st.stage)` in `HEAD`. The second case is a retirement
  back to `backlog/`. A grooming pass has no file and is exempt from the
  second test. Its gate never runs today, because a pass changes only
  `issues/`, but without the exemption a pass that changed code would pause
  instead of going back to its seats.
  `test_a_failing_gate_after_a_split_goes_back_pauses_the_landing` covers it
  by wrapping `squash` so that `main` moves once.
- `just pair-status` now shows an Issue in its backlog stage as
  `x in underway/, its backlog stage`. It used to say `x in backlog/`, which
  is no longer where the file is.
- The `board order` probe keeps its old in-progress slug as `branched`. It
  still covers a line kept on the Issue's own branch. A new `underway` slug
  sits in `underway/`.
- `adopt()` takes the first slug in `underway/` on `main`. The loop never
  puts more than one Issue there. If there is more than one, only the
  first is taken up.
- `just groom` does not yet respect an Issue in `underway/` that has no
  state. That is `groom-alongside-pair`'s job.
- A Stage wiki page did not exist, so this change adds
  `wiki/stereorepo/stage.md`. `wiki/stereorepo/flight.md` now says the Flight
  check moves the Flight to `underway/`.
