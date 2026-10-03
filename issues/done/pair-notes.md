---
difficulty: medium
---

# Keep each turn's closing message in the Issue file

A seat learns what the other did only from the diff of the working tree and
the Issue file. What the other seat said at the end of its turn goes to
`.pair/<seat>.log` and nowhere else. So a review that finds nothing to fix
leaves no trace: the next seat cannot tell a thorough check from a glance.

The seats already end every turn with a closing message. The loop keeps it
where the other seat will read it, and nothing about what the seats are told
changes.

## What is wanted

- **The supervisor keeps the notes.** After each turn, the loop appends that
  turn's closing message (`TurnResult.text`) to the Issue file under
  `## Pair notes`, labelled by seat, stage and turn, and commits it as part of
  the turn. Its own append does not count as a change: a turn whose only
  change is its note is quiet. A grooming pass has no Issue file, and keeps no
  notes; nor does a turn whose Issue file is gone, which is sent back as now,
  nor a turn whose closing message is empty.
- **A note cannot steer the loop.** The loop reads headings from the Issue
  file: `Needs elaboration` sends an Issue back, `The plan` finishes `todo/`,
  and the `Desk-check` sections drive a Flight's desk check. `board.section`,
  `board.last_section` and `board.last_of` match a heading at any level, and a
  bold lead such as `**The plan.**`, even when indented, so demoting a heading
  is not enough: the loop appends each note as a block quote (every line
  prefixed `> `), which none of them matches. The `## Pair notes` heading
  itself is not a name the loop reads, and closes the section above it, so the
  Flight's brief and desk-check notes read as before.
- **A note never lands inside another section.** The loop appends at the end
  of the file. When the file's last heading or bold lead, at any level, is
  already `## Pair notes`, the note goes under it; otherwise the loop opens a fresh
  `## Pair notes` heading first. So a note that follows a developer's
  `## Desk-check notes` or a seat's `## The plan` is not read as part of it.
- **The other seat reads them in its diff**, since the Issue file changed. No
  message passes between the seats except through the file, and the notes
  land in `issues/done/` with the Issue.
- **The words follow:** `pair/README.md` says what the loop keeps.

## Out of scope

- Any change to what the seats are told: the files under `pair/prompts/` and
  the turn message `Loop.message` builds stay as they are.
- Judging whether a review's findings are substantive; that belongs to the
  pair-versus-single-seat evaluation on the roadmap.

## Done when

- Each turn's closing message appears once under `## Pair notes` in the Issue
  file, labelled by seat, stage and turn.
- A turn whose only change is its appended note is quiet, and a stage still
  advances on two such turns.
- A closing message containing `# Needs elaboration`, `## The plan` or
  `**The plan.**` neither sends the Issue back nor finishes `todo/`, and a
  Flight whose check turns leave notes still reaches its desk check with its
  brief intact.
- A note appended after a `## Desk-check notes` section sits under its own
  `## Pair notes` heading, and `board.last_section` of the desk-check notes
  returns them without the note.
- The pair tests cover each of these, and no file under `pair/prompts/`
  changes.

## The developer's decision (2026-10-02)

The first implementation landed as `9f129a71` and was reverted (`6fd1ea9`):
its new instructions to the seats about their closing messages made the
model's safeguards refuse a fresh seat's first turn. Plainer wording was
tried and refused the same way. So this Issue keeps only the supervisor's
part, which tells the seats nothing new.

`9f129a71`'s changes to `pair/board.py` may be reused: read them with
`git show 9f129a71 -- pair/board.py`. Write the change to `pair/loop.py` and
the tests afresh. Do not open `9f129a71`'s changes to `pair/loop.py`,
`pair/prompts/` or `pair/test_pair.py`, which carry the refused wording, and
do not quote or rewrite that wording.

## The plan

**Seams.** `pair/board.py` gains the note writer; `Loop.run`'s turn loop in
`pair/loop.py` (between `settle` and `record`, around line 773) calls it;
`FakeSeat` in `pair/test_pair.py` learns to return a closing message;
`pair/README.md` says what the loop keeps.

1. **`board.with_note(text, label, note) -> str`** and `PAIR_NOTES = "Pair
   notes"`. Quote the label (`**primary, todo turn 3**`), a blank line and
   every line of the note with `> ` (blank lines become `>`). If the last line
   of `text` that `_HEADING` matches, at any level or as a bold lead, is named
   `Pair notes`, append the quote at the end of the file after one blank line;
   otherwise append `## Pair notes` first. The reverted `with_note` may be
   read for its quoting, but not its `append_under`: that inserts the note
   before a later section rather than at the end of the file, which the
   groomed rule rejects, so it is not reused.
