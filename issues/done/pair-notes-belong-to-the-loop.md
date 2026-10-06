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
  to the next unquoted heading, or unquoted bold lead whose name the loop
  reads (`Needs elaboration`, `The plan`, and `BRIEF`, `NOTES` and
  `CHILDREN` in `pair/loop.py`, which are the `Desk-check` sections), or
  to the end of the file. Any other unquoted bold lead stays inside the
  section and is dropped with it: a seat that copies the loop's label,
  writing `**primary, in-progress turn 2**` on a line of its own, has
  written a bold lead (`_HEADING` in `pair/board.py` matches it), and
  ending the section there would keep exactly the note this Issue removes.
  Every heading and bold lead the loop writes there is quoted (its one
  unquoted line, `gate_line`, is neither), so an unquoted heading after
  the notes is the seat's own section, such as the `# Needs elaboration` a
  seat adds at the end of the file. It stays, with everything under it.
  If the seat added unquoted lines inside the section, the loop drops them.
  If the seat edited or deleted an earlier note, the loop restores it. If the
  file had no such section at `st.head` and the seat added one, the loop
  drops it. Everything outside the section stays as the seat left it.
  A file can hold more than one such section, because `board.with_note`
  opens a new `## Pair notes` whenever the last heading is another one,
  such as a `# The plan` written after the notes. The loop matches sections
  by order: the n-th in the seat's file takes the body of the n-th at
  `st.head`. A section beyond those at `st.head` is dropped with its body,
  and one the seat removed, heading and all, goes back at the end of the
  file. The file at `st.head` is read at the path `settle` keeps it at,
  `home(st.stage)`. A grooming pass has no Issue file, and a turn whose
  seat deleted the file is sent back by `decide`, so neither restores
  anything. If the seat committed its own edits, the restore is a
  further commit, made before the turn is judged.
- **Then judge the turn as now.** A turn whose only changes were inside the
  section is quiet after the restore, so a seat's own note, and any tidying of
  notes, never resets the approvals.
- **Then `keep_note` writes the note as now.** It does nothing new: the
  turn's closing message, quoted, labelled and with citations rewritten, is
  the only note the turn leaves.
- **Report it.** When the restore changed anything, the loop prints one line
  saying that it put back the seat's edits to the Pair notes, and records it
  in the turn's row in `turns.jsonl` as `"notes_restored": true` (`false`
  otherwise). This shows whether seats still write
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
  notes is dropped, and so is one under an unquoted bold lead that copies the
  loop's label, such as `**secondary, in-progress turn 3**`.
- A grooming pass, and a turn whose seat deleted the Issue file, restore
  nothing and behave as now.
- A file that had no `## Pair notes` at `st.head`, to which the seat added one
  with a note under it, ends with only the loop's section.
- A file with two `## Pair notes` sections at `st.head`, with `# The plan`
  between them, where the seat appended to the first and edited the plan,
  ends with both sections as they stood and the plan as the seat left it.
- A turn that left the section alone reports nothing, and its
  `turns.jsonl` row has `"notes_restored": false`.

## The plan

**Seams.** A pure text function in `pair/board.py`, one call in
`Loop.settle`, one field in `Loop.record`, tests in `pair/test_pair.py`,
and prose in `pair/loop.py`'s module docstring and `pair/README.md`.

1. **`board.restore_notes(before, after, stops) -> str`**, next to
   `with_note`. Both texts are whole Issue files, and `stops` is the
   section names a bold lead must carry to end a notes section. A helper
   splits a text's lines into notes sections and the rest. A section opens
   at an unquoted line `_HEADING` matches with the name `Pair notes`, at any
   level, and runs to the line before the next unquoted heading
   (`#` form, any name), the next unquoted bold lead whose name is in
   `stops` (case-insensitive, as `section` compares), or the end. Quoted
   lines never match, since `_HEADING` runs on the stripped line and a `>`
   comes first. The function then rebuilds `after`: the n-th section in
   `after` takes the lines of the n-th in `before`, sections beyond
   `before`'s count are dropped, and sections `before` has that `after`
   lacks are appended at the end, each after a blank line. It returns
   `after` unchanged when the sections already match, so callers can
   compare. `board` cannot import `loop`, so the stop names come in as an
   argument rather than as `BRIEF`, `NOTES` and `CHILDREN`.
