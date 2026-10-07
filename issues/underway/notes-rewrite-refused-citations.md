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

- `board.with_note` neutralizes, in the note it writes, every form the
  citation checks refuse, as it already does for line citations: decision
  ids, `Class.slot` citations and backticked slot names, and anything else a
  check under `.meta/checks/citations/` reads. A note records a turn and is
  not a claim a reader should follow, so the rewrite keeps the words and
  drops the form the checks match.
- Prefer one rule over a list that must track the checks: for example, have
  the citation checks skip quoted lines under `## Pair notes`. Say in the
  docstring which rule was chosen and why.

## Out of scope

- A note the seat writes itself, which `pair-notes-belong-to-the-loop`
  handles.
- Citations outside `## Pair notes`, which the checks must keep reading.

## Done when

- A test shows that a note quoting a refused decision id and a refused
  `Class.slot` citation leaves `just gate meta` passing on the Issue file.
- A refused citation outside the notes still fails.
