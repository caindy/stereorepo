# Start a fresh seat session when the model refuses a seat's message

A seat that fails is restarted once from its session id, and a seat that fails
twice pauses the loop with the session id kept, so the next run resumes the
same session. That suits a crash or a timeout, where the session's history is
what the seat needs. It cannot recover from a refusal: the refused message is
in the session's history, so every resume replays it and is refused again.

## What happened

On 2026-10-01 the loop paused on `seats-run-the-targeted-gate`: the primary
seat's first turn was refused by the API's safeguards, and so was the restart
the loop gave it, so the loop paused with "the primary seat failed twice". The
refusal named the category `reasoning_extraction`. The secondary seat never
ran. The full messages are the `paused` events in `.pair/events.jsonl` in the
developer's checkout.

The refusal came from the seats' own standing instructions, not from the Issue
or a long conversation: it happened on a fresh session's first message, twice.
The only change to those instructions since the last run that worked was
`pair-notes` (landed as `9f129a71`), which added closing sentences to
`pair/prompts/primary.md` and `pair/prompts/secondary.md` and a matching
sentence in the turn message `Loop.message` builds in `pair/loop.py`. A copilot
session that quoted and examined that wording was stopped by a classifier the
same way, so that wording is to be read, not pasted.

`9f129a71` was reverted, and `pair-notes` went back to the backlog with a
`Needs elaboration` section until its wording is redone. The next run still
paused: it resumed the primary seat's saved session, whose history held the
refused message. Only clearing the saved session id by hand, in
`.pair/state.json` and `.pair/primary.session`, let a fresh seat start with
the restored instructions, and the Issue went on.

## What is wanted

- **A refusal is told apart from a failure.** `ClaudeSeat` recognises a turn
  that ends in the model's refusal (an API error naming the safeguards) and
  reports it as such in its `TurnResult`, distinct from a crash, a timeout or
  another API error.
- **A refused seat restarts fresh.** On a refusal, the loop restarts the seat
  once with a new session rather than resuming the old one, and records that it
  did. If the fresh session is refused too, the loop pauses as now, but with
  no session id saved for that seat, so the next run starts it fresh.
- **The pause says so.** The `paused` event and `just pair-status` say the seat
  was refused, not that it failed, so the developer knows to look at the
  instructions or the Issue rather than the machine.
- `pair/README.md` says how a refusal is handled.

## Out of scope

- Rewording `pair-notes`; that is its own `Needs elaboration`.
- Retrying a refused message with different wording.

## Done when

- A seat whose turn is refused is restarted with a fresh session, and a second
  refusal pauses the loop with no session saved for that seat.
- A crash or timeout is still restarted from its session, as now.
- The pause reason names the refusal.
- The pair tests cover each of these with a fake seat, and `just gate` passes.