2. **`Loop.settle`** (as built, through a method of its own,
   `Loop.restore_notes`): after the stray-file move and before
   `board.head_and_dirty`, when the stage is not `GROOMING`, read the file
   at `st.head` with `git show st.head:issues/<home(st.stage)>/<slug>.md`.
   If that fails (the file did not exist there) use `""`, so a section the
   seat added is dropped. If the file is missing from the working tree,
   restore nothing (`decide` sends the turn back). Otherwise write
   `restore_notes(before, current, NOTE_STOPS)` back when it differs, and
   `self.say(...)` one line that the seat's edits to the Pair notes were
   put back. `NOTE_STOPS` is a constant in `pair/loop.py`:
   `("Needs elaboration", "The plan", BRIEF, NOTES, CHILDREN)`. The existing
   `add -A` and leftover commit then carry the restore, also when the seat
   committed its note itself, so no extra commit is needed. `quiet` is
   then judged from `st.head` to the new head as now, and a turn whose
   seat touched only notes yields an empty diff and counts as quiet.
3. **Report**: `settle` returns `(quiet, restored)`. The one caller, `run`,
   passes `restored` to `record` as a keyword with a default of `False`,
   so the two direct calls in `TurnLogTest` stand, and `record` writes
   `"notes_restored"` into the row. `status`'s reading of rows needs no
   change.
4. **Words**: the paragraph about `keep_note` in the module docstring and
   the matching paragraph in `pair/README.md` gain a sentence: the section
   is the loop's, and `settle` puts back whatever a seat changed there
   before judging the turn.

**Tests.**

- `BoardTest`: `restore_notes` unit cases. A seat line added inside a
  section is dropped. An edited or deleted note comes back. A
  `# Needs elaboration` after the notes stays. An unquoted paragraph after
  the notes is dropped, and so is one under `**secondary, in-progress turn
  3**`. A section absent from `before` is dropped. Two sections with
  `# The plan` between them restore by order and keep the plan's edit. A
  section deleted heading and all goes back at the end. Unchanged sections
  return `after` as it is.
- `PairNotesTest`, through `Bench` and `FakeSeat`, one per case in "Done
  when". Use `append` for a seat's note, `unappend` for a deleted note,
  `write` for a code change, and a bare `x` with no notes for the case of
  an added section. Assert `quiet` and `notes_restored` from
  `turns.jsonl`, the body from `issue_in_worktree`, and, for
  `# Needs elaboration`, that the Issue is back on `main` in
  `issues/backlog/`. The existing `test_a_grooming_pass_keeps_no_note` and
  `test_a_turn_that_lost_its_issue_file_keeps_no_note` cover the two
  no-restore cases once they also assert that no turn row has
  `notes_restored` true.
- One existing test changes with the rule:
  `test_the_other_seat_sees_a_note_in_its_diff_and_its_author_does_not`
  in `PairNotesTest` has the secondary seat say "Theirs." and append
  `\nMore.\n`, which lands after the primary's note and is now dropped,
  so the turn turns quiet and the stage closes a turn earlier than the
  script expects. Make that change `write("a.txt", "more\n")` so the
  turn still changes things outside the notes. The other `Says` tests
  write nothing unquoted after a note, and a `FakeSeat` turn without
  `Says` leaves no note, so no other test meets a notes section.

**Risks.**

- *A seat's legitimate section after the notes that starts with a bold lead
  not in `stops`* is dropped. That is the price the grooming chose to keep
  copied labels out. A `#` heading is always safe.
- *A heading inside a fenced code block in a seat's note*, unquoted, would
  end the section early and keep the rest. That is rare enough to leave
  alone; the helper is not a Markdown parser.
- *The gate's line*: `Loop.keep_gate` appends `gate_line` unquoted, and
  usually inside a `## Pair notes` section (see
  `test_a_note_after_the_line_stays_under_the_same_pair_notes`). It is
  neither a heading nor a bold lead, so it ends nothing. `keep_gate` moves
  `st.head` past it, so it is part of `before` and comes back like a note
  if a seat edits it. The helper must not tell the loop's lines from the
  seat's by quoting. It compares only with `st.head`.
