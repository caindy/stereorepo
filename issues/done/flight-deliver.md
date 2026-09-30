---
difficulty: medium
parent: flights
waits_on:
  - flight-desk-check
---

# Run `just deliver`, where defined, before a Flight's desk check

One part of `flights`. Delivery is the repository's business, as provisioning
a worktree is (`just setup`, `pair.provision`): the loop never knows how a
product deploys, only whether the recipe exists and whether it passed.

## Wanted

- When a Flight passes its check, meaning `merge` finds that `retirement(st)` is
  `"desk-check"` for stage `FLIGHT_CHECK`, the loop runs `just deliver` in the
  pair worktree before `move` and `squash`. At that point the worktree is `main`
  with only the Flight file's edits on top, so the loop delivers what `main`
  holds (for example, a redeployment to a UAT environment). A Flight check that
  wrote a gap child stays in `backlog/`, and the loop does not deliver it.
- The recipe counts as defined when `just --summary` in the worktree lists
  `deliver`, as `provision` decides for `setup`. With no `deliver` recipe the
  step is skipped silently, and the Flight file is unchanged.
- When the recipe passes, the loop appends one plain line (not a heading, so
  it stays inside the brief's section), such as ``Delivered by `just deliver`
  from main at <short sha>.``, to the end of the Flight file, which ends in
  the brief the check just wrote. The loop stages the edit before `move`:
  `move` commits only the index and `squash` commits it after a soft reset,
  so an unstaged line would be left out of the landing and would block the
  rebase if `merge` goes round again. The line lands in the squash commit, so
  the developer sees at the desk check that the Flight was delivered.
- When the recipe fails, the Flight does not move to `desk-check/` and nothing
  lands. The loop pauses with `retry: merge` and the tail of the recipe's
  output, as it does for a gate failure (`GATE_TAIL`). Rerunning the loop
  retries the merge, which runs `deliver` again.
- Delivery runs once per desk-check round. A second pass through `merge` (after
  `main` moves, or after a `retry: merge` for a refused fast-forward) finds the
  Flight already in `desk-check/` and does not deliver it again.
- `deliver` is injected into `Loop` as `gate` is, so tests can fake it.
- `pair/README.md` says what `deliver` is for, next to `setup`.

## Out of scope

- Defining a `deliver` recipe in this repository or in `template/`.
- Delivering anything other than a Flight, such as a `developer` Issue at its
  desk check.
- Any release gate after `pair-accept`.

## Done when

The pair tests show four cases:

- With no recipe, the Flight lands in `desk-check/` with its file unchanged.
- With a passing recipe, the Flight lands with the delivery line in its file.
- With a failing recipe, the loop pauses with `retry: merge` and the output
  tail, and `main` and the Flight's place are unchanged.
- A landing that pauses on a refused fast-forward after a passing delivery
  does not deliver again when it is retried.

`pair/README.md` names `deliver`, and `just gate` passes.

## The plan

All in `pair/`: `loop.py`, `pair.py`, `test_pair.py`, `README.md`.

1. **The seam.** In `loop.py`, beside `Gate`, add
   `Deliver = Callable[[Path], "tuple[bool, str] | None"]`: `None` when the
   repository defines no `deliver` recipe, otherwise whether it passed and its
   output. `Loop.__init__` takes a keyword `deliver: Deliver | None = None`,
   as it takes `provision`; `None` means never deliver, so existing callers and
   tests are unchanged.
2. **`pair.py`.** Factor `recipes(tree) -> list[str]` (the `just --summary`
   call) out of `provision`, and add `deliver(tree)`, which returns `None`
   unless `"deliver"` is in `recipes(tree)`, else prints
   `delivering from worktrees/pair (just deliver) ...` as `provision` prints
   its line, and runs `just deliver` in `tree` as `gate` runs `just gate`. The
   output is captured, so that line is all the terminal shows while a slow
   deploy runs; with no recipe nothing is printed, keeping the skip silent. Pass `deliver=deliver` to `Loop` in `main`.
3. **`merge`.** After `to = self.retirement(st)`, and before `self.move`, when
   `to == "desk-check"` and `st.stage == FLIGHT_CHECK`, call a new
   `self.deliver_flight(st) -> bool`. If it returns False, return `"paused"`.
   The condition is what makes delivery once per round: `move` sets
   `st.stage = "desk-check"` and saves it, so a second pass through `merge` (the
   `continue` when `main` moved, or a `retry: merge` rerun) gets
   `retirement(st) is None` and skips it. A failed delivery pauses before
   `move`, so the stage is still `FLIGHT_CHECK` and the rerun delivers again.
4. **`deliver_flight`.** With no `self.deliver`, or when it returns `None`,
   return True. On a pass, append
   ``Delivered by `just deliver` from main at <short sha>.`` (the sha of
   `self.main`, which the branch was just rebased onto) as its own paragraph at
   the end of the Flight file in the worktree, `git add` it, and return True;
   `move`'s commit carries it and `squash` keeps it. On a failure, pause with
   `retry="merge"` and a reason that names `just deliver` and ends in the output
   tail, `out[-DELIVER_TAIL:]` in a fenced block, with a new
   `DELIVER_TAIL = 2_000` beside `GATE_TAIL`: the reason also goes to
   `notify` and to `pair-status`, so the gate's 6,000 characters is too much.
   Return False.
5. **Tests** in `FlightCheckTest`, with `Bench` gaining a fake `deliver` that
   returns `self.delivers.pop(0)` (a `(bool, str)`) while that list has entries,
   else `None`, and counts calls in `self.deliver_runs`:
   - no recipe: the existing `test_a_brief_lands_...` already covers it; add
     assertions that `deliver_runs` is 1 and the Flight file on `main` has no
     `Delivered by` line.
   - passing: the Flight lands in `desk-check/` and its file on `main` ends in
     the `Delivered by` line.
   - failing: `run(once=True)` is `"paused"` with `retry == "merge"`, the
     reason holds the fake output, `main` is unchanged, the Flight is still in
     `backlog/` on `main` with its slug in `ORDER`. A second run with a passing
     delivery lands it in `desk-check/`.
   - once per round: extend the pattern of
     `test_a_flight_paused_while_landing_still_lands_at_its_desk_check` with a
     passing delivery; after the rerun lands, `deliver_runs` is 1 and the file
     holds one `Delivered by` line.
6. **`pair/README.md`.** In the Flight check paragraph, say that before a
   Flight goes to `desk-check/` the loop runs `just deliver` in the worktree
   where the `justfile` defines it, records it in the brief, and pauses if it
   fails; and that `just setup`, where defined, provisions a fresh worktree.
   The README does not mention `setup` today, so this adds both in one place.

**Risks.**
- The Flight check could touch code outside `issues/` only if the supervisor
  let it, and `flight_checked` refuses that, so `deliver` sees `main`'s code.
- A real `just deliver` may be slow or need credentials; the loop runs it
  synchronously with no timeout, as it does `just gate`. That is the
  repository's business, and the `delivering` line from step 2 makes a hang
  visible in the terminal even though the output is captured.
- A passing delivery followed by a landing that never happens (the developer
  abandons it) leaves an environment deployed from `main` with no desk check.
  That is harmless, since it is `main`'s code.

## What the next reader should know

- **The plan held.** `pair.recipes` is now shared by `provision` and
  `deliver`. `Loop.deliver_flight` sits between `retirement` and `move` in
  `merge`.
- **The delivery line is staged, not committed.** `deliver_flight` stages
  its line and `move` commits it along with the rename. So a Flight file that
  lands with the line always lands in `desk-check/`. Nothing else commits the
  line.
- **The sha is `main`'s before the landing.** The line names the commit the
  worktree was rebased onto, which is what `just deliver` saw. After the
  landing, that commit is `main~1`, which is what the passing test checks.
- **The test bench delivers by default with no recipe.** `Bench`'s fake
  `deliver` returns `None` unless a test queues results in `delivers`, and it
  counts every call in `deliver_runs`, including calls that returned `None`.
  So every existing Flight test also covers the no-recipe case. The gap test
  asserts `deliver_runs == 0`, since a Flight check that writes a gap child
  must not deliver.
- **The Flight's path comes from the stage, not `board.read`.** It is built
  the way `move` builds it (`home(st.stage)`), so `deliver_flight` needs no
  `None` check on an Issue that `merge` has already established is there.
- **The real `deliver` in `pair.py` is untested,** as `gate` and `provision`
  are. It is a thin `subprocess` call.
