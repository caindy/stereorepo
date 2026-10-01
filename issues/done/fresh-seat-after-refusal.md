---
difficulty: medium
---

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

## How to reproduce

The refusal cannot be summoned on demand, so reproduce it with a seat that
returns the refusal's error text. The `paused` event from 2026-10-01 carried
it, as the `result` text of a `result` event with `is_error` set:

```
API Error: Opus 5.5's safeguards flagged this message
(https://www.anthropic.com/legal/aup). This sometimes happens with safe,
normal conversations. Claude Code can't respond to this message with Opus 5.5.
[...]
Details: `[reasoning_extraction]`
```

1. In `pair/test_pair.py`, script the fake seat's turn to fail with that error
   on every send. `FakeSeat.send` fails with the fixed error `"boom"` today, so
   it needs a way to be given the error text.
2. Run the loop on an Issue.
3. Today `Loop.turn` restarts the seat with the same session id (the fake
   seat's `opened` list shows `("primary", "primary-session")`), pauses with
   "the primary seat failed twice", and leaves the session in `State.sessions`
   and in `.pair/primary.session`, so the next run resumes it.

## What is wanted

- **A refusal is told apart from a failure.** `ClaudeSeat` recognises a turn
  that ends in the model's refusal (an API error naming the safeguards) and
  reports it as such in its `TurnResult`, distinct from a crash, a timeout or
  another API error. Recognise it from the error text of the `result` event
  (the phrase `safeguards flagged this message`), in one named function in
  `pair/seats.py` with a docstring quoting the shape it matches, so the match
  can be updated in one place when the harness changes its wording.
- **A refused seat restarts fresh.** On a refusal, the loop restarts the seat
  once with a new session rather than resuming the old one, and records that it
  did. A new session means the seat is opened with no `resume`: `Loop.seat`
  takes it from `State.sessions` or from `<role>.session`, so both are
  cleared for that seat. The fresh seat's message is the turn message without
  the `RESTARTED` preamble, since that preamble tells the seat its session
  survived. If the fresh session is refused too, the loop pauses as now, but with
  no session id saved for that seat, so the next run starts it fresh. The
  refused fresh session reports a session id of its own; `Loop.turn` today
  stores any `result.session_id` in `State.sessions`, so that one must not be
  kept either. `ClaudeSeat.send` also writes each new session id to
  `<role>.session` as soon as it sees it, before the turn ends, so the loop
  must remove that file after each refused turn, not only before the fresh
  start.
- **The next run does not claim a surviving session.** A refusal pause leaves
  `State.in_turn` naming the seat, and `Loop.run` prepends `RESTARTED` to the
  message whenever `in_turn` matches the seat about to take its turn. After a
  refusal pause the seat has no session to resume, so the next run sends the
  plain turn message.
- **The pause says so.** The `paused` event and `just pair-status` say the seat
  was refused, not that it failed, so the developer knows to look at the
  instructions or the Issue rather than the machine.
- `pair/README.md` says how a refusal is handled.

## Out of scope

- Rewording `pair-notes`; that is its own `Needs elaboration`.
- Retrying a refused message with different wording.

## Done when

- A seat whose turn is refused is restarted with a fresh session, and a second
  refusal pauses the loop with no session saved for that seat, in
  `State.sessions` or in `<role>.session`.
- The run after a refusal pause opens that seat with no `resume`, and its
  message does not begin with `RESTARTED`.
- A crash or timeout is still restarted from its session, as now.
- The pause reason names the refusal, in the `paused` event and in
  `just pair-status`.
- The pair tests cover each of these with a fake seat whose error is the
  quoted refusal text, and `just gate pair` passes.

## The plan

1. **`pair/seats.py`.** Add `refused: bool = False` to `TurnResult`, and a
   module-level `is_refusal(error: str | None) -> bool` whose docstring quotes
   the refusal's error text from above and which matches
   `safeguards flagged this message`. In `ClaudeSeat.send`, the `result`
   branch sets `refused=is_refusal(error)`. The other failures (the process is
   gone, a timeout, an exit mid-turn) stay `refused=False`.
2. **`pair/loop.py`, forgetting a session.** Add `Loop.forget_session(st,
   role)`, which pops `st.sessions[role]` and unlinks `<role>.session`. It is
   the one place both stores are cleared for a seat.
3. **`pair/loop.py`, `Loop.turn`.** Change the signature to
   `turn(st, role, message, restarted=False)`, so that `turn` adds
   `RESTARTED` itself rather than `Loop.run` adding it. That way the fresh
   restart can send the plain message even when the turn was itself a resume.
   - On a failure that is not a refusal, nothing changes: the seat is restarted
     from its session with `RESTARTED`.
   - On a refusal: stop and drop the seat, `forget_session`, log a
     `seat-refused` event with the role and error (not `refused`, which is
     already a run outcome in `EXIT`), and send the plain message to a seat
     opened with no `resume`.
   - If that turn is refused too: `forget_session` again (the fresh seat has
     written its own id to `<role>.session`), then pause with
     `the {role} seat was refused twice: {error}`.
   - A crash on the fresh retry pauses with "failed twice" as now, keeping the
     fresh session.
4. **`pair/loop.py`, `Loop.work`.** The Issue says `Loop.run`, but the
   method that adds `RESTARTED` is `Loop.work`. Leave `st.in_turn` as it is after a refusal
   pause, so the next run still skips `absorb_developer`: the half-done
   seat's edits in the worktree are not the developer's. Instead, base the
   `RESTARTED` prefix on whether a session survives:
   `restarted = st.in_turn == role and bool(st.sessions.get(role) or
   self.saved_session(role))`. Keep the `absorb_developer` skip on
   `st.in_turn == role` alone.
5. **Status.** `just pair-status` prints `st.paused` as written, so the reason
   text in step 3 is enough. Nothing changes in `status`/`watch` (the pause
   kind stays `paused`).
6. **`pair/README.md`.** Next to "A seat that crashes is restarted once from
   its session id", add a sentence saying that a refused seat is restarted once
   with a fresh session, and that a second refusal pauses with no session
   kept, so the next run starts the seat fresh. The developer should look at
   the seat's instructions or the Issue. Add a `seat-refused` row to the
   event table, with the fields `role` and `error`. Leave it out of
   `watch.DEVELOPER`: one refusal does not stop the loop, and the pause after
   a second one is logged as `paused`.

### Tests (`pair/test_pair.py`)

Add a `REFUSED` marker next to `CRASH`. `FakeSeat.send` returns
`TurnResult(False, error=REFUSAL, refused=is_refusal(REFUSAL), ...)` for it,
where `REFUSAL` is the quoted error text. Taking `refused` through
`is_refusal` tests the matcher on the real text.

- `is_refusal` holds for `REFUSAL` and not for `"boom"`, a timeout message or
  `None`.
- A refused seat is restarted fresh. With `("primary", REFUSED), ("primary",
  quiet)`, `b.opened == [("primary", None), ("primary", None)]`, the second
  message does not start with `RESTARTED`, and a `seat-refused` event is
  logged.
- Two refusals pause the loop. The reason contains "refused", `primary` is not
  in `state().sessions`, and `.pair/primary.session` does not exist. The
  next run opens `("primary", None)` and its message does not start with
  `RESTARTED`.
- A refusal during a resumed turn: when the supervisor is killed mid-turn and
  the resumed turn is refused, the fresh restart's message has no
  `RESTARTED` prefix.
- The existing crash tests (`test_a_crashed_seat_restarts_once_from_its_session`,
  `test_a_seat_that_crashes_twice_pauses_the_loop`) pass unchanged.
- The status view test shows the refusal reason under `paused:`.

Then run `just gate pair`.

### Risks

- The match is on harness wording that may change. `is_refusal` is the one
  place to update it, and its docstring says so.
- `FakeSeat.__init__` writes `<role>.session` as soon as the seat opens, just
  as `ClaudeSeat` does. Tests of "no session kept" must therefore check the
  state after the pause and before the next seat opens.

## Notes for the next reader

- `Loop.work` keeps two separate questions apart. `interrupted` (`in_turn`
  names the seat) decides whether to skip `absorb_developer`.
  `Loop.has_session` decides whether the message carries `RESTARTED`. After a
  refusal pause the first is true and the second false.
- When the fresh restart after a refusal crashes instead, the loop pauses with
  "failed twice" and keeps the fresh session, which never saw the refused
  message. `Loop.turn` now stores the second failure's session id in both
  failure paths. Before this change it relied on the seat having written
  `<role>.session`.
- A crash whose restart (resumed from the session) is then refused pauses
  with "the <role> seat was refused on its restart" and drops the session,
  just as a second refusal does. Without that, the pause would keep a session
  whose history holds the refused message, which is the very failure this
  Issue fixes.
- The event reader the tests use moved onto `Bench.events`, so that tests
  outside `EventLogTest` can read the log.