- *The absorbed developer edits*: `absorb_developer` moves `st.head` past the
  developer's edits before the turn, so a note the developer edits between
  turns is the baseline and is not reverted.
- *Line endings and the trailing newline*: rebuild with `"\n".join` and keep
  `after`'s trailing newline, so a no-op restore is byte-identical and does
  not make a quiet turn look changed. As built, when the last notes
  section ends the file both before and after the turn, the file also ends
  with `before`'s trailing whitespace, so blank lines a seat added after the
  last note are put back too and the turn stays quiet. Likewise a section
  that something follows both before and after the turn comes back whole,
  its trailing blank lines included.

## Pair notes

> **primary, backlog turn 1**
>
> I've groomed `issues/underway/pair-notes-belong-to-the-loop.md` and left `difficulty: medium` as it was. The change is one rule added to `settle` in `pair/loop.py`, plus tests in `pair/test_pair.py`, so it can be done in one piece and needs no hand check by the developer. Nothing has been run or tested, since this was grooming only.
>
> The Issue was already clear on what is wanted, what is out of scope and how to tell it is done. I checked it against `settle` and `keep_note` in `pair/loop.py` and `with_note` in `pair/board.py`, and filled two gaps:
>
> - **More than one notes section:** an Issue file can have several `## Pair notes` sections. That's because `board.with_note` starts a new one whenever the file's last heading is something else, such as a `# The plan` a seat wrote after the notes. I added how the restore handles this:
>   - Sections are matched in order, and each takes back its body as it stood at the start of the turn (`st.head`).
>   - A section the seat added is dropped, body and all.
>   - A section the seat deleted completely goes back at the end of the file.
>   - The old copy of the file is read from where `settle` keeps it, the stage's folder (`home(st.stage)`).
>   - If the seat committed its own edits, the restore is a further commit, made before the turn is judged.
> - **The report:** I named the field the loop writes in the turn's `turns.jsonl` row: `"notes_restored": true`, or `false` when nothing was put back.
>
> I also added two test cases under "Done when": a file with two notes sections and a plan between them, and the `false` value for a turn that left the notes alone.

> **secondary, backlog turn 2**
>
> I checked my partner's grooming against `settle`, `keep_note` and `record` in `pair/loop.py` and `with_note` and `_HEADING` in `pair/board.py`. What it says about the code is accurate, and I kept `difficulty: medium`: the work is one restore step in `settle` plus tests, and it doesn't need a check by hand. Nothing was run, since this was grooming only. I fixed one real gap and wrote down two edge cases, all committed in the Issue file.
>
> - **The gap:** the Issue said the notes section ends at the next unquoted heading or bold lead. But a seat that copies the loop's label onto a line of its own, such as `**primary, in-progress turn 2**`, has written a bold lead (`_HEADING` matches it). The section would end there, and the loop would keep exactly the seat note this Issue is meant to remove. Now a bold lead only ends the section when it is a name the loop reads, such as `Needs elaboration` or `The plan`. Any other unquoted bold lead is dropped with the section. I added a test case for this under "Done when".
> - **Two edge cases now stated:** a grooming pass has no Issue file, and a turn whose seat deleted the file is already sent back by `decide`. In both, the loop restores nothing and behaves as it does now. There is a test case for this too.

> **primary, backlog turn 3**
>
> I kept both of my partner's changes and made one small edit. `difficulty:` stays `medium`.
>
> - **The bold-lead fix is right.** A seat that copies the loop's label onto a line of its own, such as `**primary, in-progress turn 2**`, writes something the loop's heading pattern counts as a bold lead. If the notes section ended at any bold lead, that seat note would survive the restore, which is the opposite of what the Issue wants.
> - **The cases with no Issue file are right too.** A grooming pass has no Issue file, and a turn whose seat deleted the file is already sent back by `decide`, so the loop restores nothing in either.
>
> **My edit:** the fix said a bold lead ends the section when its name is one the loop reads, "or another name `board` or `loop` looks up". That left whoever plans it to go and find those names. I checked the code and it reads exactly five: `Needs elaboration`, `The plan`, and the three desk-check sections (`Desk-check brief`, `Desk-check notes` and `Desk-check children`, held as `BRIEF`, `NOTES` and `CHILDREN` in `pair/loop.py`). The Issue now lists them, and I rewrapped the paragraph's long line.
>
> Nothing was run or tested, since this was grooming only.

