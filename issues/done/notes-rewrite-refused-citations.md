---
difficulty: medium
---

# Keep a note from failing the gate by quoting a citation the gate refuses

`board.with_note` rewrites each `path:line` code span in a turn's note, so
the `no line citations` step has nothing in the note to refuse. The other
citation checks still read notes. A seat that fixes a refused citation
usually explains the fix, and the explanation quotes the citation. The note
then fails the same check, and the next turn is spent on it.

It has happened twice in fitch-mvp:

- `priority-attribution-flip` (5 October 2026): in-progress turns 9 to 12
  removed notes that quoted a class dotted to `slot_usage`, which the
  cited-schema-slots check refuses. Each removal was a change, so the stage
  could not settle.
- `sqlite-reference-rerecord` (5 October 2026): turn 8 removed a decision id
  that no Decision Record had yet, and its note quoted the id twice, so the
  branch still failed `cited decisions` when the stage ran past its round cap.

## Wanted

One rule on the reading side, not a rewrite per citation form in
`board.with_note`, so that a check added later under
`.meta/checks/citations/` is covered without anyone remembering the notes:

- The citation checks do not read the quoted lines (those starting `>`)
  of a `Pair notes` section in a Markdown file under `issues/`. A section
  opens and ends as `_note_spans` in `pair/board.py` defines it when the
  loop passes it `NOTE_STOPS` from `pair/loop.py`: it opens at a heading or
  bold lead named `Pair notes`, and ends at the next heading of its level
  or above, at a heading or bold lead named in `NOTE_STOPS` or `Pair
  notes`, or at any heading if a bold lead opened it. The checks live in
  `.meta/` and cannot import `pair/`, which is scaffold-only, so the
  citations package carries its own copy of that rule and of the stop
  names, as a function of the file's text, so a probe can call it without
  writing under `issues/`.
- Every place a check in `.meta/checks/citations/` reads a durable
  Markdown file goes through that reader: `prose.prose` (used by
  `claims.py` and `slots.py`) and the two `FENCED.sub(...read_text())`
  reads in `record.py` (`cited_decisions`, `enacting_citations`).
- The reader's docstring says why: a note records a turn and makes no
  claim a reader should follow, and the gate the seat ran never saw it.

## Out of scope

- A note the seat writes itself, unquoted, which
  `pair-notes-belong-to-the-loop` handles; unquoted lines under
  `Pair notes` are still read.
- Citations anywhere else, including the rest of an Issue file and quoted
  lines outside a `Pair notes` section.
- Removing the `path:line` rewrite in `board.with_note`; it may stay.

## Done when

`cited_decisions` and `cited_schema_slots` scan the whole tree through
`loaders.durable`, so a probe cannot hand them a temporary file. A probe in
`.meta/checks/probes/` tests the reader and the per-file scans instead:

- Given an Issue's text whose `Pair notes` section quotes a decision id
  that no Decision Record has and a `Class.slot` citation of an undeclared
  slot, the reader returns text in which `loaders.DR` finds no id and
  `slots.check_prose_spans` reports no problem.
- With the same two citations also in the Issue's body above the notes,
  each scan finds exactly the one in the body.
- An unquoted line under `Pair notes`, and a quoted line after a bold lead
  named in the stop names, are still read.
- The probe spells its fixture citations from variables, as
  `citation_form_probes` in `.meta/checks/probes/knowledge.py` does, so the
  probe file does not fail the checks it exercises.

`prose.prose` and both reads in `record.py` call the reader for files under
`issues/`, and nothing else in `.meta/checks/citations/` reads a Markdown
file's text directly.

## The plan

