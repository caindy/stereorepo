---
difficulty: developer
parent: pair-versus-single-seat
---

# Propose which landed Issues to replay

One part of `pair-versus-single-seat`. The replays are expensive, so the
developer chooses which landed Issues they run on. This Issue asks for a
choice, so it is `developer`: the seats write the proposal into this file,
and the developer chooses at its desk check.

## Wanted

A `## Proposal` section in this file, holding:

- **Candidates.** Between twelve and twenty Issues from `issues/done/` that
  did their own work, not Flights (an Issue that other Issues name in
  `parent:`), whose work landed in their parts. Each comes
  with its slug, its `difficulty`, the area it changed (`pair/`, `.meta/`
  checks, bootstraps, documentation, or other), the commit it started from
  (the parent of its `Start <slug>` commit on `main`), and, where history
  shows one, the later Issue or revert that fixed its change.
- **Spread.** The candidates span every difficulty that has landed and every
  area above, and favour Issues whose change was later fixed. A table says
  how many fall in each difficulty and area.
- **How the fixes were found.** The `git log` searches used (a later
  Issue file or commit message that names the slug, a `Revert` commit), so
  the developer can check them.
- **Cost.** For each candidate, its logged two-seat cost, turns and
  wall-clock from the `.pair/turns.jsonl` of the stereorepo checkout
  where rows for it exist (if a seat cannot read that file, say so here), and the sum
  for replaying the whole proposal in both modes. Where a candidate has no
  rows, say so and estimate it from the mean of its difficulty.
- **Recommendation.** The subset the seats would replay if the budget allows
  only eight to ten, and why.

The proposal is data in this Issue file. No code changes.

## How anyone will know it is done

- The section exists, every candidate's start commit resolves with
  `git rev-parse`, and every named fix exists in history.
- The developer has chosen the sample at the desk check and written it into
  this file as a `## Chosen sample` list of slugs, which
  `pair-mode-decision` reads.

## Out of scope

- Running any replay.
