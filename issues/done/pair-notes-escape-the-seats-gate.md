---
difficulty: easy
---
# A seat's pair note escapes the gate that seat ran

`Loop.keep_note` in `pair/loop.py` quotes a seat's closing message under
`## Pair notes` in the Issue file after the turn ends, so the `just gate meta`
the seat ran never saw it. When the note cites a stale `path:line`, the
`path and line claims` step fails on the next seat's turn, and that seat
spends its turn rewording the other seat's note. On
`release-recipe-is-scaffold-only` this happened on two turns running: each
note described the fix by quoting the stale citations it had just removed.

The step (`path_and_line_claims` in `.meta/checks/citations/claims.py`)
reads every `.md` file, Issue files included. It matches only a code span
holding a path, a colon and a line number (its `PATH_LINE` pattern), and it
then checks that the line exists and contains the code spans written beside
it.

## Wanted

The note keeps a record of the turn. It is not a claim that a later reader
should follow to a line. So `board.with_note` in `pair/board.py`, which
`keep_note` calls, rewrites each `path:line` code span in the note so that
`PATH_LINE` no longer matches it. The path stays in code formatting and the
line number moves out as prose: a span holding pair/loop.py:1009 becomes
`` `pair/loop.py` line 1009 ``. (The citations in this file are written
without their backticks so that the file does not itself make the claim.) Code spans that do not hold a line citation
stay as they are. The rewrite applies only to the note, not to the rest of
the Issue file.

The `with_note` docstring says that a note's line citations are defanged, and
why.

## Out of scope

- Changing what `path and line claims`, or any other citation step, checks in
  other files.
- Other steps that a note could fail, such as an unresolved DR or Article
  number, or a quotation attributed to an entry that does not hold it. None
  has been seen to fail on a note. If one does, it goes in a new Issue.
- Rewriting notes that are already in Issue files.

## How anyone will know it is done

- A test in `pair/test_pair.py` gives `board.with_note` a note holding a
  code span of pair/loop.py:99999 beside an unrelated code span. The quoted
  note in the result holds `` `pair/loop.py` line 99999 `` and no code span
  of the form path, colon, line number. The test states that form itself
  rather than importing `PATH_LINE`: importing `.meta/checks` pulls in
  `linkml_runtime`, which the pair tests do not have.
- In the same test, a code span with no line number (for example `keep_note`)
  and the Issue text above the note come back unchanged.
- The tests that already cover `## Pair notes` still pass unchanged.

## The plan

One seam, `board.with_note` in `pair/board.py`. `keep_note` in `pair/loop.py`
does not change.

1. In `pair/board.py`, next to `PAIR_NOTES`, add a private pattern
   `_LINE_CITATION`. It copies `PATH_LINE` from
   `.meta/checks/citations/claims.py` character for character: a backtick,
   a path with no backtick, space or colon that holds a `.` or `/`, a colon,
   digits, then a backtick. A comment names `PATH_LINE` as its source, so that
   anyone who edits one knows to edit the other. The pattern is copied rather
   than imported because the pair package does not import from `.meta`.
2. In `with_note`, before quoting, run
   `` _LINE_CITATION.sub(r"`\g<path>` line \g<line>", note) ``. The label and
   `text` are not touched.
3. Add a paragraph to the `with_note` docstring. It says that a note records a
   turn and makes no claim a reader should follow to a line. The gate the seat
   ran never saw the note, so any line citation in it is rewritten out of the
   form the `path and line claims` step checks.
4. Add a `BoardTest` case in `pair/test_pair.py` beside
   `test_a_note_opens_its_own_section_after_any_other`. Its note holds a code
   span of pair/loop.py:99999 next to `keep_note`, and its text has a code
   span of its own. The test builds the backticked citation by concatenating
   strings, so the test file does not itself carry the claim. (Test files are
   not `.md`, but the concatenation keeps a reader from mistaking it for one.)
   It asserts that:
   - the result holds `` `pair/loop.py` line 99999 ``
   - a local copy of the pattern finds nothing in the result
   - `keep_note` and the text above the note come back unchanged
5. Run `python -m unittest` on `BoardTest` and `PairNotesTest` in
   `pair/test_pair.py`.

**Risks.** The copied pattern can drift from `PATH_LINE`. The comment is the
only guard, and that is enough for a single regex. The rewrite also reaches
inside a fenced code block in a note, which `PATH_LINE` may skip. That only
changes how a note reads, so it is acceptable. Forms that `PATH_LINE` does not
match, such as a line range or a column, are left alone, as they should be.

## What was done

