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
  has no fault for it.
- The pair tests cover each of these, and `just gate` passes.
