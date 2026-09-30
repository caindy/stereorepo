---
difficulty: easy
parent: flight-instruments
---

# Exit codes that say what the loop did

`pair/pair.py` exits 0 whatever `Loop.run`, `Loop.groom`, `Loop.accept` or
`Loop.resume` returned: `landed`, `desk-check`, `paused`, `stopped`, `empty`,
`groomed` and the rest are only printed as `pair: <outcome>`. A session driving
the loop has to parse that line to learn what happened. The one non-zero exit
today is 1, when another process holds the run lock.

## What is wanted

- `main` in `pair/pair.py` maps each outcome string the `Loop` entry points
  return to its own exit code, in one table, and exits with it: for `run`,
  `groom`, `accept` and `resume`. The strings today are `landed`,
  `desk-check`, `kicked` (from `run --once` when the Issue is sent back),
  `paused`, `stopped`, `empty`, `grooming`, `refused`, `busy`, `nothing`,
  `none`, `groomed`, `accepted` and `resumed`.
- The early branch in `main` that answers a Flight's desk check
  (`just pair-accept <slug>`, `just pair-resume <slug>`) and returns 0 before
  taking the lock uses the same table.
- An outcome where the loop did what it was asked and needs nothing more
  (`landed`, `groomed`, `accepted`, `resumed`) exits 0. Every other outcome
  has a distinct non-zero code, and "another process holds the lock" keeps its
  own, 1. `desk-check` has one code whether or not `--flight` was given: a
  session running `just pair --flight <slug>` expects that code, and the
  developer still has to answer the desk check.
- An outcome string with no entry in the table is a test failure, not a silent
  0.
- `pair/README.md` lists the codes in a table.

## Out of scope

- The event log and `just pair-watch` (`pair-event-log`).
- Changing what any outcome means, or when it is returned.

## Done when

- Each outcome of each command exits with the code in the table, and the pair
  tests check that every string the `Loop` entry points can return is in it.
- `pair/README.md` lists the codes, and `just gate` passes.