`board.with_note` rewrites line citations as the plan describes, and
`BoardTest.test_a_note_cites_no_line_for_the_citation_step_to_check` covers it.
The plan held. The citation pattern now lives in three places: `PATH_LINE` in
the check, `_LINE_CITATION` in `pair/board.py`, and inline in the test. An
edit to `PATH_LINE` belongs in all three. Notes already in Issue files keep their
citations. A stale one there still fails the step, and the fix is to edit that note.
`pair/README.md`, which describes how the loop keeps notes, now says that a
note's line citations are rewritten, and why.

## Pair notes

> **primary, backlog turn 1**
>
> I've groomed `issues/underway/pair-notes-escape-the-seats-gate.md`, set it to `difficulty: easy`, and committed it as `7bae51d3`. I didn't run any tests, since only the issue file changed.
>
> - **What the fix is:** the seat's closing note goes into the Issue file through `board.with_note` in `pair/board.py`. The fix changes that function to rewrite each `path:line` citation in the note: a span holding pair/loop.py:1009 becomes `` `pair/loop.py` line 1009 ``. The `path and line claims` step only recognises a path, colon and line number inside one code span, so it no longer checks these. The rest of the Issue file, and code spans without a line number, stay as they are. The function's docstring should say why.
> - **Out of scope:** changing what the citation checks do, other checks a note could fail (such as a decision record number that doesn't exist), and rewriting notes already in Issue files. The original issue asked for a general guarantee against any failing check. I narrowed it to `path:line` citations because those are the only failures anyone has seen. If another check fails on a note, that goes in a new Issue.
> - **How we'll know it's done:** a new test in `pair/test_pair.py` passes a note citing pair/loop.py:99999 in a code span to `with_note`. The output must hold the rewritten form, and the citation check's pattern must find nothing in it. The test also confirms that other code spans and the Issue text above the note come back unchanged. The existing tests for `## Pair notes` must still pass.

> **secondary, backlog turn 2**
>
> I fixed two problems in the groomed issue and committed the change as `91f2ed08`. The grooming itself was sound: `with_note` exists in `pair/board.py`, `keep_note` in `pair/loop.py` calls it, and the regex the citation check uses is as the issue describes. `difficulty: easy` is right.
>
> - **The issue file failed the check it is about.** It quoted the test's example citation, line 99999 of `pair/loop.py`, inside backticks, so it would have failed the `path and line claims` check. I ran that check on its own and it flagged the example twice: once in the done criteria and once in the primary seat's pair note. The other example, line 1009, passed only because that line is `keep_note` today; any edit above it in `pair/loop.py` would break it. I rewrote every example citation in the file without backticks and added a short sentence explaining why. Running the check again on its own found no problems in the file.
> - **The done criterion couldn't be tested as written.** It asked the test in `pair/test_pair.py` to import the check's regex from `.meta/checks/citations/claims.py`. Importing that module also loads `linkml_runtime`, and the pair tests don't import anything under `.meta`. The criterion now has the test write the citation form itself and assert that no code span in the result has that form.

> **primary, backlog turn 3**
>
> Your partner's two fixes are right, and I'm leaving the issue as it stands.
>
> - **Backticked example citations:** writing them without backticks keeps the issue file from failing the citation check it describes. Backticked, the `pair/loop.py` line 99999 example would always have failed. The line 1009 example passed only because that line happens to hold `keep_note` today.
> - **The test's pattern:** having the test write out the citation form itself is the workable choice. Importing the pattern from `.meta/checks/citations/claims.py` would also load `linkml_runtime`, which the pair tests don't have.
>
> None of the backticked spans left in the file are a path, colon and line number in one span, so the check won't match them.

> **primary, todo turn 1**
>
> I've written the plan under `## The plan` in `issues/todo/pair-notes-escape-the-seats-gate.md` and committed it. I haven't run any tests, since only the issue file changed.
>
> The change sits in one function, `board.with_note` in `pair/board.py`. The function that calls it, `keep_note` in `pair/loop.py`, stays as it is.
>
> 1. **A copy of the citation check's pattern.** Add a private pattern, `_LINE_CITATION`, to `pair/board.py`. It is an exact copy of `PATH_LINE` from `.meta/checks/citations/claims.py`, the pattern behind the `path and line claims` check. A comment names the original. It is copied rather than imported because the pair code doesn't import anything from `.meta`.
> 2. **The rewrite.** `with_note` runs the pattern over the note before quoting it. A code span holding pair/loop.py:1009 comes out as `` `pair/loop.py` line 1009 ``. The label and the rest of the Issue file are left alone.
> 3. **The docstring.** A paragraph in `with_note`'s docstring explains why: a note records a turn rather than making claims about lines, and the gate the seat ran never saw it.
> 4. **The test.** A new test in `BoardTest` in `pair/test_pair.py` checks three things:
>    - the citation comes out in the rewritten form;
>    - a local copy of the pattern finds no citation in the output;
>    - an ordinary code span and the text above the note come back unchanged.
> 5. **The test run.** Run `BoardTest` and `PairNotesTest` with `unittest`.
>
> There are two small risks:
> - **The copy can drift.** If someone edits `PATH_LINE`, the copy won't follow it. The comment is the only safeguard, which seems enough for one regex.
> - **Code blocks get rewritten too.** A citation inside a fenced code block in a note is rewritten, even if the check would have skipped it there. That only changes how the note reads.

> **secondary, todo turn 2**
>
> The plan holds up, so I've left the issue unchanged.
>
> - **Names:** the classes and the test the plan names are all in `pair/test_pair.py`: `BoardTest`, `PairNotesTest`, and `test_a_note_opens_its_own_section_after_any_other`. `PAIR_NOTES` is in `pair/board.py`, where step 1 places the new pattern.
> - **Citation check:** I ran the `path and line claims` check alone on the issue file with the plan in it, and it reported nothing. The pattern in step 2's code span doesn't look like a path, a colon and a line number.
> - **Approach:** copying the pattern instead of importing it fits how the pair tests are set up, since they import nothing under `.meta`. The risks the plan lists, the copy drifting from the original and citations inside code blocks being rewritten, are small.

> **primary, in-progress turn 1**
>
> A seat's note can no longer leave a line citation in the Issue file for the `path and line claims` check to fail on. I implemented the plan and committed it as `269a339a`. `just gate meta` and `just gate pair` both pass (the pair gate ran 231 tests).
>
> - **The fix:** `board.with_note` in `pair/board.py` now rewrites each line citation in a note before quoting it. A code span holding pair/loop.py:1009 comes out as `` `pair/loop.py` line 1009 ``, which the check doesn't look at. The label and the rest of the Issue file are left alone. The docstring explains why: the seat's gate ran before the note was written, so it never checked the note.
> - **The pattern:** `_LINE_CITATION` is an exact copy of the check's `PATH_LINE` from `.meta/checks/citations/claims.py`. A comment points back to the original, because the pair code can't import from `.meta`.
> - **The test:** `test_a_note_cites_no_line_for_the_citation_step_to_check` in `BoardTest` checks three things:
>   - the citation comes out in the rewritten form;
>   - an ordinary code span and the Issue text above the note come back unchanged;
>   - no citation is left in the output.
>
>   It builds the citation by joining two strings, so the test file doesn't contain one itself. I added `import re` to `pair/test_pair.py` for it.
>
> The plan held. I added a `## What was done` section to the issue for the next reader, which makes two points:
> - **Three copies of the pattern:** it now lives in the check, in `pair/board.py` and in the test, so a change to `PATH_LINE` needs all three.
> - **Old notes:** notes already in Issue files keep their citations. A stale one there will still fail the check until someone edits that note.

> **secondary, in-progress turn 2**
>
> My partner's implementation was correct; the one thing it missed was the documentation. `pair/README.md` explains how the loop keeps a seat's note in the Issue file, but it didn't mention the new rewrite.
>
> - **The code:** `with_note` in `pair/board.py` rewrites a code span holding a path, a colon and a line number into the path followed by "line" and the number. The rest of the Issue file is left alone. The new test checks the rewritten form and that no citation is left in the output. It also checks that an ordinary code span and the text above the note come back unchanged.
> - **What I changed:** I added a sentence to `pair/README.md` saying that a note's line citations are rewritten, and why: the seat's checks ran before the note was written, so a stale citation would fail the next seat's turn. I also added a line to the issue's "What was done" section pointing to that sentence.
> - **Checks:** `just gate meta` and `just gate pair` both pass after these edits; the pair gate ran 231 tests. Both changes are committed, the second as `dd581fa0`.

> **primary, in-progress turn 3**
>
> My partner's addition is correct, so I'm changing nothing this turn. AGENTS.md wants documents updated along with the change, and `pair/README.md` describes how the loop keeps notes, so it needed a sentence. Theirs names `board.with_note` and explains the reason accurately. My partner ran `just gate meta` and `just gate pair` after that edit and both passed; I haven't run them again because nothing has changed since. The code, the test and the issue's `## What was done` section still match each other.