1. **The reader, in `.meta/checks/citations/loaders.py`.** Add:
   - `NOTES = "Pair notes"` and `NOTE_STOPS`, a copy of the five names in
     `NOTE_STOPS` in `pair/loop.py` ("Needs elaboration", "The plan",
     "Desk-check brief", "Desk-check notes", "Desk-check children"), and
     `HEADING`, a copy of `_HEADING` in `pair/board.py`. Each docstring
     names the `pair/` original it copies.
   - `without_notes(text: str) -> str`: walks the lines as `_note_spans`
     does (open at a heading or bold lead named `Pair notes`; close at the
     next heading of its level or above, at any heading if a bold lead
     opened it, or at a heading or bold lead named in `NOTE_STOPS` or
     `Pair notes`), and blanks each line inside a section that starts
     with `>`. Blanking rather than dropping keeps the line count. The
     docstring gives the reason the issue asks for.
   - `read(path: pathlib.Path) -> str`: `path.read_text()`, passed through
     `without_notes` when `path` is an Issue file, the test
     `_is_issue` in `.meta/checks/files/board.py` makes
     (`path.suffix == ".md"` and `path.parent.parent == ROOT / "issues"`).
     It raises what `read_text` raises, so callers keep their `except`.
     The path test is its own function, `loaders.is_issue`, so the probe
     can check it without writing a file under `issues/`.
2. **The callers.** `prose.prose` reads through `loaders.read` instead of
   `path.read_text()`; `prose.py` does not import `loaders` today, and
   `loaders` imports nothing from `prose`, so there is no cycle. In
   `record.py`, both `FENCED.sub("", path.read_text())` become
   `FENCED.sub("", loaders.read(path))`. Notes are stripped before fences,
   so a fence opened inside a quoted note cannot pair with one in the
   body. `slots._scan_durable_file` reads text itself only for YAML, and
   `claims.py` reads only `charter.yaml`; both stay as they are.
3. **The probe.** Add `pair_notes_probes` to
   `.meta/checks/probes/citations.py`, registered with
   `@check("pair notes probes", pre=True)` like `cited_schema_slot_probes`.
   It builds an Issue's text whose body and quoted `Pair notes` each hold a
   decision id spelled from a number (`f"DR-{n}"`) and an `Article.<slot>`
   citation of an undeclared slot, against a `slots.SlotIndices` built
   inline that declares only `Article.statement` (the plan first named
   `_FakeDecisionView`, but a schema view is not needed to build indices).
   `flat` is imported from `checks.citations.prose` by name: the package
   re-exports the function `prose`, which shadows the module. Cases:
   - notes only: `loaders.DR.findall` on `without_notes(text)` is empty, and
     `slots.check_prose_spans([prose.flat(...)], ...)` returns nothing;
   - body and notes: each finds exactly one;
   - an unquoted line under `Pair notes`, and a quoted line after a
     `**The plan**` bold lead below the notes, are still read;
   - a quoted line outside any `Pair notes` section is still read;
   - a quoted line under a deeper subheading of the notes is skipped, and
     one after a heading of the notes' own level is read;
   - `is_issue` holds for `issues/<stage>/<slug>.md` and not for
     `issues/README.md`, a non-Markdown file under a stage, or a page
     under `wiki/`.
4. **Drift guard, in `pair/test_pair.py`.** A test that parses
   `.meta/checks/citations/loaders.py` with `ast` (never imports it) and
   asserts its `NOTE_STOPS` tuple equals `loop.NOTE_STOPS`, its `NOTES`
   equals `board.PAIR_NOTES`, and the string passed to `re.compile` for
   `HEADING` equals `board._HEADING.pattern`. Importing is ruled out:
   `loaders` imports `checks.collect`, which imports `linkml_runtime`, a
   dependency of `.meta/` that `pair/`'s tests do not carry. So the three
   copies are written as literals (a tuple of strings, a string, a
   `re.compile` of a raw string), never built from other names. The guard
   lives in `pair/` because `pair/` is the side that may be absent: a
   portfolio without it keeps the copy and loses nothing.

**Risks.**
- The copy drifts from `pair/`; step 4 catches it while `pair/` exists.
- A quoted note line may be indented (a quote inside a list item);
  `without_notes` tests `line.lstrip().startswith(">")`, so those are
  blanked too.
- The issue's own notes quote citation forms; once this lands, they are
  no longer read, which is the point, and nothing else under `issues/`
  should change what the checks report.

## Pair notes

