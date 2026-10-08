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
  hours of wall-clock, so the seats do not start them. They are kept in the
  main checkout's `.pair/replays/<slug>-<mode>/`, and only a replay run from
  a `main` that holds `replay-in-the-era-it-replays` (commit `e59cad35`)
  counts: an older one may have failed on an era clash that it reports as
  `sent-back`, not `clashed`. If any of the twenty are missing or older, the
  seats add a `# Needs elaboration` section naming them.
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
- `just pair` with no flag runs the chosen mode, and the flag runs the other:
  a test in `pair/test_pair.py`, beside
  `test_single_seat_runs_an_issue_to_main_with_the_primary_alone`, starts an
  Issue with no flag and finds `State.mode` is the chosen mode. If two seats
  stay the default, `--single-seat` is unchanged; if one seat becomes it,
  `--single-seat` gives way to a flag that names two seats, and `pair/pair.py`'s
  usage text, the `pair` recipe's comment in `justfile` and `pair/README.md`
  say so.

## Out of scope

- Changing prompts, stages or gates to suit the chosen mode.
- Running any replay, including the second round of the sample; if the
  report leaves the choice open, the seats recommend the second round in the
  Decision Record and the developer runs it.

# Needs elaboration

On 8 October 2026 the main checkout's `.pair/replays/` holds 18 of the 20
first-round replays. Missing: `seed-rendered-gate-lost` (single) and
`adoption-discipline` (both modes). All 18 kept were run between 10:37 and
15:13, before `replay-in-the-era-it-replays` landed at 15:32, so none can
show `clashed`, and `squash-reverts-commits-on-main`, `fresh-seat-after-refusal`
and `bootstrap-render-step` are known to have been sent back by a clash. The
developer re-runs the whole first round from today's `main` (with `--force`
over the kept ones) before the seats can write the report.

## Pair notes

> **primary, backlog turn 1**
>
> I groomed `issues/underway/pair-mode-decision.md` and committed it as `c26dc02d`. Its `difficulty` stays `developer`, because the Issue asks the developer to choose the default mode. I also added a `# Needs elaboration` section, because the replays the Issue depends on aren't ready.
>
> **The replays aren't ready.** The main checkout's `.pair/replays/` holds 18 of the 20 first-round replays:
> - **Missing:** `seed-rendered-gate-lost` in single-seat mode, and `adoption-discipline` in both modes.
> - **Too old:** all 18 were run between 10:37 and 15:13 on 8 October 2026. The fix for era clashes (`replay-in-the-era-it-replays`) landed at 15:32, so none of them can report a `clashed` outcome. A replay that failed on an era clash shows as `sent-back` instead, which the seats would count as their own failure. Three are known to have been sent back that way: `squash-reverts-commits-on-main`, `fresh-seat-after-refusal` and `bootstrap-render-step`.
>
> Before the seats can write the report, you need to re-run the whole first round from today's `main`, using `--force` to replace the kept replays.
>
> **Other changes to the Issue:**
> - **Which replays count:** they are kept in the main checkout's `.pair/replays/<slug>-<mode>/`, and only one run from a `main` that includes commit `e59cad35` counts.
> - **How anyone will know it is done:**
>   - A new test in `pair/test_pair.py` starts an Issue with no flag and checks that `State.mode` is the chosen mode.
>   - If two seats stay the default, the existing `--single-seat` flag is unchanged.
>   - If one seat becomes the default, `--single-seat` is replaced by a flag that selects two seats. The usage text in `pair/pair.py`, the comment on the `pair` recipe in `justfile`, and `pair/README.md` all say so.
> - **Out of scope:** the seats run no replays, including the second round of the sample. If the report leaves the choice open, the seats recommend a second round in the Decision Record, and you run it.
