# Find out whether the pair is worth its second seat

The pair loop runs two seats on every Issue, which roughly doubles what an
Issue costs to read, since both seats read the same code. Its first day (11
units of work, 88 turns, about 110 minutes of turns and about $28 of
API-equivalent usage) showed that it converges, runs without the developer,
and lands work that passes the gate. It did not show that the second seat
catches enough to be worth its cost, against one careful seat and the gate.
The answer is a Decision Record, and the choice in it is the developer's.

The comparison replays Issues that have already landed, rather than waiting
for new work. More than a hundred Issues have landed under two seats. Each
started from a known commit (the parent of its `Start <slug>` commit on
`main`), and for each, later history shows whether its change had to be
fixed. Replaying a sample of them in both modes, from the commit each
started from, compares the same Issue on the same code with only the seat
count changed. Nothing a replay does reaches `main`.

## Wanted

- **A single-seat mode.** A flag on `just pair` runs every turn as the
  primary seat, with the same prompts, stages, gates and desk checks. A stage
  closes when the seat leaves it as it stands and its requirement is met, as
  a stage closes today when both seats have. Each row in `turns.jsonl` and
  each `started` event records which mode ran.
- **A replay.** A recipe takes a landed Issue's slug and a mode, and runs the
  Issue again in a scratch clone:
  - The clone's `main` is reset to the commit the Issue started from, and its
    backlog holds only that Issue, as its file stood then.
  - The loop that runs it is the current one, from the stereorepo checkout,
    run against the clone as a portfolio's loop is
    (`uv run --script <stereorepo>/pair/pair.py run --once`). For an Issue
    that changes `pair/`, the seats edit the clone's old `pair/`, not the loop
    that runs them.
  - The clone has no remote, and the replay's logs, its landed diff and its
    outcome (landed, sent back, paused) are kept for the report.
  - A desk check in a replay is answered by accepting it, so that a
    `developer` Issue completes. The developer reviews its result in the
    report instead.
  - Both modes are replayed, not only the single seat. The logged two-seat
    runs used older loop code and earlier models, so they are kept as a
    third reference, not compared directly.
- **A sample.** The developer chooses the Issues to replay, from a proposal
  the seats write into this Issue. The proposal spans the difficulties and the
  areas of the repository (`pair/`, `.meta/` checks, bootstraps,
  documentation), favours Issues whose change was later fixed by another
  Issue (found from history: a later Issue that names it, or a revert), and
  says what the replays would cost, from the per-Issue cost already in
  `turns.jsonl`.
- **A report.** A recipe prints, for each sampled Issue and summed by
  difficulty, the four criteria for each mode:

  | Criterion | Measure |
  |---|---|
  | Quality | whether the replay landed; gate failures on the way; for an Issue whose change was later fixed, whether the replay's result has the same defect, checked by running the fixing Issue's tests against it where it added any; how many of the secondary seat's turns changed something, and what |
  | Autonomy | pauses, send-backs and `Needs elaboration` sections |
  | Time | wall-clock, gate included; turns per stage |
  | Tokens | API-equivalent cost, cache reads and writes apart |

  It also shows each pair of landed diffs side by side, for the developer to
  judge the quality the numbers do not reach.
- **The decision.** A Decision Record in stereorepo states what the replays
  measured and which mode the loop runs by default, with the rejected mode's
  costs. It cites the report, not impressions.

## How anyone will know it is delivered

- `just pair` with the single-seat flag lands an Issue with only the primary
  seat's turns in `turns.jsonl`, each row marked with its mode.
- Replaying a landed Issue in either mode leaves `main` and the developer's
  checkout unchanged, and keeps the replay's logs and diff.
- The report prints all four criteria for both modes over the chosen sample.
- The Decision Record exists, and `pair/README.md` says which mode is the
  default and how to run the other.

## Out of scope

- Changing the prompts, stages or gates to suit one seat. The comparison is
  of the seat count alone.
- A third seat, or seats on different models.
- Replaying another portfolio's Issues. The replay works on stereorepo's own
  history first.
