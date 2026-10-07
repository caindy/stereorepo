---
difficulty: easy
---

# Drop the line-citation rewrite from pair notes

`board.with_note` in `pair/board.py` rewrites each `path:line` code span in
a turn's note so the `no line citations` step has nothing in the note to
refuse. Since `notes-rewrite-refused-citations`, the citation steps skip the
quoted lines of an Issue's `Pair notes` altogether (`without_notes` in
`.meta/checks/citations/loaders.py`), and `with_note` quotes every line of
the note, so the rewrite, and the copy of `PATH_LINE` (in
`.meta/checks/citations/claims.py`) it keeps as `_LINE_CITATION`, guard
nothing.

## Decision

Drop the rewrite. Keeping the note's prose in the form DR-355 asks for is
not worth a second copy of a pattern that must track the step: a note
records a turn, and no reader follows a note to a line. A note is quoted
as the seat wrote it.

## Wanted

- `with_note` in `pair/board.py` no longer rewrites the note, and
  `_LINE_CITATION` is gone. Its docstring drops the paragraph on the
  rewrite; it may say instead that the citation steps skip quoted notes
  (`without_notes`).
- The paragraph on notes in `pair/README.md` drops the sentences on the
  rewrite and keeps the one on `without_notes`, worded so it covers line
  citations as well as decision ids and `Class.slot` citations.
- The consequence in `.meta/assertions/decisions/DR-355.yaml` that names
  `board.with_note` instead says that the citation steps do not read the
  quoted lines of an Issue's `Pair notes` (`without_notes`), so a note
  may cite a line without failing the next seat's gate. Re-render so
  `.meta/decisions.md` matches.
- `test_a_note_cites_no_line_for_the_citation_step_to_check` in
  `pair/test_pair.py` is replaced by a test that a note's `path:line` code
  span is quoted unchanged (built by concatenation, as now, so the test
  file holds no citation of its own).

## Out of scope

- How `without_notes` decides where a notes section ends.
- `gate_line` in `pair/loop.py`, which strips backticks from a gate's
  reasons: that line is not quoted under `Pair notes`, so the steps still
  read it.
- Any other refused form in a note.

## Done when

- `grep -rn _LINE_CITATION pair/` finds nothing, and no text under `pair/`
  or in DR-355 says that `with_note` rewrites a citation.
- The replacement test passes: `with_note` given a note holding a
  `path:line` code span returns the span unchanged inside a `> ` line.
- `pair_notes_probes` in `.meta/checks/probes/citations.py` covers a line
  citation: its `cites` today holds only a decision id and a `Class.slot`
  citation, so it gains a `path:line` code span (built from variables, as
  the others are). `no_line_citations` takes no text and reads the tree, so
  each case instead counts `PATH_LINE` matches in `without_notes(text)`,
  the pattern the step applies to what `loaders.read` returns, and expects
  the same count as for the other two forms: none for a span quoted in the
  notes, one for a span in the body. The probe's docstring names the line
  citation alongside the other two.

## The plan

1. **`pair/board.py`.** Delete `_LINE_CITATION` with the comment above
   it, and the first statement of `with_note`, which applies it. Replace
   the docstring's second paragraph with one saying the note is quoted as
   written: the citation steps skip quoted lines under `Pair notes`
   (`without_notes` in `.meta/checks/citations/loaders.py`), so a note
   the seat's gate never saw cannot fail the next turn. `re` stays
   imported (`_FRONT`, `_HEADING` and others use it).
2. **`pair/test_pair.py`.** In `BoardTest`, replace
   `test_a_note_cites_no_line_for_the_citation_step_to_check` with
   `test_a_note_keeps_a_line_citation_as_written`: the same concatenated
   `cite`, asserting that the output starts with `text` and holds the
   line `> See {cite} in `keep_note`.` unchanged. Drop the `re.search`
   assertion.
3. **`.meta/checks/probes/citations.py`, `pair_notes_probes`.** Spell a
   line citation from variables (a backtick, `x/y.py:`, `number`, a
   backtick, so the file holds no literal one) and append it to `cites`.
   Import `PATH_LINE` from `checks.citations`; in the loop, count
   `PATH_LINE.findall(read)` alongside `ids` and `found`, each expected
   to equal `expected`, and name the count in the problem message. Name
   the line citation in the docstring next to the decision id and the
   `Class.slot` citation.