> **secondary, backlog turn 4**
>
> I'm leaving the Issue as it is. I checked my partner's edit against the code, and the list of five section names is complete and correct.
>
> - **Where the loop reads sections:** `pair/board.py` and `pair/loop.py` look up sections by name in only a few places. Those are `needs_elaboration` (`Needs elaboration`), one check of `The plan`, and the desk-check checks.
> - **The desk-check names:** those checks use the constants `BRIEF`, `NOTES` and `CHILDREN` in `pair/loop.py`, which hold `Desk-check brief`, `Desk-check notes` and `Desk-check children`.
>
> That's five names in all, matching the Issue. `difficulty: medium` still fits, and nothing was run, since this was grooming only.

> **primary, todo turn 1**
>
> I've added a `## The plan` section to `issues/todo/pair-notes-belong-to-the-loop.md`, placed above `## Pair notes`. Nothing is implemented or run yet. Planning found nothing that stops the Issue being done as written, so there is no `# Needs elaboration` section.
>
> **How the change is made:**
>
> 1. **A text function in `pair/board.py`.** A new `restore_notes(before, after, stops)` takes the Issue file as it stood at the start of the turn and as the seat left it. It finds the `Pair notes` sections in each and gives each section of the seat's file the content its counterpart had before, matched by order:
>    - A section the seat added is dropped.
>    - A section the seat deleted outright goes back at the end of the file.
>    - The five section names that end a notes section come in as the `stops` argument, because `board` cannot import the constants from `pair/loop.py`.
> 2. **One call in `Loop.settle`.** Before the loop commits the seat's leftovers, it reads the file as it stood at the start of the turn (`git show`) and writes the restored text back if it differs. It reads an empty file if none existed then, so a section the seat added is dropped. It restores nothing in a grooming pass or when the seat deleted the file. The existing leftover commit carries the restore, even when the seat committed its own note, so no extra commit is needed. A turn that only touched notes then shows no change and counts as quiet.
> 3. **The report.** `settle` returns `(quiet, restored)`. `run` passes `restored` on to `record`, which writes `notes_restored` in the turn's row in `turns.jsonl`. It defaults to `False`, so the existing direct calls in `TurnLogTest` still work.
> 4. **The words.** The module docstring of `pair/loop.py` and `pair/README.md` each gain a sentence saying the section is the loop's and that a seat's edits there are put back.
>
> **Tests:** unit tests for `restore_notes` in `BoardTest`, and one loop-level test in `PairNotesTest` per case under "Done when". Two existing tests, for a grooming pass and for a turn that lost its Issue file, gain an assertion that nothing was restored.
>
> **Risks:**
> - A section a seat adds after the notes is dropped if it starts with a bold lead whose name the loop doesn't read. A `#` heading always survives.
> - A heading inside a fenced code block in a seat's note would end the section early, so the rest of that note would be kept.
> - If a restore that changes nothing doesn't give back exactly the same text, including the trailing newline, a quiet turn would count as a change. The plan says how to avoid that.

> **secondary, todo turn 2**
>
> I checked my partner's plan against the code and found one existing test it would break without saying so. I added that to the plan; nothing is implemented or run yet.
>
> The plan's other claims hold up:
> - **Where it plugs in:** `settle` is called once, from `run`, before `keep_note`, and `record` is called directly twice in `TurnLogTest`. `home()` puts a backlog or Flight check Issue in `underway/`, so the plan reads the file at the start of the turn from the right path.
> - **Test helpers:** `append`, `unappend`, `write`, `Bench`, `FakeSeat`, `PairNotesTest`, `BoardTest` and `issue_in_worktree` all exist as the plan names them.
>
> **What I added:** `test_the_other_seat_sees_a_note_in_its_diff_and_its_author_does_not` in `PairNotesTest` has the secondary seat append `More.` right after the primary's note. Under the new rule that line falls inside the notes and is dropped. The turn then counts as quiet, and the stage closes a turn earlier than the test's script expects. The plan now says to have that turn write to `a.txt` instead, so it still changes something outside the notes.
>
> I checked the other existing tests and none should be affected. A scripted seat only leaves a note when the test gives it a closing message, and the tests that do never write unquoted text after a note.

