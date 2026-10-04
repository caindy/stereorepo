# Record each gate the loop runs, where a reader of the Issue can find it

The supervisor runs the gate outside the seats' sandbox before an Issue
leaves `in-progress/` (`close_stage` and `run_gate` in `pair/loop.py`) and
again before it lands. Nothing records what that gate ran or what it found.
`events.jsonl` has no entry for it, the Issue file does not mention it, and the
seats cannot see it from their sandbox.

fitch-mvp showed what that costs. On `inverse-pairs-follow-the-record`, the
seats' last note said the four rewritten Neo4j queries "have never been run
against Neo4j", because no Neo4j was reachable in their sandbox. In fact the
supervisor's gate had run them, with Docker, before the Issue moved to
`desk-check/`: a step that could not run would have paused the loop
instead. The desk check showed the seats' note and nothing of the gate, so
the developer was told something false, and the session supervising the
loop repeated it and re-ran the gate by hand.

## Wanted

- **An event per gate run.** Each time the supervisor runs a gate, the event
  log gets one `gated` event naming the Issue, the stage it was closing (or
  `landing`), the targets it selected (or the whole gate), the outcome
  (`passed`, `failed` or `could-not-run`), and the count of steps, with the
  names of any that failed or could not run. `pair-status` and `pair-watch`
  read it as they read the other kinds, and the event table in
  `pair/README.md` lists it.
- **A line in the Issue file.** The gate that lets an Issue leave
  `in-progress/` adds one line to the Issue file, after its notes, such as
  "Gated by the supervisor at 11:58: `meta`, `fitch`, 96 steps passed,
  including 24 Neo4j tests". A Flight's brief, and a `developer` Issue's
  desk check, then show what the supervisor checked beside what the seats
  could.
- **The seats know the gate is not theirs.** The prompts say that the
  supervisor's gate, not the seat's sandbox, is where a step the sandbox
  cannot run is checked. A seat's note may then say that the step is left
  to the supervisor's gate, not that it is unchecked.

## How anyone will know it is done

- A test with a fake gate: closing `in-progress/` writes one `gated` event
  and one line in the Issue file, for a pass, a failure and a step that
  could not run.
- A landing gate writes its own `gated` event, with the stage `landing`.
- `pair-status --json` shows the last gate's outcome for the Issue underway.

## Out of scope

- What the gate runs, or how its targets are selected (DR-303).
