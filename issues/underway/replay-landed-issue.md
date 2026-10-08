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
  `.pair/events.jsonl`, the landed diff (start commit to the clone's final
  `main`) as `landed.diff`, and an `outcome.json` with the outcome (`landed`,
  `sent-back` or `paused`), the mode, the start commit and the wall-clock.
- Leaves stereorepo's `main`, its working tree and the developer's checkout
  unchanged, and can be run again over an earlier replay of the same slug and
  mode only with `--force`, which deletes the earlier one first.

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
- A slug with no `Start <slug>` commit is refused; a second replay without
  `--force` is refused.

## Out of scope

- Replaying another portfolio's Issues.
- The report over replays; that is `replay-report`.
