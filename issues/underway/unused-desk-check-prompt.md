---
difficulty: easy
---

# Remove the stage prompt no turn loads

`Loop.message` loads `pair/prompts/stage-{stage}.md` for the stage a turn runs
in. No turn runs in a `desk-check` stage: `Loop.resume` moves the Issue to
`in-progress/` before the pair takes it up again, and sends its own note. So
`pair/prompts/stage-desk-check.md` is never read, yet it reads as if it
governs the resumed turn. The turn after `just pair-resume` loads
`stage-in-progress.md` and carries the note
"The developer sent this back from the desk check." instead.

A Flight's desk check does not load it either: `Loop.resume_flight` sends the
Flight back to `backlog/`, and its next turns run in the stages a Flight runs
in.

## What is wanted

- Delete `pair/prompts/stage-desk-check.md`.
- Before deleting it, confirm that no path reaches `Loop.message` with
  `st.stage == "desk-check"`. If one does, keep the file and add a test in
  `pair/test_pair.py` that drives that path and shows the prompt is loaded.

## Out of scope

- Changing what the resumed turn is told, or the note `Loop.resume` sends.
- The other stage prompts.

## Done when

- `stage-desk-check.md` is gone, or a test shows a turn that loads it.
- No file in the repository names `stage-desk-check.md`.
- `just gate pair` passes.
