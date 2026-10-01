# Seats run the targeted gate; the loop runs the full one

`pair/prompts/stage-in-progress.md` tells a seat to keep `just gate` green and
to run it before it finishes its turn. So every implementing turn runs the
whole gate, every Project in the portfolio: the Rust seed's build and mutation
testing and the Python seed's mutation testing included, however little of
them the change touches, and often more than once in a turn. On
`pair-notes`, a change confined to `pair/`, each seat's implementation turn
ran the full gate at least twice, and the turns took 12 and over 19 minutes.
The loop then runs the full gate again before it lands the Issue, which is the
check that decides. `AGENTS.md` already says to prefer a targeted gate while
working.

## What is wanted

- **The stage prompts ask for the targeted gate.** `stage-in-progress.md`
  (and any other stage prompt that names the gate) asks a seat to run the
  gates of the Projects its change touches, by name (`just gate pair`,
  `just gate meta`, and so on, as `just --list` shows them), and to leave the
  whole `just gate` to the loop, which runs it before the Issue lands and
  hands back any failure as now.
- **The loop's gate is unchanged:** the full `just gate` before landing.
- **The words follow:** `pair/README.md` says which gate a seat runs and which
  the loop runs.

## Out of scope

- Narrowing the loop's own gate to the Projects a change touches (on the
  roadmap: `gate-only-touched-projects`).

## Done when

- No stage prompt asks a seat to run the whole `just gate`, and the
  implementation prompt names the targeted gate.
- A full-gate failure at landing still reaches the seats with its output.
- `just gate` passes.
