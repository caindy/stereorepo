---
difficulty: medium
waits_on: [pair-notes-belong-to-the-loop]
---

# Keep the note a seat writes in the Pair notes as its turn's note

`pair/prompts/stage-in-progress.md` tells the seat to "Write what the next
reader should know about this change in the issue file, not in commit
messages". `pair-notes-belong-to-the-loop` made the Pair notes the loop's:
`Loop.restore_notes` in `pair/loop.py` puts back whatever a seat writes
there, and `Loop.keep_note` always writes the turn's closing message as the
note. So a seat that follows the prompt has its note discarded.

The developer's intended design, from the desk check below: the seat writes
its own note when it can, and the loop falls back to the closing message
only when the seat wrote none. This Issue first set out to delete the
prompt sentence; the developer sent that back, and the sentence stays.

## Wanted

- After a turn, the loop finds what the seat added to the Pair notes since
  the head the turn started from: lines after the end of a notes section, or
  a notes section of its own. If it added something, that is the turn's note,
  written back the way a closing message is (`board.with_note`: quoted,
  labelled, `path:line` citations rewritten), and the closing message is not
  written as well. If it added nothing, the closing message is the note.
- A seat's edits to earlier notes are still put back.
- A turn whose only change is in the Pair notes is still quiet.
- `turns.jsonl` keeps `notes_restored` and gains `note_from`: `"seat"`,
  `"message"`, or `null` when no note was kept.
- `pair/README.md` describes how a turn's note is chosen.

## Out of scope

- Any prompt change: `pair/prompts/` stays as it is on `main`.
- `wiki/stereorepo/issue.md`, whose lead says seats add "what the next
  reader should know once they have", which stays true.

## Done when

`pair/test_pair.py` shows each of these:
- a turn whose seat added a note leaves exactly that note, quoted and
  labelled, and no closing-message note;
- a turn whose seat added none leaves its closing message;
- a seat's edit to an earlier note is put back, and what it appended in the
  same turn is still its note;
- a turn that only wrote a note is quiet.

## The plan

1. `board.added_note(before, after, stops)` in `pair/board.py` returns what
   the seat appended to each `Pair notes` section, matched by order as
   `board.restore_notes` matches them. For a section `before` had, that is
   the final `insert` of a line diff (`difflib.SequenceMatcher`) against the
   section as it stood, so edits above it are not part of the note. For a
   new section, it is everything under its heading. When every line is
   quoted, one level of `> ` comes off, and any line shaped like a turn label
   (`**primary, todo turn 2**`) is dropped, so a seat that copies the look of
   the loop's notes is not quoted or labelled twice. A `Pair notes` section
   runs to the next heading of its own level or above (`board._note_spans`),
   so a subheading in a seat's note stays in the note instead of splitting
   it: the part under it would otherwise stay unquoted in the file, with the
   loop's note under a second `## Pair notes` after it.
2. `Loop.restore_notes` returns that note alongside whether it put anything
   back; `Loop.settle` passes it on; `Loop.keep_note` takes it as `own` and
   writes it in place of the closing message when it is not empty, and says
   which it kept; `Loop.record` writes `note_from`.
3. Update `pair/README.md` and the module docstring of `pair/loop.py`.
4. Tests in `PairNotesTest` and a unit test of `board.added_note` beside
   those of `board.restore_notes`. The existing tests that asserted a seat's
   own note was dropped now assert that it is kept.

Risky: a seat that rewrites the last line of an earlier note and appends
after it in one turn gets no note of its own: the diff cannot tell where the
edit ends and the note begins, so the closing message is kept, as before
this change.

## Pair notes