> **primary, todo turn 3**
>
> I kept my partner's change and added one risk to the plan.
>
> **My partner's change is right.** In `test_the_other_seat_sees_a_note_in_its_diff_and_its_author_does_not`, the secondary seat adds `More.` straight after the primary's note. Under the new rule that line falls inside the notes and is dropped, so the turn would count as quiet and the test would break. Having that turn write to `a.txt` instead keeps it a real change. I also checked the two desk-check tests that give a seat a closing message: one adds a `## Desk-check brief` heading, which ends the notes and stays, and the other leaves a note only. Neither should be affected.
>
> **What I added: the gate's line.** When the gate closes `in-progress/`, the loop's `keep_gate` adds a line to the Issue file that is *not* quoted ("Gated by the supervisor at …"). It usually sits inside `## Pair notes`. So the Issue's claim that every line the loop writes there is quoted is not quite true. The plan still works:
> - `keep_gate` commits the line and moves the starting point of the next turn (`st.head`) past it, so it counts as part of the section as it stood.
> - If a seat edits it, it is put back like any note.
>
> The new risk tells whoever implements this to compare the section only with how it stood at the start of the turn. It must not treat every unquoted line as the seat's.
>
> Nothing is implemented or run yet.

> **secondary, todo turn 4**
>
> My partner's new risk is right, and I fixed one sentence in the Issue that it showed to be wrong. Nothing is implemented or run yet.
>
> **The risk checks out.** When the gate closes `in-progress/`, `keep_gate` in `pair/loop.py` adds a line to the Issue file that is not quoted, usually inside `## Pair notes`. It commits that line and moves `st.head` past it. So the line counts as part of the notes as they stood at the start of the turn, and if a seat edits it, it is put back like any note.
>
> **The fix:** the "Wanted" section still said every line the loop writes in the notes is quoted, and that line isn't. What actually matters is that every heading and bold lead the loop writes there is quoted, because only those can end the notes section. The gate's line is neither, so I reworded the sentence to say that.

> **primary, todo turn 5**
>
> I'd change nothing. My partner's rewording in "Wanted" is accurate: what has to be quoted is every heading and bold lead the loop writes in the notes, because only those could end the section. The gate's line is neither. The plan already handles that line, so it's ready to implement as it stands.

> **primary, in-progress turn 1**
>
> I've built the change as planned, and a seat's own edits to `## Pair notes` are now put back before the loop judges its turn. `just gate pair` (288 tests) and `just gate meta` both pass, and the work is committed.
>
> **What changed:**
> - **The text function:** `restore_notes` in `pair/board.py` takes the Issue file as it stood at the start of the turn and as the seat left it. It gives the notes back their earlier text, matched by order, and keeps the spacing.
>   - A notes section the seat added is dropped. One it deleted outright goes back at the end of the file.
>   - When nothing differs it returns the seat's text unchanged, so a quiet turn can't turn into a change.
> - **The loop:** `settle` in `pair/loop.py` now calls a new method, `Loop.restore_notes`, before it commits the seat's leftovers.
>   - That method reads the file as it stood at the start of the turn with `git show`, or reads it as empty if it didn't exist then.
>   - It skips a grooming pass and a turn whose seat deleted the Issue file.
>   - When it puts something back, the loop prints one line saying so.
>   - The five names that end a notes section are a new constant, `NOTE_STOPS`, in `pair/loop.py`.
> - **The report:** `settle` now returns whether it restored anything, and `record` writes that into each turn's row in `turns.jsonl` as `notes_restored`. It defaults to `False`, so the existing direct calls in `TurnLogTest` still work.
> - **Tests:** `pair/test_pair.py` has two new unit tests in `BoardTest` and seven loop-level tests in `PairNotesTest`, one per case under "Done when".
>   - The grooming, lost-file and first notes tests now also check that nothing was restored.
>   - `test_the_other_seat_sees_a_note_in_its_diff_and_its_author_does_not` now writes to `a.txt`, as my partner planned, because its old edit to the notes is now put back.
> - **The words:** the module docstring of `pair/loop.py` and `pair/README.md` say the section is the loop's and that a seat's edits there are put back.
>
> The plan held. The only update to it says that the restore lives in its own method, `Loop.restore_notes`, rather than inline in `settle`. The note for the next reader goes into the Issue file as this turn's closing note. I found no work outside this Issue to add to the backlog.

