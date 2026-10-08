# Find out whether the pair is worth its second seat

The pair loop runs two seats on every Issue, which roughly doubles what an
Issue costs to read, since both seats read the same code. Its first day (11
units of work, 88 turns, about 110 minutes of turns and about $28 of
API-equivalent usage) showed that it converges, runs without the developer,
and lands work that passes the gate. It did not show that the second seat
catches enough to be worth its cost, against one careful seat and the gate.
The answer is a Decision Record, and the choice in it is the developer's.

The loop now records most of what the comparison needs. `.pair/turns.jsonl`
holds each turn's seat, stage, seconds, tokens and cost, and whether it
changed anything. `.pair/events.jsonl` holds each start, landing, gate run,
desk check, pause and send-back. More than a hundred Issues have landed under
two seats, so the two-seat side of the comparison mostly exists already. What
is missing is a way to run the loop with one seat, a report that reads both
modes the same way, and a trial.

## Wanted

- **A single-seat mode.** A flag on `just pair` runs every turn as the
  primary seat, with the same prompts, stages, gates and desk checks. A stage
  closes when the seat leaves it as it stands and its requirement is met, as
  a stage closes today when both seats have. Each row in `turns.jsonl` and
  each `started` event records which mode ran, so the two are never mixed up.
- **A report.** A recipe reads `turns.jsonl`, `events.jsonl` and the Issue
  files in `issues/done/`, and prints the four criteria below for each mode,
  by difficulty:

  | Criterion | Measure |
  |---|---|
  | Quality | desk-check send-backs; Issues sent back for elaboration; how many of the secondary seat's turns changed something, and what (two-seat mode only) |
  | Autonomy | pauses, send-backs and `Needs elaboration` sections per Issue |
  | Time | wall-clock per Issue, gate included; turns per stage |
  | Tokens | API-equivalent cost per landed Issue, cache reads and writes apart |

  Defects found after landing cannot be read from the logs. The report leaves
  that line for the developer to fill in by hand before the decision.
- **A trial.** Over the next run of comparable Issues, the loop alternates
  modes Issue by Issue, so the two modes see work of the same kind and
  difficulty, until each mode has landed enough Issues of each difficulty for
  the report to compare. The trial includes Issues outside `pair/`, such as
  `.meta/` checks, bootstraps and documentation, and may include another
  portfolio's Issues, since the mode works wherever the loop runs.
- **The decision.** A Decision Record in stereorepo states what the trial
  measured and which mode the loop runs by default, with the rejected mode's
  costs. It cites the report's numbers, not impressions.

## How anyone will know it is delivered

- `just pair` with the single-seat flag lands an Issue with only the primary
  seat's turns in `turns.jsonl`, each row marked with its mode.
- The report prints all four criteria for both modes from the real logs.
- The Decision Record exists, and `pair/README.md` says which mode is the
  default and how to run the other.

## Out of scope

- Changing the prompts, stages or gates to suit one seat. The comparison is
  of the seat count alone.
- A third seat, or seats on different models.