> **primary, backlog turn 1**
>
> I've regroomed `issues/underway/drop-seat-note-instruction.md` and set its difficulty from `medium` to `developer`.
>
> - **Why `developer`:** before it lands, someone has to run a fresh seat's first turn with the new prompt and see whether the model's safeguards refuse it. A seat can't do that check. The loop reads its prompts from the checkout it runs from (`PROMPTS` in `pair/pair.py`), not from this worktree, and a seat's sandbox can't start another seat. So the developer has to run it by hand before the Issue goes to `main`.
> - **Wanted:** the choice is now made. Delete the one sentence ("Write what the next reader should know… in the issue file, not in commit messages"). The same prompt already tells the seat to update the plan in the Issue file, so narrowing the sentence to the plan would only repeat that.
> - **Done when:** I took out the condition about the restore count in `turns.jsonl` falling to zero over the next Issues. That can only be seen after this lands, so I moved it to "Out of scope". What's left can be checked: the sentence is gone, nothing else under `pair/prompts/` differs from `main`, and the developer has recorded the result of the fresh-seat run in the file.
> - **Context:** I confirmed that the Issue this one waits on, `pair-notes-belong-to-the-loop`, is in `issues/done/`. I also named the code it added: `Loop.restore_notes` and the `notes_restored` field it logs in `turns.jsonl`.

> **secondary, backlog turn 2**
>
> I checked my partner's grooming against the code. It holds up, so I made only one change to the Issue file.
>
> **What I checked:**
> - The sentence the Issue removes is in `pair/prompts/stage-in-progress.md`.
> - That prompt already says "Update the plan in the issue file if the work shows it was wrong", so deleting the sentence doesn't stop seats updating the plan.
> - The Issue this one waits on, `pair-notes-belong-to-the-loop`, is in `issues/done/`.
> - The code the Issue names exists in `pair/loop.py`: `Loop.keep_note`, `Loop.restore_notes` and the `notes_restored` field it logs.
> - `PROMPTS` in `pair/pair.py` reads the prompts from the checkout the loop runs from, not from this worktree.
> - Commit `6fd1ea94` is the revert of the earlier prompt change the model's safeguards refused.
>
> **What I added:** the same wording appears in one other place, the opening paragraph of `wiki/stereorepo/issue.md`, which says seats add "what the next reader should know once they have". I listed that page under "Out of scope" and said why it doesn't need to change: the seat still writes that note, as the closing message the loop keeps. Without this, whoever plans the work might think the page has to change too.
>
> **What I kept:** `difficulty: developer` is right. A seat can't run a new seat's first turn under the changed prompt, so only the developer can find out whether the safeguards refuse it, and that has to happen before the Issue goes to `main`.

> **primary, backlog turn 3**
>
> I've made no changes this turn; the Issue is ready to plan as it stands.
>
> My partner added one item to "Out of scope": `wiki/stereorepo/issue.md`. Its opening paragraph says seats add "what the next reader should know once they have", which echoes the sentence being removed. I confirmed that wording is on the page, and it stays accurate after the change, because the seat still writes that note as the closing message the loop keeps. So the page doesn't need to change.
>
> The rest stands as groomed in my last turn:
> - **Wanted:** delete the one sentence from `pair/prompts/stage-in-progress.md`.
> - **Done when:** the sentence is gone, nothing else in the prompts differs from `main`, and the developer has recorded the result of a fresh seat's first turn under the new prompt.
> - **Difficulty:** `developer`, because a seat can't run that fresh-seat turn itself.

> **primary, todo turn 1**
>
> I've written the plan into the Issue file under `## The plan`. Nothing is implemented yet.
>
> 1. **The change:** delete the one sentence from `pair/prompts/stage-in-progress.md` and nothing else. The prompt's earlier phrase "say in your note…" stays, because "note" still means the closing message the loop keeps.
> 2. **Nothing else needs to change:** only the prompt quotes the sentence. `pair/README.md` names the file without quoting it, and `pair/test_pair.py` doesn't check its wording. Comparing `pair/prompts/` against `main` should show just the one deletion.
> 3. **Tests:** no new test. No test can say whether a model refuses a prompt; the existing `pair/test_pair.py` suite must still pass.
> 4. **The developer's check:** the loop reads its prompts from the main checkout, so no seat sees the new wording until the Issue lands. At the desk check, the developer runs one fresh primary seat's first in-progress turn by hand with this branch's prompts, against a throwaway Issue in a scratch worktree. They record the date, the model and whether it was refused, then either accept or put the sentence back and send the Issue back.
>
> The risk is that the change reverted in `6fd1ea94` was refused in this same area, which is why the check has to happen before landing. Once it lands, the running loop notices the changed prompt (`code_fingerprint` in `pair/pair.py`) and restarts itself. Every later seat then gets the new wording at once, with no gradual rollout.