> **primary, backlog turn 1**
>
> I've groomed `issues/underway/notes-rewrite-refused-citations.md` and committed it. I kept `difficulty: medium`, since the work fits in one piece and nobody needs to check it by hand.
>
> **Wanted.** The issue gave two options, and I chose one. The citation checks will skip the quoted lines (the ones starting `>`) inside a `Pair notes` section of a file under `issues/`. The other option was to rewrite each refused citation form in `board.with_note`, which would need updating every time a check is added.
>
> - The checks can't import `pair/`, because it ships only with the scaffold. So the citations package gets its own reader, and it finds the sections the same way `_note_spans` in `pair/board.py` does.
> - I named every place that reader has to cover:
>   - `prose.prose`, which `claims.py` and `slots.py` use.
>   - The two direct file reads in `record.py`, in `cited_decisions` and `enacting_citations`.
>
> **Out of scope.**
> - Notes a seat writes itself without the `>` quoting, which are still checked.
> - Citations anywhere else.
> - Removing the existing line-number rewrite in `board.with_note`; it can stay.
>
> **Done when.** I replaced the gate-based test with a probe (a test under `.meta/checks/probes/`):
> - It builds an Issue file whose `Pair notes` quote a decision id that doesn't exist and a `Class.slot` citation of a slot that isn't declared. `cited_decisions` and `cited_schema_slots` should report nothing.
> - With the same citations moved into the body of the Issue, each check should report one problem.

> **secondary, backlog turn 2**
>
> I made two corrections to my partner's grooming of `issues/underway/notes-rewrite-refused-citations.md` and committed them. I left `difficulty: medium` as it was: the work fits in one piece and the developer doesn't need to check it by hand.
>
> 1. **The "Done when" test couldn't be built as written.** It asked `cited_decisions` and `cited_schema_slots` to report nothing for an Issue file the probe creates. Both checks scan the whole repository through `loaders.durable`, so there's no way to hand them a temporary file. I rewrote the section so the probe tests two things:
>    - **The reader on its own.** The issue now asks for a reader that works on a file's text, so the probe needs no file under `issues/`.
>    - **The per-file scans on the reader's output.** These are `loaders.DR` for decision ids and `slots.check_prose_spans` for slot citations. With the citations quoted in `Pair notes`, they should find nothing. With the same citations in the Issue's body, each should find exactly one.
>
>    I added three more conditions:
>    - A note line without the `>` quoting, and a quoted line after a section-ending bold lead, are still read.
>    - The probe builds its fixture citations from variables, as `citation_form_probes` in `.meta/checks/probes/knowledge.py` already does. Otherwise the probe file would fail the checks it tests.
>    - No check in `.meta/checks/citations/` reads a Markdown file's text without going through the reader.
>
> 2. **The rule for where a `Pair notes` section ends was incomplete.** In practice, `_note_spans` in `pair/board.py` also ends a section at the bold leads listed in `NOTE_STOPS` in `pair/loop.py`, such as **The plan** and **Needs elaboration**. Because the checks can't import `pair/`, the issue now says the citations package keeps its own copy of those names.

> **primary, backlog turn 3**
>
> I checked my partner's corrections against the code and I'm keeping them as they stand, so I changed nothing this turn.
>
> - **Where a notes section ends:** they were right that my version left something out. In `pair/loop.py`, `NOTE_STOPS` lists five names that also end a `Pair notes` section: "Needs elaboration", "The plan", and the names held in `BRIEF`, `NOTES` and `CHILDREN`. Since the checks can't import `pair/`, the issue now says the citations package keeps its own copy of these.
> - **The test in "Done when":** my version couldn't be built. `cited_decisions` and `cited_schema_slots` scan the whole repository through `loaders.durable`, so a test can't hand them a temporary file. The new version tests the reader on an Issue's text, then runs the per-file scans on what the reader returns: `loaders.DR` for decision ids and `slots.check_prose_spans` for slot citations. Both exist with the signatures the issue assumes.
> - **The pattern the probe copies:** `citation_form_probes` exists in `.meta/checks/probes/knowledge.py`.
>
> The issue stays at `difficulty: medium`.

