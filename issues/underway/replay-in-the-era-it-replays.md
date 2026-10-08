---
difficulty: medium
parent: pair-versus-single-seat
---

# Keep a replay's tree as the replayed Issue's own era would have it

A replay (`pair/replay.py`) runs today's loop against a clone reset to the
commit a landed Issue started from. Wherever today's loop writes into the
clone's tree, or calls into the clone's operator surface, in a form that the
clone's older code or checks do not accept, the replay fails for that reason
and not for anything the seats did. The first round of
`pair-versus-single-seat` (8 October 2026) hit it twice:

- **The state file, reached through the gate's call.** The loop keeps its
  runtime state in `.pair/state.json` inside the clone, now with the fields
  `models` and `mode`. In `squash-reverts-commits-on-main` (single), the
  supervisor gated with `just gate meta pair` (`gate` in `pair/pair.py`
  passes every target in one call). The clone's own `gate` recipe, from before
  `gate-takes-several-targets`, took one target, so `just` ran `gate meta` and
  then the `pair` recipe: the clone's old loop itself, which read the
  supervisor's `.pair/state.json`, met the `models` field its `State` lacks,
  and crashed before any pair test ran. The kick-back commit in the kept clone
  (`.pair/replays/squash-reverts-commits-on-main-single/`) records it.
  `squash-reverts-commits-on-main` and `fresh-seat-after-refusal` were sent
  back in both modes for this reason alone; the seats' note said "This needs
  you; another turn won't change it."
- **The notes.** Today's loop keeps a seat's own note in the Issue file and
  puts it back if a seat edits it (`Loop.keep_note`, `Loop.restore_notes`).
  The clone's older `.meta` checks predate `notes-rewrite-refused-citations`,
  so they do not skip quoted Pair notes. In `bootstrap-render-step` (two
  seats), a note quoted a class-and-slot citation the old check refuses, the
  seats could not remove it, and every gate failed on that one line until the
  round cap sent it back.

Either clash can strike any replay in either mode, so it adds noise to both
sides of the comparison and makes some results meaningless. The round was
stopped after 16 of its 20 replays.

## To reproduce

`just pair-replay squash-reverts-commits-on-main --mode single` from today's
`main`: the Issue changes `meta` and `pair`, the supervisor's gate fails in
the `pair` recipe on `.pair/state.json`, and the outcome is `sent-back`.
`just pair-replay bootstrap-render-step --mode pair` fails the same way on its
notes when a seat quotes a citation, which depends on what the seats write.

## Wanted

- **Every clash found and named.** Find each place today's loop writes into
  the clone or calls into it for its own purposes, not only the two above: at
  least its runtime state (`.pair/`), the turn notes and restored notes, the
  supervisor's gate lines (`Loop.keep_gate`), and its calls to the clone's
  recipes (`just gate`, `just setup`, `just deliver`, `just --summary` in
  `pair/pair.py`). The module docstring of `pair/replay.py` says, for each,
  how a replay keeps it out of the old code's way, or why it cannot reach it.
- **The gate is called in a form any era accepts.** A replay's gate (the
  `gate` seam `make_loop` gives the loop in `pair/pair.py`) runs `just gate
  <target>` once for each target and joins the results, so an older
  single-target recipe never runs a second recipe as a target. With no
  targets (the whole gate), it runs `just gate` once, as now. The gate passes
  only if every call passes, and its output is each call's output in turn,
  headed by the target it ran.
- **The notes stay where the seats see them, and out of the old checks.**
  Recommended: the replay's gate runs against a copy of the worktree in which
  the Issue file has the loop's own additions taken out (the `Pair notes`
  section and the supervisor's gate lines), so the clone's checks see the
  Issue file as its era wrote it, and the seats still read and write the notes
  as they do outside a replay. The other way, keeping the notes outside the
  Issue file during a replay, changes what the seats see and so what the
  comparison measures. The seats may choose otherwise if the code shows a
  reason; either way, record the choice in the docstring.
- **The runtime state is not read by the clone's code.** With the gate called
  one target at a time, nothing in the clone's era runs its loop, so moving
  `.pair/` out of the clone is not required; if a remaining path reads it,
  move the replay's runtime directory outside the clone.
- **The replayed Issue's own files** are otherwise exactly as they stood at
  its start commit, and the seats still see each other's notes in two-seat
  mode.
- **A clash shows in the outcome.** When a replay ends other than `landed` and
  its last `gated` event failed or could not run, the replay gates the clone
  once more at its `Replay <slug>` commit, with no seat's work, on that
  event's targets. If that also fails, the failure is not the seats':
  `outcome.json` says `clashed` instead of `sent-back` or `paused`, and the
  replay keeps that gate's output as `clash.txt` beside it. `pair/report.py`
  leaves `clashed` replays out of both modes' columns and counts them.

## How anyone will know it is done

Tests in `pair/test_pair.py`, over temporary repositories:

- A replay of an Issue that changes `pair/`, from a start commit whose
  `justfile` has a single-target `gate` recipe and a `pair` recipe that fails
  when it runs, gates each target on its own, never runs the `pair` recipe,
  and lands.
- A replay of an Issue whose seat writes a Pair note quoting text that the
  start commit's check refuses (a stub check failing on that text anywhere in
  the Issue file) gates past the note and lands, and the landed Issue file
  still holds the note.
- A replay whose seats' work fails a gate that the `Replay <slug>` commit also
  fails ends `clashed` with `clash.txt`; one whose work fails a gate the
  `Replay <slug>` commit passes ends `sent-back` as before.
- `pair/report.py` leaves a `clashed` replay out of the measures and reports
  how many there were per mode.
- `pair/README.md` says what a replay keeps outside the clone's tree and
  what `clashed` means.

## Out of scope

- Re-running the round, which the developer starts once this lands.
- Replaying another portfolio's Issues.
- Changing how the loop gates outside a replay: `gate` in `pair/pair.py`
  keeps passing every target in one call.
