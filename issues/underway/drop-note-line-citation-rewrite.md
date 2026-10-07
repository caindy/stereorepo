# Drop the line-citation rewrite from pair notes

`board.with_note` in `pair/board.py` rewrites each `path:line` code span in
a turn's note so the `no line citations` step has nothing in the note to
refuse. Since `notes-rewrite-refused-citations`, the citation steps skip the
quoted lines of an Issue's `Pair notes` altogether (`without_notes` in
`.meta/checks/citations/loaders.py`), so the rewrite, and the copy of
`PATH_LINE` it keeps as `_LINE_CITATION`, guard nothing.

Decide whether to drop the rewrite: it keeps a note's prose in the form
DR-355 asks for, but costs a second copy of a pattern that must track the
step. If dropped, update the paragraph on notes in `pair/README.md`, the
consequence in DR-355 that names `board.with_note`, and the test
`test_a_note_cites_no_line_for_the_citation_step_to_check`.
