---
difficulty: medium
parent: pair-versus-single-seat
waits_on:
  - replay-landed-issue
---

# Report the replays by mode

One part of `pair-versus-single-seat`. The report turns the replays kept
under `.pair/replays/` into the four criteria the decision rests on.

## Wanted

A recipe, `just pair-replay-report`, that reads every replay under
`.pair/replays/` and prints, for each replayed slug and summed by
difficulty, for each mode:

| Criterion | Measure |
|---|---|
| Quality | whether the replay landed; gate failures on the way (from `events.jsonl`); for an Issue whose change was later fixed, whether the fixing Issue's tests pass against the replay's result, where that Issue added tests; how many of the secondary seat's turns changed something, and in which files |
| Autonomy | pauses, send-backs and `Needs elaboration` sections |
| Time | wall-clock, gate included; turns per stage |
| Tokens | API-equivalent cost, with cache reads and cache writes apart |

It also prints, as a third reference beside the two modes, the same
measures from the original two-seat run where stereorepo's own
`.pair/turns.jsonl` and `.pair/events.jsonl` hold rows for the slug, marked
as run by older loop code and models.

With `--diff <slug>`, it shows the two modes' `landed.diff` side by side
for the developer to judge.

The fixing Issue for a slug is read from a `fixed_by:` list in the replay's
`outcome.json` or given by `--fixed-by <slug>=<fix>`; the report runs the
fixing Issue's added tests against the replay's clone and records pass or
fail.

## How anyone will know it is done

Tests in `pair/test_pair.py`, on fixture replay directories:

- Two replays of one slug, one per mode, print all four criteria for both
  modes, with costs, cache reads and cache writes summed from the rows.
- A slug replayed in only one mode is printed with the other mode marked
  missing, not dropped.
- A replay whose fix's tests fail against it is reported as having the
  defect.
- `--diff` prints both diffs.

## Out of scope

- Running replays.
- Judging the diffs; that is the developer's.
