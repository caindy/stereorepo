---
parent: pair-versus-single-seat
---

# Keep a replay's tree as the replayed Issue's own era would have it

A replay (`pair/replay.py`) runs today's loop against a clone reset to the
commit a landed Issue started from. Wherever today's loop writes into the
clone's tree in a form that the clone's older code or checks do not accept,
the replay fails for that reason and not for anything the seats did. The
first round of `pair-versus-single-seat` (8 October 2026) hit it twice:

- **The state file.** The loop keeps its runtime state in `.pair/state.json`
  inside the clone, now with the fields `models` and `mode`. For a replayed
  Issue that changes `pair/`, the gate runs that Issue's own older `pair/`
  code, which cannot load the newer file, so the `pair` gate crashed before
  its tests. `squash-reverts-commits-on-main` and `fresh-seat-after-refusal`
  were sent back in both modes for this reason alone; the seats' note said
  "This needs you; another turn won't change it."
- **The notes.** Today's loop keeps a seat's own note in the Issue file and
  puts it back if a seat edits it. The clone's older `.meta` checks predate
  `notes-rewrite-refused-citations`, so they do not skip quoted Pair notes. In
  `bootstrap-render-step` (two seats), a note quoted a class-and-slot
  citation the old check refuses, the seats could not remove it, and every
  gate failed on that one line until the round cap sent it back.

Either clash can strike any replay in either mode, so it adds noise to both
sides of the comparison and makes some results meaningless. The round was
stopped after 16 of its 20 replays.

## Wanted

- Nothing the loop writes for its own purposes lands in the clone's tree in a
  form the clone's own code or checks read: its runtime state (`.pair/`), the
  turn notes, and the supervisor's gate lines in the Issue file. Find every
  such write, not only the two above, and say in `pair/replay.py` how each is
  kept out of the old code's way. Moving the loop's runtime state outside the
  clone is one way for the state file. For the notes, one way is to keep them
  where the seats still see them but the clone's checks do not read them;
  another is to gate the clone's checks as they would have run on the Issue's
  own era, with nothing the newer loop added. Choose, and record the choice.
- The replayed Issue's own files are otherwise exactly as they stood at its
  start commit, and the seats still see each other's notes in two-seat mode.
- A replay that fails for a reason of this kind says so in its outcome,
  rather than reading as `sent-back` like an Issue the seats could not do.

## How anyone will know it is done

- A test replays, over a temporary repository whose older `pair/` code cannot
  read today's state file, an Issue that changes `pair/`, and its gate runs
  the old tests rather than crashing.
- A test replays an Issue whose seat writes a note quoting a citation that
  the older checks refuse, and the gate passes on the seats' own work.
- `pair/README.md` says what a replay keeps outside the clone's tree.

## Out of scope

- Re-running the round, which the developer starts once this lands.
- Replaying another portfolio's Issues.
