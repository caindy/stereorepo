# The seats' standing instructions are refused by the model's safeguards

On 2026-10-01 the loop paused on `seats-run-the-targeted-gate`: the primary
seat's first turn was refused by the API's safeguards, and so was the restart
the loop gave it, so the loop paused with "the primary seat failed twice".
The refusal named the category `reasoning_extraction`. The secondary seat
never ran. The full message is the `paused` event in `.pair/events.jsonl` in
the developer's checkout.

The refusal comes from the seats' own standing instructions, not from the
Issue or a long conversation: it happened on a fresh session's first message,
twice. The only change to those instructions since the last run that worked is
`pair-notes` (landed as `9f129a71`), which added closing sentences to
`pair/prompts/primary.md` and `pair/prompts/secondary.md` asking each seat how
to end its turn, and a matching sentence in the turn message `Loop.message`
builds in `pair/loop.py`. A copilot session that quoted and examined that
wording was stopped by a classifier the same way, so read it rather than
paste it.

Until this is fixed, every Issue the loop takes will pause the same way.

## What to do

This is the developer's, worked in an interactive session, not by the loop:
the loop's seats would be refused before they could change anything.

- Either rephrase the closing instructions so they ask for what the next
  reader needs (what was decided and why, what was checked and what it
  showed) without the wording that trips the safeguards, or revert
  `9f129a71` and re-file `pair-notes` with new wording.
- Check the fix with one fresh seat session on a single turn before running
  the loop again.
- Then `just pair` resumes `seats-run-the-targeted-gate`, which is paused
  in `.pair/state.json`, and this note can be deleted.
