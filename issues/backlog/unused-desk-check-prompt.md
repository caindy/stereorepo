# Remove the stage prompt no turn loads

`Loop.message` loads `pair/prompts/stage-{stage}.md` for the stage a turn runs
in. No turn runs in a `desk-check` stage: `Loop.resume` moves the Issue to
`in-progress/` before the pair takes it up again, and sends its own note. So
`pair/prompts/stage-desk-check.md` is never read, yet it reads as if it
governs the resumed turn.

## Done when

- `stage-desk-check.md` is gone, or a test shows a turn that loads it.
- `just gate pair` passes.
