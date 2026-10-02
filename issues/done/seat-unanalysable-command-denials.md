---
difficulty: easy
---

# Count the shell commands a sandboxed seat is still refused

With Bash in Claude Code's sandbox (DR-302), a compound command built from
plain parts runs without a prompt. Claude Code still refuses, before running
it, a command it cannot analyse statically: a variable set from a command
substitution (`x=$(git rev-parse HEAD) && echo "$x"`), or a redirect to a path
built at run time (`echo hi > "$TMPDIR/f"`). In `-p` mode each refusal is a
denial, and the seat has to rewrite the command.

The `result` event of each turn carries `permission_denials`, a list of
`{tool_name, tool_use_id, tool_input}`. Nothing reads it yet, so nobody knows
whether these refusals cost the seats much work.

## Wanted

The count is per turn, so it belongs in the per-turn row of
`.pair/turns.jsonl` (`Loop.record` in `pair/loop.py`), not in
`.pair/events.jsonl`, whose events are transitions between turns.

- `TurnResult` (`pair/seats.py`) carries the turn's denials, read from
  `permission_denials` of every `result` event in the turn: a turn that
  settles background tasks sees more than one `result`, and its denials are
  all of them together, as `usage` already is.
- Each `turns.jsonl` row gains `denials`, the count, and `denied`, the list of
  denied commands: for a `Bash` denial its `tool_input.command`, for any other
  tool its `tool_name`. A turn with none records `0` and `[]`.
- `just pair-status` shows the count on each of its "last turns" lines. Rows
  written before this change have no `denials` key; `status()` shows them
  without the count rather than failing (it reads `row['cache_read']` by
  key today, so the new field must be read with `.get`).
- `pair/README.md`, where it describes `turns.jsonl`, says the row records
  denials.

## Out of scope

- Changing the sandbox's write confinement or the deny list.
- Finding or adopting a Claude Code setting that lets these commands run.
  That waits on the counts: once they show the refusals are frequent, a new
  Issue for the developer can take it up.
- Adding an event to `.pair/events.jsonl`, or an aggregate across turns.

## Done when

- A test in `pair/test_pair.py` drives a fake seat whose `result` event
  carries two `permission_denials` (one `Bash`, one other tool) and finds a
  `turns.jsonl` row with `denials: 2` and both entries in `denied`; a turn
  with no `permission_denials` key records `0` and `[]`.
- A test with a turn that settles background tasks finds the denials of both
  `result` events in the one row: `denials` is their total and `denied`
  lists the entries of both.
- `status()` output for such a row shows the denial count, and `status()`
  over a `turns.jsonl` row with no `denials` key still renders its line.

## The plan

The change crosses one seam: `ClaudeSeat.send` turns the stream into a
`TurnResult`, and `Loop.record` turns a `TurnResult` into a row. The seat
reduces each denial to one string, so the loop and `FakeSeat` never see
Claude Code's shape.

1. `pair/seats.py`
   - `TurnResult` gains `denied: list[str] = field(default_factory=list)`,
     one entry per denial, in the order they came.
   - A module function `denied(entry)` returns `tool_input.command` when
     `tool_name` is `Bash` and the command is a string, else `tool_name`
     (falling back to `"?"` if that is missing too). Its docstring records the
     shape of a `permission_denials` entry, as `is_refusal` records the shape
     of a refusal.
   - In `send`, next to the `usage` sum, a `denials: list[str]` collects
     `denied(e)` for each `e` in `event.get("permission_denials") or []` of
     every `result`, including one answered with `SETTLE`. The returned
     `TurnResult` carries it; the docstring's "`usage` is summed over every
     `result`" sentence names the denials too. The timeout and `_exited`
     results leave it empty: those turns write no row.
2. `pair/loop.py`
   - `record` adds `"denials": len(result.denied)` and
     `"denied": result.denied` to the row.
   - `status` appends `  denied {n}` to a "last turns" line, reading
     `row.get("denials")` and leaving it off when it is `None`, so older rows
     render as before. `status_view` passes rows through unchanged.
3. `pair/README.md`: the `turns.jsonl` sentence in the runtime-state paragraph
   says each row also has the turn's denied commands (`denials`, `denied`).
4. `pair/test_pair.py`
   - `result()` takes an optional `denials` list, emitted as
     `permission_denials`.
   - `ClaudeSeatTest`: a turn whose `result` carries a `Bash` denial
     (`{"tool_name": "Bash", "tool_input": {"command": "x=$(git rev-parse
     HEAD)"}}`) and a `Write` denial gives `turn.denied == ["x=$(git rev-parse
     HEAD)", "Write"]`; a plain `result` gives `[]`. The existing
     background-task test, given one denial on each of its two `result`s,
     asserts `turn.denied` holds both.
   - A loop test calls `Loop.record` with a `TurnResult` carrying two denials
     and with one carrying none, reads `loop.dir / "turns.jsonl"`, and finds
     `denials: 2` with both entries, then `0` and `[]`.
   - A status test writes two rows to `turns.jsonl` in the pair runtime
     directory, one with `denials: 2` and one without the key, and finds
     `denied 2` on the line of the row that has it, and the other line
     rendered without it.

Risk is small. The one guess is the entry's shape: if Claude Code nests the
command elsewhere, `denied` records `Bash` rather than failing, and the
counts stay right. Rows are append-only JSON, so readers other than `status`
(`status_json`, and anyone with `jq`) see the new keys without a change.

## Notes from the work

- The shape of a `permission_denials` entry is the Agent SDK's documented
  `SDKPermissionDenial`; no seat log in `.pair/` held a denial on
  2026-10-02 to confirm it. The first real denial in `.pair/<seat>.jsonl` is
  worth a glance: if `denied` shows `Bash` where a command was expected, fix
  `seats.denied`.
- The stand-in `claude`'s `result()` emits `permission_denials` only when
  given denials, so every other `ClaudeSeatTest` turn exercises a `result`
  without the key. A third case, a `Bash` denial with no `command`, checks
  the fallback to `Bash`.
- `seats.denied` takes any object: an entry that is not a dict reads as `?`,
  and a `tool_input` that is not a dict as the tool's name, so an entry of an
  unexpected shape is counted rather than raising inside `send` and losing
  the turn over a statistic.
- `status()` now reads `denials` with `.get`; the other fields of a
  "last turns" line are still read by key, as before.
