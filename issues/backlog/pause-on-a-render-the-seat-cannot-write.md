---
difficulty: medium
---

# Pause the loop when a stale page is one the seat cannot write

When an Issue changes the source of a page that `just render` writes under
`.claude/skills/`, the seats' sandbox denies the write
(`render-in-seat-sandbox`), and the gate's `rendered prose` step
(`.meta/checks/files/rendered.py`) reports the stale copy as `x`. The loop
treats `x` as the seats' to fix: `run_gate` in `pair/loop.py` returns
`gate_fails` whenever the gate fails, so it hands the failure back turn after
turn until the round cap sends the Issue to the backlog. Neither seat can fix
it. Found in `trim-decision-records-065-177`, which went three rounds on it
before the change was split out.

## How to reproduce

On a branch, change the source of a skill that renders to
`.claude/skills/<skill>/SKILL.md` (for example the `/technical-writing`
skill's preamble in `.meta/assertions/imported/structure.yaml`) and commit
without rendering. Run the loop on it: every round's gate failure names the
stale `.claude/skills/` page, the seats' `just render` reports it could not
write it, and the Issue goes back to the backlog at the round cap.

## Wanted

- When every failure in the gate's output is a `rendered prose` finding for
  a page the seats cannot write, the loop pauses rather than handing it back,
  the way `GateUnrunnable` does for a `?` step. The pause reason names each
  such file and says to run `just render` outside the sandbox, then resume.
- "A page the seats cannot write" is one under a path the seats'
  confinement denies (`confinement()` in `pair/seats.py`) or that the
  sandbox otherwise holds back from writes, which today means `.claude/`.
  Derive the rule from one place, so it does not drift from the sandbox.
- Any other failure in the same gate run, including a stale page the seats
  can write, keeps today's behaviour: the whole failure goes back to the
  seats.
- How the loop tells such a finding apart (reading the gate's output in
  `pair/loop.py`, or having `rendered prose` report such a page as `?` with
  a reason) is the pair's choice. If the step changes, the developer's own
  `just gate` must still fail on a stale page outside any sandbox.

## Out of scope

- Widening the seats' sandbox to allow writes under `.claude/`.
- The loop rendering the page itself.

## Done when

- A pair-loop test in which the only gate failure is a stale page under
  `.claude/skills/` ends in a pause whose reason names the file, not in
  another turn.
- A pair-loop test in which the gate fails on that page and on something
  else hands the failure back to the seats as today.
- A test in which the only failure is a stale page outside `.claude/` hands
  it back as today.