> **secondary, todo turn 2**
>
> I checked my partner's plan against the code and corrected one step. Everything else holds, and nothing is implemented yet.
>
> **What I fixed:** step 4, what the developer does if the new prompt is refused. The plan said to "send the Issue back" but didn't say how. The obvious way, `just pair-resume`, doesn't do what "Done when" asks:
> - `Loop.resume` in `pair/loop.py` moves the Issue to `in-progress` for the pair to redo. It doesn't send it to the backlog.
> - What moves an Issue to `issues/backlog/` is a `# Needs elaboration` section in its file. `Loop.decide` sees that section after the next turn and kicks the Issue back.
>
> So step 4 now says: on a refusal, the developer puts the sentence back in the worktree, quotes the refusal under a `# Needs elaboration` heading, then runs `just pair-resume`.
>
> **What I confirmed:**
> - `code_fingerprint` in `pair/pair.py` covers `prompts/`, so a running loop restarts itself when the prompt changes.
> - `pair/seats.py` builds the `claude -p … --append-system-prompt` command that step 4's manual run copies.
> - `pair/test_pair.py` doesn't check the prompt's wording.

> **primary, todo turn 3**
>
> I've changed nothing this turn, because my partner's correction to step 4 is right and the plan is ready to implement.
>
> Step 4 now covers what the developer does if a fresh seat refuses the new prompt at the desk check:
> - **What `just pair-resume` does:** it sends the Issue to `in-progress` for the pair to redo (`Loop.resume` in `pair/loop.py`), not to `issues/backlog/`.
> - **What actually sends it back:** a `# Needs elaboration` section in the Issue file. After the next turn, `Loop.decide` sees that section and returns the Issue to the backlog.
>
> So the steps now in the Issue file are: put the sentence back in the worktree, quote the refusal under a `# Needs elaboration` heading, then run `just pair-resume`. That gets the Issue back to the backlog, as "Done when" asks.

> **primary, in-progress turn 1**
>
> I've deleted the sentence from `pair/prompts/stage-in-progress.md`. That one line is the only difference from `main` under `pair/prompts/`, and nothing else changed, so the plan held as written. Committed as `2b660e41`.
>
> The meta gate passed, and so did the pair gate, which ran the 288 tests in `pair/test_pair.py` and ruff.
>
> One thing is still left before this lands: the developer's check at the desk check. Neither seat can do it, because the loop reads its prompts from the main checkout, so no seat has seen the new wording yet. The developer runs one fresh primary seat's first in-progress turn with this branch's prompts, against a throwaway Issue in a scratch worktree. They record the date, the model and whether it was refused in the Issue file, then:
> - **If it isn't refused:** run `just pair-accept`.
> - **If it is refused:** put the sentence back in the worktree, quote the refusal under a `# Needs elaboration` heading, and run `just pair-resume`.

> **secondary, in-progress turn 2**
>
> I checked the implementation, and it's right, so I've changed nothing this turn.
>
> - **The change:** the sentence is deleted from `pair/prompts/stage-in-progress.md`. Comparing `pair/` against `main` shows only that one line changed, and no other wording in the prompt moved.
> - **Gates:** I didn't re-run them, since I changed nothing. My partner ran the meta gate and the pair gate (the 288 tests in `pair/test_pair.py` and ruff) on this same change, and both passed.
> - **Still to do:** the developer has to run one fresh seat's first in-progress turn under the new prompt and record whether it was refused. No seat can do that, so it waits for the desk check.

Gated by the supervisor at 21:19: `meta`, `pair`; 97 steps passed.

## Desk-check notes

The developer does not want the sentence deleted. The intended design is that
the seat writes its own note in the Issue file when it can, and the loop
writes the turn's closing message as the note only when the seat wrote none.
What `pair-notes-belong-to-the-loop` built instead discards whatever the seat
writes and always keeps the closing message. Rework this Issue to the
intended design.

- **Keep the sentence.** Restore `pair/prompts/stage-in-progress.md` to its
  wording on `main`, so no prompt changes. With no prompt change, the check
  of a fresh seat's first turn is no longer needed: drop it from "Done when"
  and from the plan, and lower the difficulty from `developer`.
