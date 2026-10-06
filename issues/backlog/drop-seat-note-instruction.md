---
difficulty: medium
waits_on: [pair-notes-belong-to-the-loop]
---

# Stop telling a seat to write in the Issue file what the loop already keeps

`pair/prompts/stage-in-progress.md` tells the seat to "Write what the next
reader should know about this change in the issue file, not in commit
messages". The loop keeps each turn's closing message as the note
(`Loop.keep_note`), so a seat that follows the sentence writes a second one.
`pair-notes-belong-to-the-loop` makes that harmless by putting the Pair notes
back after each turn. This Issue removes the cause.

The prompt sentence was left in place deliberately. The first version of
`pair-notes` changed the seats' instructions in this area, and a fresh seat's
first turn was refused twice by the model's safeguards, so it was reverted
(`6fd1ea94`). The redo changed nothing the seats are told.

## Wanted

- Remove the sentence, or narrow it to the plan, which the same prompt
  already asks the seat to update when the work shows it was wrong. Change no
  other wording.
- Before it lands, run a fresh seat's first turn with the new prompt and
  record the outcome in this file. If it is refused, send this Issue back
  with the refusal, and leave the prompt as it is.

## Out of scope

- Any other prompt change.

## Done when

- A fresh seat's first turn under the new prompt was not refused, and this
  file records the run.
- The count of restores that `pair-notes-belong-to-the-loop` reports in
  `turns.jsonl` falls to zero over the next Issues. Say in this file how many
  Issues were watched.