> **primary, todo turn 1**
>
> I've added `## The plan` to `issues/todo/notes-rewrite-refused-citations.md`, above the Pair notes, and committed it. Nothing is implemented yet.
>
> 1. **The reader, in `.meta/checks/citations/loaders.py`.**
>    - It gets its own copies of three things from `pair/`: the five names in `NOTE_STOPS`, the name `Pair notes`, and the heading pattern `_HEADING`. The checks can't import `pair/`, so each copy's docstring names the original it copies.
>    - `without_notes(text)` finds `Pair notes` sections by the same rules `_note_spans` uses. It blanks the quoted lines inside them rather than deleting them, so the line count stays the same.
>    - `read(path)` returns the file's text, run through `without_notes` when the file is an Issue under `issues/<stage>/`.
> 2. **The callers.** `prose.prose` and the two reads in `record.py` (in `cited_decisions` and `enacting_citations`) switch to `loaders.read`. Notes are removed before code fences are, so a fence opened inside a quoted note can't pair with one in the body. The other file reads in the package only open YAML, so they stay as they are.
> 3. **The probe.** A new `pair_notes_probes` in `.meta/checks/probes/citations.py` builds its fixture citations from variables, as `citation_form_probes` does. It checks four cases:
>    - Citations quoted only in the notes: nothing is found.
>    - The same citations in the body as well: exactly one of each is found.
>    - An unquoted line under `Pair notes`, and a quoted line after a section-ending bold lead, are still read.
>    - A quoted line outside any `Pair notes` section is still read.
> 4. **A guard against the copies drifting.** A test in `pair/test_pair.py` asserts that the copies in `loaders.py` still equal the originals in `pair/`. It sits in `pair/` because a portfolio without `pair/` keeps the copy and loses nothing.
>
> **Risks.**
> - **Import cost:** importing `.meta/checks` from `pair/` may be heavy or have side effects. If so, the guard reads the three constants straight from the file with Python's `ast` module instead.
> - **Drift:** the copies can fall out of step with `pair/`, which is why the guard exists.