- **Keep the seat's note when it wrote one.** After a turn, the loop finds
  what the seat added to the Pair notes section during that turn, by
  comparing the section with how it stood at the head the turn started from.
  - If the seat added a note, that note is the turn's note. The loop gives it
    what it gives a closing message today: quoted, under the turn's label,
    with `path:line` citations rewritten, so that no heading or bold lead in
    it steers the loop (`board.with_note`). The closing message is then not
    written as a second note.
  - If the seat added nothing, the loop writes the closing message as the
    note, as it does now.
  - Edits a seat makes to earlier notes are still put back, as
    `restore_notes` does now: only what the seat added this turn can become
    its note.
- **Keep what already works.** A turn whose only changes are to the Pair
  notes section still counts as quiet, so writing or tidying a note never
  resets the approvals. `notes_restored` in `turns.jsonl` stays, and a new
  field records whether the turn's note came from the seat or from its
  closing message.
- **Retitle the Issue** to say what it now delivers, and update
  `pair/README.md` where it describes how a turn's note is written.
- **Tests** in `pair/test_pair.py`: a turn whose seat added a note leaves
  exactly that note, quoted and labelled, and no closing-message note; a turn
  whose seat added none leaves the closing message; a seat's edit to an
  earlier note is put back; and a turn that only wrote a note is quiet.

## Pair notes

> **primary, in-progress turn 1**
>
> I've reworked the Issue to the developer's design: if a seat writes a note in the Pair notes, the loop now keeps that note as the turn's note and falls back to the closing message only when the seat wrote none. The meta and pair gates both pass (291 tests, ruff clean), and it's committed.
>
> - **Prompt:** `pair/prompts/stage-in-progress.md` is back to its wording on `main`, so the sentence stays and no prompt changes.
> - **Issue file:** retitled "Keep the note a seat writes in the Pair notes as its turn's note". I rewrote "Wanted", "Out of scope", "Done when" and the plan, and lowered the difficulty from `developer` to `medium`. With no prompt change, the hand check of a fresh seat's turn is no longer needed.
> - **Finding the seat's note:** a new function, `board.added_note` in `pair/board.py`, finds what the seat added to the Pair notes during the turn. That is either lines appended after the end of an existing notes section, or a notes section the seat opened itself. Edits to earlier notes are not part of the note.
>   - If the seat copied the look of the loop's notes, one level of `> ` quoting and any label line come off, so the note isn't quoted or labelled twice.
> - **Loop changes** (`pair/loop.py`):
>   - `Loop.restore_notes` still puts back every edit the seat made to the Pair notes. It now also returns what the seat added.
>   - `Loop.keep_note` writes the seat's note if there is one, and the closing message otherwise.
>   - A turn whose only change is in the Pair notes still counts as quiet.
> - **Log:** each row in `turns.jsonl` keeps `notes_restored` and gains a `note_from` field: `"seat"`, `"message"`, or `null` when no note was kept.
> - **Docs:** `pair/README.md` and the module docstring of `pair/loop.py` now describe how a turn's note is chosen.
> - **Tests:** I changed four existing tests in `PairNotesTest` that expected a seat's note to be dropped; they now expect it to be kept. I added tests for a seat note quoted like the loop's, and for a turn that both edits an earlier note and appends a new one. I also added a unit test for `board.added_note`.
>
> One limitation is noted as a risk in the Issue file. If a seat rewrites the last line of an earlier note and appends after it in the same turn, the loop can't tell where the edit ends and the new note begins. That turn gets no note of its own, and its closing message is kept instead, as before this change.
>
> I didn't write a decision record for the new design; your partner may judge whether one is needed.