2. **`Loop.keep_note(st, role, result)`**, called right after `settle`.
   It returns at once for a grooming pass, an empty `result.text`, or an Issue
   file that is gone (`board.read` is None; `decide` then sends it back as
   now). Otherwise it writes `with_note` to the Issue file at its home stage,
   commits it as `{role}: note on {stage} turn {n}` with `Seat: loop`, where
   `n` is `st.turn + 1`, the number `record` logs (`decide` increments
   `st.turn` only afterwards), and
   sets `st.head = st.seen[role]` to the new commit. `quiet` is already
   decided by `settle` from the seat's own changes, so the note cannot make a
   turn count as a change, and `seats_used` is untouched. Moving `st.head`
   keeps `absorb_developer` from reading the note commit as a developer edit;
   moving `st.seen[role]` keeps a seat from being shown its own note, while
   the other seat's `st.seen` still predates it, so `message` puts the note in
   its diff.
3. **`FakeSeat.send`**: a scripted turn may be `(role, Says(text, action))`,
   a small test-only wrapper; `send` runs `action` and returns `text` as the
   turn's `TurnResult.text`. Any other action gives `""`. Do not take the
   text from an action's return value: existing actions such as
   `lambda wt: path.write_text(...)` return values by accident, and one that
   happened to return a string would quietly give an old test a note.
4. **README**: in the turn description of "How an Issue moves", saying the loop appends each closing message,
   quoted, under `## Pair notes` in the Issue file and commits it.

**Tests** (`pair/test_pair.py`), each driven through `Loop.run` with scripted
closing messages:

- Two turns with messages: the Issue file holds both, once each, under one
  `## Pair notes` heading, labelled with seat, stage and turn. On a later
  turn the other seat's message shows the note in its diff, and the author's
  does not. (Corrected while implementing: a seat's first turn in a stage is
  sent no diff at all, so the secondary's first turn reads the note in the
  file, not in a diff; the diff check is on the primary's second turn.)
- Two quiet turns that each leave a message advance `backlog` to `todo`, and
  `turns.jsonl` records both as quiet.
- A message holding `# Needs elaboration`, `## The plan` and
  `**The plan.**`: the Issue is not sent back, and in `todo` two quiet turns
  still stop with the "write the plan" note rather than advancing.
- A Flight check whose turns leave notes and write a brief lands at its desk
  check, and `board.last_section(body, BRIEF)` equals the brief alone (extend
  the shape of `test_a_brief_lands_the_flight_at_its_desk_check_...`).
- Unit tests of `with_note`: after `## Desk-check notes` it opens its own
  `## Pair notes`, and `last_section(..., "Desk-check notes")` is unchanged;
  after an existing trailing `## Pair notes` it adds no second heading.
- An empty message leaves the file unchanged and makes no commit.

**Risks.**
- `owed_children` asks for the children section "at the end of the Flight
  file"; its check uses `last_of` over the
  three desk-check names, which a quoted note never matches, so a trailing
  `## Pair notes` does not break it. The Flight test above covers it.
- A turn now makes up to two commits; the landing squash takes its `Seat:`
  trailers from `st.seats_used`, not from commits, so attribution is
  unchanged.
- A crash after the note commit but before `decide` saves the state leaves
  `st.in_turn == role` and the old `st.head` on disk, so the restarted turn
  re-runs and `settle` counts the note commit as a change. That costs one
  extra turn, not a wrong advance; accept it rather than adding a second
  save, and do not test it.
- Per the developer's decision, nothing under `pair/prompts/` changes, and
  the reverted `loop.py`, prompt and test changes are not opened.

## Implementation notes

- `board.with_note` and `Loop.keep_note` are as planned; `keep_note` runs
  between `settle` and `record` in `Loop.run`. The note commit's subject is
  `{role}: note on {stage} turn {n}`, with `Seat: loop`.
- The README needed no change to the `.pair/` paragraph, since the notes live
  in the Issue file, not in `.pair/`; the paragraph after the turn
  description in "How an Issue moves" says what the loop keeps.
- Tests: `PairNotesTest` (kept once and quiet; diff seen by the other seat
  only; headings in a note steer nothing; an empty message, a turn that lost
  its Issue file, and a grooming pass each leave no note),
  `FlightCheckTest.test_notes_from_a_flight_check_leave_its_brief_intact`,
  and two `BoardTest` cases for `with_note`'s placement, including a later
  `###` heading and a bold lead.
- The seat's own first turn in each stage still gets no diff, so the other
  seat meets the first note of a stage in the Issue file, not a diff. This
  Issue changes nothing about what the seats are sent, so that stays.
