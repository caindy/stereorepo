---
difficulty: easy
---

# Seats run the targeted gate; the loop runs the full one

`pair/prompts/stage-in-progress.md` tells a seat to keep `just gate` green and
to run it before it finishes its turn. So every implementing turn runs the
whole gate, every Project in the portfolio: the Rust seed's build and mutation
testing and the Python seed's mutation testing included, however little of
them the change touches, and often more than once in a turn. On
`pair-notes`, a change confined to `pair/`, each seat's implementation turn
ran the full gate at least twice, and the turns took 12 and over 19 minutes.
The loop then runs the full gate again before it lands the Issue (`gate` in
`pair/pair.py`, called from `pair/loop.py`), which is the check that decides.
`AGENTS.md` already says to prefer a targeted gate while working.

## What is wanted

- **The stage prompts ask for the targeted gate.** `stage-in-progress.md` is
  the only stage prompt that names the gate today. It asks a seat to run the
  gate of each Project its change touches, by name, and to leave the whole
  `just gate` to the loop, which runs it before the Issue lands and hands back
  any failure with its output, as now. The Projects are those
  `just --list` shows under `gate`: `meta` (`.meta/`, and the repository-wide
  checks on `wiki/`, `issues/` and the instructions), `rust-seed`
  (`bootstraps/rust/seed/`), `python-seed` (`bootstraps/python/seed/`) and
  `pair` (`pair/`). The prompt says which directory belongs to which Project,
  or points at where that is written (each Project's `name` in
  `.meta/assertions/structure.yaml` is its directory), so a seat need not
  guess. Every turn edits the Issue file under `issues/`, which `meta` checks,
  so the prompt asks for `just gate meta` on every turn, plus the gate of each
  other Project whose directory the change touches.
- **The loop's gate is unchanged:** the full `just gate` before landing, and
  on a rebase after `main` moved.
- **The words follow:** `pair/README.md` says which gate a seat runs and which
  the loop runs. The targeted-gate sentence in `AGENTS.md` lists `pair` among
  its examples, and its "run it after authoring changes" does not contradict
  the prompt.

## Out of scope

- Narrowing the loop's own gate to the Projects a change touches (on the
  roadmap: `gate-only-touched-projects`).
- Changing how `.meta/assertions/structure.yaml` declares a Project's
  directory; the prompt may point at the `name` fields or state the mapping in
  words.

## Done when

- No stage prompt asks a seat to run the whole `just gate`, and
  `stage-in-progress.md` names the targeted gate and how to pick it:
  `just gate meta` always, and `just gate <project>` for each other Project
  the change touches. A seat that edits only `pair/` and its Issue file is
  told to run `just gate meta` and `just gate pair`, and nothing more.
- `test_gate_failure_goes_back_to_the_pair_with_its_output` in
  `pair/test_pair.py` still passes unchanged: a full-gate failure at landing
  still reaches the seats with its output.
- `just gate pair` and `just gate meta` pass, and then `just gate`.