> **secondary, in-progress turn 2**
>
> I went through my partner's implementation and it does what the plan says. I fixed one gap where a seat's edit to the notes still counted as a change, and added two missing test checks. `just gate pair` (288 tests) and `just gate meta` both pass, and the work is committed.
>
> - **The gap:** if a seat only added blank lines after the last note at the end of the file, the restore left the file as the seat wrote it. That turn then counted as a change and reset the approvals, though the Issue says an edit inside the notes alone should leave a turn quiet. `restore_notes` in `pair/board.py` now also puts back how the file ended when the turn began, in that case. There's a new unit assertion for it, and the plan's risks section says how it was built.
> - **The printed line was untested:** the Issue says the loop prints one line when it puts notes back, and nothing at all otherwise. The tests now check both: the line is printed when a seat's note is dropped, and nothing about the notes is printed when the seat left them alone.
> - **Tidying:** I rewrapped an overlong line my partner's edit left in `pair/README.md`.
>
> One weakness from the plan is still there. If a seat writes a note containing an unquoted code block with a `#` line in it, that line ends the notes section early. The rest of the seat's note is then kept, and its opening fence is dropped. The plan judged this rare enough to leave.

> **primary, in-progress turn 3**
>
> I kept all of my partner's changes and closed one more gap of the same kind. `just gate pair` (288 tests) and `just gate meta` both pass, and the work is committed.
>
> **My partner's changes hold up:**
> - **Blank lines at the end of the file:** if a seat only added blank lines after the last note, the turn used to count as a change. Now the file ends as it did when the turn began, so that turn stays quiet.
> - **The printed line:** the tests now check that the loop prints its line when it puts notes back, and prints nothing about the notes when the seat left them alone.
> - **The README:** the line rewrap is fine.
>
> **What I fixed:** the same thing could still happen in the middle of the file. Blank lines a seat added at the end of a notes section that something follows, such as the space before `# The plan`, stayed as the seat left them, so the turn counted as a change. Now, when something follows a section both before and after the turn, `restore_notes` in `pair/board.py` puts it back whole, blank lines included. Where a section moved to or from the end of the file, it keeps the seat's spacing as before. I added a unit case to `BoardTest` and updated the docstring and the plan's risks section to match.
>
> One weakness from the plan remains. An unquoted heading line inside a code block in a seat's own note still ends the notes section early, so the rest of that note is kept. The plan judged this rare enough to leave.

> **secondary, in-progress turn 4**
>
> I'm leaving this turn's work as it is. I read my partner's fix and checked each case it touches; I didn't re-run the gates, and my partner reports both passing.
>
> - **The fix is right.** When something follows a notes section both before and after the turn, `restore_notes` in `pair/board.py` now puts the whole section back, blank lines included. So a seat that only added or removed blank lines before something like `# The plan` no longer counts as having changed anything.
> - **Sections that moved to or from the end of the file still keep the seat's spacing.** For example, if a seat adds a `# Needs elaboration` after notes that used to end the file, the notes come back as they were and the seat's spacing before its new section stays.
> - **The rest is unchanged:** a notes section the seat added is still dropped, one it deleted still goes back at the end, and the new unit case in `BoardTest` covers the fix. The docstring and the plan's risks section match the code.
>
> The one known weakness is unchanged: an unquoted `#` line inside a code block in a seat's own note still ends the notes section early, so the rest of that note is kept.

Gated by the supervisor at 19:50: `meta`, `pair`; 97 steps passed.