> **secondary, in-progress turn 2**
>
> My partner's rework does what the developer asked at the desk check: a note the seat writes in the Pair notes is now kept, and the closing message is used only when it wrote none. I fixed one bug in it and one inaccurate passage in the README. The pair gate (291 tests and ruff) and the meta gate both pass, and the fixes are committed as `fdd5033b`.
>
> **The bug:** a note with its own subheading, such as `### Details`, was split in two. A `Pair notes` section ended at any heading at all, so a scratch script showed this result:
> - the loop kept only the part above the subheading as the turn's note;
> - the part below stayed in the Issue file unquoted;
> - the loop then opened a second `## Pair notes` heading after it.
>
> The old behaviour left the same mess, but it matters more now that seats are told to write their notes in the file and those notes are kept.
>
> **The fix** (`_note_spans` in `pair/board.py`): a `Pair notes` section now runs until a heading of its own level or higher. It still ends at any heading named `Pair notes` or in the stop list, so a seat's `# Needs elaboration` still ends it, as before. A section opened by a bold lead still ends at any heading. I added two cases to `test_added_note_is_what_a_seat_wrote_after_the_notes_and_no_edit`: a deeper subheading stays in the note, and a heading at the same level ends it. I also recorded this in the plan in the Issue file.
>
> **The README:** `pair/README.md` said a seat's note is kept only if the seat "left otherwise as it was" the section it wrote in. That isn't what the code does: a seat can edit an earlier note and still have what it appended kept, which `test_a_seats_edit_to_an_earlier_note_is_put_back_and_its_own_note_kept` checks. The README now says what the code does, and also covers subheadings. I also rewrapped a line that was too long, and the description of `PAIR_NOTES` in `pair/board.py` now says "note" instead of "closing message".

> **primary, in-progress turn 3**
>
> My partner's fix is right, and I've kept it. The only thing I changed is the wrapping of two lines in `pair/README.md`. The meta gate and the pair gate (291 tests and ruff) pass, and it's committed as `05dfd139`.
>
> - **The bug it fixes:** a `Pair notes` section used to end at any heading. So if a seat gave its note a subheading such as `### Details`, the loop kept only the part above it. The part below stayed in the file unquoted, and the loop opened a second `## Pair notes` heading after it.
> - **The fix:** a section now runs until a heading at its own level or higher, so a subheading stays part of the note.
> - **Why it's safe:** the only code that uses this section finder is the notes restore and `board.added_note`.
>   - A section still ends at any heading named in the stop list or named `Pair notes`, so a seat's `# Needs elaboration` or `The plan`, at any level, still sits outside the notes.
>   - A heading the developer writes at the desk check is committed before the turn starts, so the loop doesn't treat it as the seat's addition.
> - **The README:** my partner's edit left one line too long and one paragraph broken mid-sentence. I rewrapped both, and changed no wording.

> **secondary, in-progress turn 4**
>
> I agree with my partner's last turn and kept everything in it. The only thing I changed is the wrapping of one paragraph in `pair/README.md`. The pair gate (291 tests and ruff) and the meta gate both pass, and the change is committed as `95a6b1c2`.
>
> My partner's rewrap left two long lines in the paragraph under "How an Issue moves", which describes how a turn's note is kept. Fixing just those two lines kept pushing the overflow onto the next line, so I rewrapped the whole paragraph to 78 columns. A word-by-word diff shows no wording changed. The rest of the README still has long lines, but they were there before this Issue and I left them alone.
>
> The code change, the tests and the plan stand as they were after my last turn.

> **primary, in-progress turn 5**
>
> I kept my partner's rewrap of the `pair/README.md` paragraph about how a turn's note is kept, with one fix:
> - **The problem:** the rewrap split two code spans across a line break: `` `# Needs elaboration` `` and `` `just gate` ``. Markdown still renders them correctly, but searching the README for either one no longer found it.
> - **The fix:** I moved each span onto a single line by breaking the line just before it. No wording changed.
>
> The meta gate and the pair gate both pass, and the fix is committed as `ef9709b4`. The code, the tests and the plan are unchanged from earlier turns.

> **secondary, in-progress turn 6**
>
> Nothing to change this turn: my partner's fix is right, and I've left it as it is.
>
> My `textwrap` rewrap had split two code spans, `` `# Needs elaboration` `` and `` `just gate` ``, across line breaks, so searching the README for either one no longer found it. My partner put each span back on one line and changed no wording. That leaves one line at 85 columns, but most of the README's other long lines were there before this Issue, so it isn't worth another rewrap.
>
> The code, the tests and the plan are as they were. I made no change, so I didn't re-run the gates; they passed after my partner's last commit, `ef9709b4`.

Gated by the supervisor at 21:39: `meta`, `pair`; 97 steps passed.
