---
difficulty: medium
---

# Keep each turn's rationale and findings in the Issue file

A seat learns what the other did only from the diff of the working tree and
the Issue file. What the other seat said at the end of its turn goes to
`.pair/<seat>.log` and nowhere else. So a review that finds nothing to fix
leaves no trace: the next seat cannot tell a thorough check from a glance, and
must either re-derive it or take it on trust. The seats already write notes
into Issue files unprompted, but as recaps of what they did, which the diff
already shows.

The next reader needs two things the diff cannot give: why a change was made
the way it was, and what a review checked.

## What is wanted

- **The seats end each turn in a known shape.** The stage prompts ask a seat
  that changed the plan or the implementation to end its turn with its
  rationale: why this approach, what it considered and rejected, and what it
  is unsure of. They ask a seat reviewing the other's work to end with its
  findings: what it checked and how (the test it ran, the file it read, the
  case it tried), what it found wrong and why, and what it confirmed is
  right. Neither is a recap of the diff. Reasoning that belongs in a Decision
  Record or a docstring still goes there, as Journaling routes it. Four
  prompts already say otherwise and change with it: `primary.md` and
  `secondary.md` tell a seat that would change nothing to "say so briefly",
  which is exactly the untraceable review this Issue is about, and now ask for
  its findings instead, as does the line the loop adds to every turn's
  message (`loop.py`, "If you would change nothing, change nothing and say
  so."); `stage-in-progress.md` tells a seat to write what the
  next reader should know into the Issue file, which the closing message now
  carries, so it asks for that in the closing message; and the note the loop
  sends when the developer resumes a desk check (`Loop.resume`, "Their notes
  are in the issue file") now points at the developer's edits in the diff, so
  a seat does not answer the Pair notes instead. `stage-desk-check.md` says
  the same, but no turn runs in a `desk-check` stage, so the loop never loads
  it; it gets the same words and is otherwise left alone.
  `stage-flight-check.md` says a Flight file "ends in" `## Desk-check notes`,
  which stops being literally true once Pair notes can follow; it now says
  what the loop tests, that the last of its Desk-check sections is the notes.
- **The supervisor keeps the notes.** After each turn, the loop appends that
  turn's closing message (`TurnResult.text`) to the Issue file under
  `## Pair notes`, labelled by seat, stage and turn, and commits it as part of
  the turn. Its own append does not count as a change: a turn whose only
  change is its note is quiet. A grooming pass has no Issue file, and keeps no
  notes; nor does a turn whose Issue file is gone, which is sent back as now;
  nor does a turn that failed (`TurnResult.ok` false) or ended with no text.
  Quietness is judged before the note is appended, as `settle` judges it now.
- **A note cannot steer the loop.** The loop reads headings from the Issue
  file: `Needs elaboration` sends an Issue back, `The plan` finishes `todo/`,
  and the `Desk-check` sections drive a Flight's desk check. `board.section`,
  `board.last_section` and `board.last_of` match a heading at any level, and a
  bold lead such as `**The plan.**`, even when indented, so demoting a heading
  is not enough: the loop appends each note as a block quote (every line
  prefixed `> `), which none of them matches. The `## Pair notes` heading
  itself is not a name the loop reads, and closes the section above it, so the
  Flight's brief and desk-check notes read as before.
- **The other seat reads them in its diff**, since the Issue file changed. No
  message passes between the seats except through the file, and the notes
  land in `issues/done/` with the Issue.
- **The words follow:** `pair/README.md` says what a turn is told and what the
  loop keeps.

## Out of scope

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
- The stage prompts ask for rationale from a changing turn and findings from a
  reviewing one, no prompt or turn message still asks a seat to "say so" in
  place of its findings, or to write its notes into the Issue file itself, and
  the message that resumes a desk check points at the developer's edits.
- The pair tests cover each of these, and `just gate` passes.

## The plan

**Seams.** `pair/board.py` gets the pure text function; `pair/loop.py` calls it
between `settle` and `decide` in `Loop.work`, and changes the turn message and
the resume note; the prompts and `pair/README.md` change their words.

1. **`board.with_note(text, label, note) -> str`** (pure). Quote the note, with
   every line prefixed `> ` (a blank line becomes `>`), under a quoted bold
   label line, `> **primary · todo · turn 3**`. If the body has no
   `## Pair notes` heading, append one at the end of the file, followed by the
   quote. If it has one, insert the quote at the end of that section: before
   the first later line that `_HEADING` matches, at any level, including a
   bold lead, or at the end of the file. Inserting there rather than at the
   end of the file matters: a seat or the developer may write `## The plan`,
   `## Desk-check brief` or `## Desk-check notes` below Pair notes, and a note
   appended after one of those would read as part of that section's text
   (`section` runs to the next heading of the same level, and quoted lines are
   not headings). Separate notes with one blank line, so each is its own
   quote.
2. **`Loop.note(st, role, result)`**, called in `work` right after
   `quiet = self.settle(st, role)`. It does nothing for a grooming pass, a
   failed turn or an empty `result.text.strip()`, or when
   `board.read(self.wt, st.slug)` is None. Otherwise it rewrites the Issue file
   through `with_note`, labelled `role · st.stage · turn st.turn + 1` (the
   numbering `record` uses), and commits it as
   `{role}: note on {st.stage} turn {n}` with `Seat: {role}`. It then sets
   `st.head` and `st.seen[role]` to the new commit. That keeps
   `absorb_developer` from taking the commit for the developer's edit, keeps
   the seat's own note out of its next diff, and leaves it in the other
   seat's diff. `quiet` is already decided, so the note never breaks
   agreement, and `seats_used` is untouched.
3. **Words the seats are told.**
   - `primary.md` and `secondary.md`: replace "and say so briefly" with a
     closing shape. Your rationale for what you changed (why this way, what
     you rejected, what you are unsure of), and your findings on what you
     checked (how, what was wrong and why, what you confirmed), not a recap of
     the diff. Note that the loop keeps it in the Issue file. Both seats both
     change and check, so both prompts carry both halves.
   - `Loop.message` in `pair/loop.py`, the last line of every message: "If you would change
     nothing, change nothing, and end with your findings."
   - `stage-in-progress.md`: "Write what the next reader should know … in the
     issue file" becomes "in your closing message".
   - `Loop.resume`'s note: "Their notes are in the changes below." Replace
     `stage-desk-check.md`'s "the notes in the issue file" the same way.
   - `stage-flight-check.md`: "ends in a `## Desk-check notes` section"
     becomes "the last of its Desk-check sections is `## Desk-check notes`".
4. **`pair/README.md`**: a short paragraph where turns are described, saying
   what a turn ends with, that the loop keeps it under `## Pair notes` as a
   block quote, and that the note does not count as a change.

**Tests** (`pair/test_pair.py`). `FakeSeat` takes an optional third element in
a scripted turn, the closing text, and returns it as `TurnResult.text`. A
two-element turn returns no text, so every existing test keeps its commits and
assertions.
- `board.with_note` unit tests: the first note creates the heading; a second
  note lands under the first; with `## Desk-check notes` below Pair notes, the
  note goes above it and `board.section(..., "Desk-check notes")` is
  unchanged; a multi-line note with blank lines is fully quoted.
- Loop: two quiet turns with text advance `backlog` → `todo`, and the Issue
  file holds both notes once each, labelled; the secondary's message diff
  contains the primary's note and the primary's next diff does not repeat
  its own.
- Loop: a closing text of `# Needs elaboration\n\nx` in `backlog`, and
  `## The plan\n\nx` / `**The plan.**` in a quiet `todo` round, neither sends
  the Issue back nor finishes `todo/` (the stage's requirement message is sent
  instead).
- Loop: an existing Flight-check test, given closing text on its turns, still
  reaches `desk-check` with `section(body, BRIEF)` equal to what the seat
  wrote. The same goes for a Flight answering desk-check notes:
  `owed_children` still sees NOTES last.
- Loop: a turn with no text, and a grooming pass with text, add no note.
- Loop: after a noted turn, the next message carries no "The developer
  changed things" note, and no `developer: edits` commit appears: the note's
  commit must not look like a developer's edit to `absorb_developer`.

Run `just gate pair` while working, and `just gate` at the end.

**Risks.**
- The supervisor can die after the turn's commit and before `decide` saves
  the state. The saved state still has `in_turn` set, so the turn reruns as
  a restarted turn, as it does today; a note committed in between rides
  along and is not lost. Keep the note's commit inside that same unsaved
  window, after `settle` and before `decide`, and add no `save` between them.
  The cost is accepted, not avoided: the saved `st.head` predates the note,
  so the rerun's `settle` counts the dead run's note as a change (the rerun
  is not quiet even if the seat changes nothing), and the rerun appends a
  second note under the same label. Saving after the note would instead
  lose `decide` for that turn. A test is not needed; the README need not
  mention it.
- A closing message can be long. It goes in uncut: the reader wants it whole,
  and the Issue file is the record. `DIFF_LIMIT` already truncates the diff
  that carries it to the other seat.
- A seat may later edit or delete the Pair notes by hand. Nothing guards
  against that; it shows in the diff like any other edit.

### What changed from the plan

- **`board.append_under(text, name, block, *, nested)`** is the general
  insert: the end of the last section named `name`, as `section` reads it
  (`nested=True`) or up to the next heading or bold lead of any level
  (`nested=False`). `with_note` uses it with `nested=False`.
- **The `just deliver` line moved into the brief.** `deliver_flight` used to
  append it to the end of the Flight file, which `pair/README.md` called
  "after the brief". Once Pair notes can follow the brief, that put the line
  under the notes, so it now goes through `append_under(text, BRIEF, line)`,
  at the end of the latest brief, falling back to the end of the file when
  there is no brief. The README says "at the end of the latest brief".
- `stage-desk-check.md` got the resume note's words, as the Issue asks;
  removing it is `issues/backlog/unused-desk-check-prompt.md`.
- `FakeSeat` reads the closing text as an optional third element of a
  scripted turn (`Turn` in `test_pair.py`). The existing
  `test_notes_come_back_…` assertion on "ends in a `## Desk-check notes`
  section" now asserts the new Flight-check wording.
- **A seat's first turn on an Issue carries no diff.** `Loop.message` says
  "This is your first turn here" when `st.seen` has no mark for the seat, so
  the secondary's first turn (backlog, turn 2) gets the primary's first note
  only by reading the Issue file, not in its diff. Every later turn carries
  the other seat's note in its diff. "The other seat reads them in its diff"
  is therefore true from each seat's second turn on; the test asserts both
  halves.
