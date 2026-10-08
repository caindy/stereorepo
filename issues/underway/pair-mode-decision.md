---
difficulty: developer
parent: pair-versus-single-seat
waits_on:
  - replay-sample-proposal
  - replay-report
  - replay-in-the-era-it-replays
---

# Decide which mode the loop runs by default

One part of `pair-versus-single-seat`, and its last. The choice of default
mode is the developer's, so this Issue is `developer`: the seats write the
evidence, the options and their recommendation, and the developer decides at
the desk check.

## Wanted

- **The replays.** Before this Issue starts, the developer runs `just
  pair-replay <slug> --mode single` and `--mode pair` for each slug in the
  `## Chosen sample` of `replay-sample-proposal`. The replays cost money and
  hours of wall-clock, so the seats do not start them. If the replays are
  not all under `.pair/replays/` when this Issue starts, the seats add a
  `# Needs elaboration` section naming the ones missing.
- **The report.** The output of `just pair-replay-report` over the sample,
  committed into this Issue file under `## Report`.
- **A draft Decision Record**, `.meta/assertions/decisions/DR-nnn.yaml`
  numbered as `AGENTS.md` says, re-rendered, which states what the replays
  measured on each criterion, cites the report, and sets out both options
  with their costs:
  - two seats stay the default, and single-seat is a flag;
  - one seat becomes the default, and two seats a flag.

  The seats write their recommendation into it. The developer settles the
  choice at the desk check, and the seats leave the record stating the
  chosen mode.
- **`pair/README.md`** says which mode is the default and how to run the
  other. If the choice is one seat, the default flips in `pair/loop.py`
  and the flag on `just pair` names the other mode.

## How anyone will know it is done

- The Decision Record exists, cites the report, and gives the rejected
  mode's costs.
- `pair/README.md` names the default mode and the flag for the other.
- `just pair` with no flag runs the chosen mode, as the tests of
  `single-seat-mode` show for each mode.

## Out of scope

- Changing prompts, stages or gates to suit the chosen mode.