4. **`pair/README.md`.** In the notes paragraph, delete the sentence on
   the rewrite (from "A code span citing a path and a line" through "on
   the next seat's turn.") and reword the `without_notes` sentence so it
   covers line citations, decision ids and `Class.slot` citations alike.
5. **`.meta/assertions/decisions/DR-355.yaml`.** Rewrite the consequence
   that names `board.with_note` as Wanted says, then `just render`. The
   index row for DR-355 shows only the title, so `.meta/decisions.md`
   likely does not change, but render anyway.

**Tests.** `BoardTest` in `pair/test_pair.py`: the replacement test, and
the other tests that call `with_note`, which must pass unchanged. The
`pair notes probes` check reports nothing. `grep -rn _LINE_CITATION pair/`
finds nothing.

**Risks.**
- `slots.check_prose_spans` cannot read the new span as a `Class.slot`
  citation: `QUALIFIED_SLOT` in `.meta/checks/citations/slots.py` needs
  a capitalised class name found in `class_slots` (here only `Article`),
  and no `SLOT_PHRASES` pattern matches a path, so a lowercase `x/y.py`
  adds no slot finding and `DR.findall` finds no id in it. Keep the path
  lowercase, so the one-of-each count holds.
- An edited probe line over the `line-length` limit would trip the
  `meta lines` ratchet, which has no entry for that file to absorb it,
  so wrap long lines.

## Implementation notes

- The plan held. One addition: with the rewrite's test gone, nothing in
  `pair/test_pair.py` used `re`, so its import went too.
- The probe spells the backtick as a variable (`tick`), so the line
  citation it builds never appears literally in the probe file.
- DR-355's rejected option keeps its substance, since it records what
  the choice was weighed against, but its name now ends "as pair notes
  were": "are" claimed in the present tense a rewrite that no longer
  exists, which Done when rules out.
- `just render` wrote no files, as the plan expected.

## Pair notes

> **primary, backlog turn 1**
>
> I groomed `issues/underway/drop-note-line-citation-rewrite.md`, set it to `difficulty: easy` and committed it as 9ede55a1.
>
> - **Decision:** drop the rewrite. Every line of a note is quoted, and the citation steps already skip quoted lines under `Pair notes` (`without_notes`). The rewrite protects nothing, and it costs a second copy of the `PATH_LINE` pattern that has to stay in step with the check. A note will now be quoted exactly as the seat wrote it.
> - **Wanted:**
>   - Remove `_LINE_CITATION` and the rewrite from `with_note`, and update its docstring.
>   - Trim the paragraph on notes in `pair/README.md`.
>   - Change the DR-355 consequence that names `board.with_note`, then re-render `.meta/decisions.md`.
>   - Replace `test_a_note_cites_no_line_for_the_citation_step_to_check` with a test that a `path:line` span is quoted unchanged.
> - **Out of scope:** how `without_notes` finds where a notes section ends, `gate_line` in `pair/loop.py` (its line isn't quoted, so the steps still read it), and other refused forms in a note.
> - **Done when:** nothing under `pair/` or in DR-355 refers to the rewrite any more, and the replacement test passes. There is also one gap to close: `pair_notes_probes` in `.meta/checks/probes/citations.py` only tests decision ids and `Class.slot` citations, not line citations. The issue therefore requires a `path:line` case run through the `no line citations` step. A line citation quoted in the notes should produce no finding, and one in the body should produce one.

> **secondary, backlog turn 2**
>
> The grooming holds up. I made one change to the Issue file and kept `difficulty: easy`.
>
> **What I checked:** the case for dropping the rewrite is correct. The `no line citations` step (`no_line_citations` in `.meta/checks/citations/claims.py`) gets its text from `prose.prose`. That calls `loaders.read`, which runs `without_notes` on every Issue file. So the step already skips the quoted lines of `Pair notes`, and the rewrite in `with_note` protects nothing. Every place the Issue says to edit exists and matches its description: `_LINE_CITATION`, the DR-355 consequence that names `board.with_note`, the notes paragraph in `pair/README.md`, the test to replace, and `pair_notes_probes`.
>
> **What I fixed:** the last "Done when" item asked the probe to "run the `no line citations` step" on each case, which it can't do. That step takes no text; it reads the files in the repository. The item now has the probe count `PATH_LINE` matches in `without_notes(text)`, which is the pattern the step applies to what `loaders.read` returns. A line citation quoted in the notes should give no match, and one in the body should give one, the same as the other two citation forms. The probe's docstring must also mention line citations.
>
> I committed the change as 0b5ae297.

> **primary, backlog turn 3**
>
> I checked my partner's change against the code and it's right, so I've changed nothing this turn.
>
> `no_line_citations` in `.meta/checks/citations/claims.py` takes no text. It reads the repository's files through `loaders.durable` and `prose.prose`, then applies `PATH_LINE` to what it finds. So the probe can't feed a test case to the step itself, as my wording asked. Counting `PATH_LINE` matches in `without_notes(text)` tests the same skipping of quoted notes, using the pattern the step applies.
>
> The Issue file now covers what is wanted, what is out of scope and how anyone will know it is done, and `difficulty: easy` still fits.

> **primary, todo turn 1**
>
> I added `## The plan` to `issues/todo/drop-note-line-citation-rewrite.md` and committed it as d36bdc48. Nothing is implemented yet.
>
> **Steps, in order:**
> 1. **`pair/board.py`:** delete `_LINE_CITATION`, its comment, and the call in `with_note` that rewrites the note. Replace that part of the docstring with a note that the citation steps already skip quoted notes (`without_notes`).
> 2. **`pair/test_pair.py`:** replace `test_a_note_cites_no_line_for_the_citation_step_to_check` with `test_a_note_keeps_a_line_citation_as_written`, which checks that a `path:line` span comes through unchanged.
> 3. **`.meta/checks/probes/citations.py`:** in `pair_notes_probes`, add a `path:line` span to the citations each case uses. Count its `PATH_LINE` matches next to the other two kinds, and mention line citations in the docstring.
> 4. **`pair/README.md`:** delete the sentence about the rewrite, and reword the `without_notes` sentence so it covers all three kinds of citation.
> 5. **DR-355:** rewrite the consequence that names `board.with_note`, then run `just render`. `.meta/decisions.md` probably won't change, since its DR-355 entry shows only the title.
>
> **How we'll know it works:** the new test and the other `BoardTest` tests that call `with_note` pass, the `pair notes probes` check reports nothing, and `grep -rn _LINE_CITATION pair/` finds nothing.
>
> **Risks:**
> - The check for `Class.slot` citations might mistake the new span's file path for one and report an extra finding, which would break the probe's counts. The plan uses a lowercase path with a `/` to avoid that, and keeps the line citation separate if it still happens.
> - Any new probe line longer than the line-length limit would fail the line-length check, which has no allowance for that file. Long lines need wrapping.

> **secondary, todo turn 2**
>
> The plan is sound. I changed one of its risks into a fact and committed that as 92e592de.
>
> **What I checked:**
> - **`pair/board.py`:** `_LINE_CITATION`, the comment above it and the first statement of `with_note` are the only parts that do the rewrite. Removing them leaves the rest of `with_note` alone.
> - **Wording:** nothing outside `pair/board.py` depends on the rewrite. No test or probe checks the README or docstring sentences the plan deletes.
>
> **What I changed:** the plan's first risk worried that the `Class.slot` check might mistake the new `path:line` span for a citation and throw off the probe's counts. That can't happen. `QUALIFIED_SLOT` in `.meta/checks/citations/slots.py` only matches a capitalised class name that `class_slots` lists, and the probe lists only `Article`. None of the `SLOT_PHRASES` patterns can match a path, and the decision-id pattern finds no `DR-` in it either. So a lowercase path like `x/y.py` keeps every case at one of each kind. The plan now says that and drops the fallback of counting the line citation separately.
>
> I tried to confirm this by running the check on a sample, but running Python here needs approval I don't have. The conclusion comes from reading the patterns, not from a run.

> **primary, todo turn 3**
>
> I'm leaving the plan as it stands this turn. My partner's correction to the first risk is right, and I confirmed it by reading the patterns.
>
> Adding the line citation to the probe can't change its "one of each" counts:
>
> - **`QUALIFIED_SLOT`** in `.meta/checks/citations/slots.py` only matches a capitalised class name (`[A-Z][a-zA-Z0-9]+`) followed by a dot. In a lowercase `x/y.py`, the only name before a dot is `y`, which doesn't qualify.
> - **`SLOT_PHRASES`**: each pattern needs a slot name of lowercase letters, digits and underscores, so the `/` and `:` in the span stop every one of them from matching.
> - **The decision-id pattern** (`DR` in `.meta/checks/citations/loaders.py`) finds nothing in the span either.
>
> Like my partner, I didn't run anything to confirm this; the conclusion comes from reading the patterns.

> **primary, in-progress turn 1**
>
> I removed the line-citation rewrite as planned, and both gates for what this touches pass: `just gate pair` (292 tests) and `just gate meta` (96 steps, including `pair notes probes`). The work is committed as 7db43967.
>
> - **`pair/board.py`:** I deleted `_LINE_CITATION` and the line that applied it in `with_note`. A note is now quoted exactly as the seat wrote it, and the docstring says the citation steps skip quoted notes (`without_notes`).
> - **`pair/test_pair.py`:** `test_a_note_keeps_a_line_citation_as_written` replaces the old test and checks that a `path:line` span comes through unchanged. Nothing else in the file used `re`, so I removed its import.
> - **`.meta/checks/probes/citations.py`:** `pair_notes_probes` now includes a line citation in its test text alongside the decision id and the `Class.slot` citation. Each case also counts `PATH_LINE` matches and expects the same number as for the other two. The docstring mentions line citations too.
> - **`pair/README.md` and DR-355:** the sentence about the rewrite is gone. Both now say that quoted notes aren't checked, so a note can cite a line without failing the next turn. `just render` wrote no files, as the plan expected.
>
> DR-355 still lists a rejected option worded "as pair notes are", which describes the old rewrite. I left it as written because it records what that decision was weighed against. The new "Implementation notes" section in the Issue file says so for the next reader.

> **secondary, in-progress turn 2**
>
> My partner's implementation was correct and complete. I fixed one leftover wording issue, and both gates pass: `just gate meta` (96 steps, including the probe that checks quoted notes are skipped) and `just gate pair` (292 tests).
>
> **What I checked:**
> - **`pair/board.py`:** the rewrite is gone and `re` is still used elsewhere in the file.
> - **Tests:** the new test builds its citation by joining strings, so the test file contains no line citation of its own.
> - **Probe:** it now counts line citations in each case, alongside decision ids and `Class.slot` citations.
> - **`pair/README.md`:** the notes paragraph says notes are kept as written and that the citation checks skip quoted notes.
> - **Other docs:** nothing else under `pair/`, the wiki or the decision records still describes the rewrite.
>
> **What I changed:** DR-355's rejected option was named "Rewrite line citations out of every Issue file, as pair notes are". After this change that's no longer true, and the Issue's "Done when" says DR-355 shouldn't say it. My partner had left it on the grounds that it is history. I kept what the option says but changed "are" to "were", so it still records what the decision was weighed against without claiming something false. `just render` wrote no files. I updated the Issue's implementation notes to explain this, and committed it as 481d8700.

> **primary, in-progress turn 3**
>
> I'm keeping my partner's change and changing nothing myself this turn.
>
> They renamed DR-355's rejected option from "as pair notes are" to "as pair notes were". I had left the old wording on the grounds that it is history, but "are" now claims a rewrite that no longer exists, and the Issue's "Done when" rules that out for DR-355. "Were" keeps the record without that false claim, and the option's substance is unchanged.
>
> Since I changed nothing, I didn't re-run the gates. My partner ran both after their edit and both passed: `just gate meta` (96 steps) and `just gate pair` (292 tests).

Gated by the supervisor at 11:13: `meta`, `pair`, `specialization`; 99 steps passed.
