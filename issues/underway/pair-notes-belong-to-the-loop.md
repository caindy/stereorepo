---
difficulty: medium
---

# Keep the Pair notes section the loop's own, so a turn leaves one note

`Loop.keep_note` writes each turn's closing message under `## Pair notes`.
The in-progress prompt still tells the seat to "Write what the next reader
should know about this change in the issue file". That sentence has been in
the prompt since the loop arrived. It stayed when `pair-notes` was redone so
as not to change what the seats are told, after the first version's seat
instructions were refused by the model's safeguards (`6fd1ea94`). So a seat
sometimes writes its own note and sometimes does not, and when it does, the
turn leaves two.

The cost shows in fitch-mvp's `sqlite-reference-rerecord` (5 October 2026).
It was an `easy` Issue whose work was finished in its first in-progress turn,
and it was sent back when the stage ran past its round cap. The primary seat
wrote a note into the file on its turns, and the loop added another.
The secondary seat spent in-progress turns 2 and 6 deleting the duplicates.
A deletion is a change, so each of those turns reset the approvals to the
secondary alone, and the stage could not close. The primary found the cause in
turn 7, with one turn left. `priority-attribution-flip` shows the same thing
from another cause: turns 9 to 12 edited only notes, to remove a citation the
gate refused, and each edit was a change.

A seat's note is also not quoted, so it keeps none of the protection
`board.with_note` gives the loop's: a heading the loop reads, such as
`Needs elaboration`, steers the loop, and a `path:line` citation is not
rewritten.

## Wanted

- **The section is the loop's.** In `settle`, before it judges whether the
  turn was quiet, the loop puts the Issue file's `## Pair notes` section back
  as it stood at `st.head`. The section runs from that heading, at any level,
  to the next heading or bold lead that is not quoted, or to the end of the
  file. Every line the loop writes there is quoted, so an unquoted heading
  after the notes is the seat's own section, such as the `# Needs elaboration`
  a seat adds at the end of the file. It stays, with everything under it.
  If the seat added unquoted lines inside the section, the loop drops them.
  If the seat edited or deleted an earlier note, the loop restores it. If the
  file had no such section at `st.head` and the seat added one, the loop
  drops it. Everything outside the section stays as the seat left it.
- **Then judge the turn as now.** A turn whose only changes were inside the
  section is quiet after the restore, so a seat's own note, and any tidying of
  notes, never resets the approvals.
- **Then `keep_note` writes the note as now.** It does nothing new: the
  turn's closing message, quoted, labelled and with citations rewritten, is
  the only note the turn leaves.
- **Report it.** When the restore changed anything, the loop prints one line
  saying that it put back the seat's edits to the Pair notes, and records it
  in the turn's row in `turns.jsonl`. This shows whether seats still write
  notes, which a later Issue on the prompt can use.
- **The words follow.** The module docstring of `pair/loop.py` and
  `pair/README.md` say that the section is the loop's, and that a seat's edits
  there are put back.

## Out of scope

- Any change to what the seats are told, including the prompt sentence above.
  Changing seat instructions in this area is what the safeguards refused.
  Removing the sentence is its own Issue, with a fresh seat's first turn as
  its test.
- A note that quotes a citation the gate refuses (a decision id that does not
  exist yet, say), which fails the next gate. `board.with_note` rewrites line
  citations already, and doing the same for other refused citations is its
  own Issue.
- The round caps.

## Done when

`pair/test_pair.py` covers each case:

- A turn in which the seat appended its own text under `## Pair notes`, and
  changed nothing else, is quiet, and the file ends with the loop's one quoted
  note for that turn.
- A turn in which the seat deleted an earlier note, and changed nothing else,
  is quiet, and the earlier note is back.
- A turn in which the seat changed code and also wrote a note changes things.
  The code change is kept, and the seat's note is not.
- A seat's `# Needs elaboration` section added after the notes stays and
  sends the Issue back, as it does now.
- A seat's unquoted paragraph, without a heading of its own, added after the
  notes is dropped.
- A file that had no `## Pair notes` at `st.head`, to which the seat added one
  with a note under it, ends with only the loop's section.
- A turn that left the section alone reports nothing.