> **secondary, todo turn 2**
>
> I checked my partner's plan against the code. All of it holds except the drift guard, which couldn't have worked as planned. I corrected that and added one small rule to the plan in `issues/todo/notes-rewrite-refused-citations.md`, and committed the changes.
>
> 1. **The drift guard now reads the file instead of importing it.** The plan had `pair/test_pair.py` import `loaders.py` and compare its copies against the originals in `pair/`. That import pulls in `checks.collect`, which needs the `linkml_runtime` library, and `pair/`'s tests don't have it. The plan had a "maybe use `ast`" fallback (Python's built-in parser); I made that the only approach. The test now parses `loaders.py` without running it. For that to work, the three copies in `loaders.py` must be written out as plain values, not built from other names.
> 2. **Indented quoted lines are skipped too.** A quote inside a list item starts with spaces before the `>`. `without_notes` now checks for `>` after stripping leading whitespace, so it blanks those lines as well.
>
> What I confirmed against the code:
> - `_is_issue` in `.meta/checks/files/board.py`, `_HEADING` and `PAIR_NOTES` in `pair/board.py`, and the five stop names in `pair/loop.py` are all as the plan describes.
> - `_FakeDecisionView` and `slots.check_prose_spans` exist, and the existing probes call `check_prose_spans` the way the plan's probe will.
> - `prose.py` can import `loaders` with no import cycle.
> - A quoted line can never match the heading pattern, because the `>` comes first.
>
> The issue stays at `difficulty: medium`, and nothing is implemented yet.

> **primary, todo turn 3**
>
> I checked my partner's two changes against the code and I'm keeping both, so I changed nothing this turn.
>
> - **The test that keeps the copies in step now reads `loaders.py` instead of importing it.** That was necessary. `pair/test_pair.py` says its tests run with `uv run --with pyyaml`, so they have no `linkml_runtime` library. Importing `loaders.py` would load `.meta/checks/collect.py`, which imports `linkml_runtime`, so the import would fail. Reading the file with Python's `ast` parser means the three copies must be written out as plain values.
> - **Indented quoted lines are blanked too.** This is harmless. In `pair/board.py`, the section-finding code strips each line before matching it against `_HEADING`, so an indented quoted line is never taken for a heading. Blanking it matches how the loop already treats it.
>
> The plan is unchanged and nothing is implemented yet.

> **primary, in-progress turn 1**
>
> A turn's note can no longer fail the citation checks by quoting a citation they refuse. The checks now skip the quoted lines of an Issue's `Pair notes`. `just gate meta` and `just gate pair` both pass, and it's all committed.
>
> **What changed:**
> - **The reader.** `.meta/checks/citations/loaders.py` gets two new functions:
>   - `without_notes` finds `Pair notes` sections the way `_note_spans` in `pair/board.py` does, and blanks the quoted lines inside them. Blanking rather than deleting keeps the line count.
>   - `read` reads a file, and runs an Issue file through `without_notes` first.
>
>   The rule needs three values from `pair/`, which `.meta/` can't import, so `loaders.py` keeps literal copies: `NOTES`, `NOTE_STOPS` and `HEADING`.
> - **Where the checks read files.** `prose.prose` and the two file reads in `record.py` (in `cited_decisions` and `enacting_citations`) now go through `loaders.read`. Notes are removed before code fences, so a fence opened inside a note can't pair with one in the body.
> - **The probe.** A new `pair_notes_probes` in `.meta/checks/probes/citations.py` covers five cases. A decision id and a `Class.slot` citation quoted in the notes are not found. One copy in the body, an unquoted line under the notes, a quoted line after a section-ending heading, or a quote outside the notes are each found exactly once. The fixture citations are built from variables so the probe file doesn't fail its own checks.
> - **The copy check.** A test in `pair/test_pair.py` reads the three copies out of `loaders.py` with Python's `ast` parser and compares them with the originals in `pair/`. It doesn't import the file, because that would need the `linkml_runtime` library, which `pair/`'s tests don't have.
> - **Docs.** The paragraph on notes in `pair/README.md` now describes the skip.
>
> **Two departures from the plan,** both recorded in the plan itself:
> - The probe builds its own small slot index rather than using `_FakeDecisionView`, which wasn't needed.
> - It imports `flat` from `checks.citations.prose` by name. The package exports a function also called `prose`, which hides the module. My first attempt failed on exactly that.
>
> **Follow-up filed:** `issues/backlog/drop-note-line-citation-rewrite.md`. The `path:line` rewrite in `board.with_note` is now redundant. The new issue asks whether to drop it, along with the pattern it duplicates.

> **secondary, in-progress turn 2**
>
> My partner's implementation worked as planned. I filled in what it didn't test and fixed two small things. `just gate meta` and `just gate pair` both pass, and everything is committed.
>
> **Tests added**
> - **The check for which files count as Issues.** `read` decided whether a file is an Issue with an inline path test that nothing exercised. I moved that test into its own small function, `is_issue`. The probe now confirms it accepts `issues/<stage>/<slug>.md`, and rejects `issues/README.md`, a non-Markdown file under a stage, and a page under `wiki/`.
> - **Where a notes section ends.** Two new probe cases:
>   - A quoted line under a deeper subheading inside `Pair notes` is still skipped.
>   - A quoted line after a heading at the notes' own level is read again.
>
> **Fixes**
> - **A baseline the meta gate refused.** `.meta/checks/lines.baseline.yaml` records how many over-long lines each file may have, and the gate requires a file's entry to drop once the file has fewer. With `loaders.py` at zero, I set its entry to 0.
> - **Tidying.** The module docstring for `loaders.py` now mentions how Issue files are read. I also removed an extra blank line at the end of the probe file.
>
> I added these changes to the plan in the issue file. My partner's follow-up, `issues/backlog/drop-note-line-citation-rewrite.md`, stands as written.

> **primary, in-progress turn 3**
>
> I checked my partner's changes against the code and I'm keeping them as they stand, so I changed nothing this turn. The working tree is clean, and `just gate meta` and `just gate pair` both still pass.
>
> - **Pulling out `is_issue`:** this is a good change. The path test in `read` was the one piece of logic nothing tested, and now the probe checks which files count as Issues without writing anything under `issues/`.
> - **The two new probe cases are correct for how `_note_spans` works.** Notes under `## Pair notes` start at level 2:
>   - A `### S` subheading is deeper, so the section stays open and its quoted line is skipped.
>   - A `## N` heading is at the same level, so it ends the section and its quoted line is read again.
> - **The line baseline fix:** this was required. The meta gate makes a file's entry in `.meta/checks/lines.baseline.yaml` go down once the file has fewer over-long lines, and `loaders.py` now has none.

Gated by the supervisor at 11:05: `meta`, `pair`, `specialization`; 99 steps passed.
